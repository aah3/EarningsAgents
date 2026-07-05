import os
import pytest
from datetime import date
from sqlmodel import SQLModel, Session, create_engine, select

from database.models import EarningsHistory
from database.earnings_repo import (
    compute_reaction_summary,
    get_reaction_summary_and_history,
    sync_ticker_history,
)


# ---------- fixtures ----------
@pytest.fixture
def mem_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


class FakeSource:
    """Mirrors EarningsAPIDataSource's return contract. Q1 = EPS beat / +3% next day,
    Q2 = EPS miss / -4% next day."""
    
    def connect(self):
        return True
        
    def get_profile(self, symbol):
        return {
            "company_name": "Fake Corp",
            "sector": "Tech",
            "industry": "Software",
            "market_cap": 1.5e11,
            "exchange": "NASDAQ",
            "country": "US",
            "cik": "0000000000",
            "outstanding_shares": 1e9,
        }
        
    def get_company_earnings(self, symbol):
        return [
            {"date": "2025-05-01", "symbol": symbol, "time": "amc",
             "eps": 2.0, "epsEstimate": 1.9, "revenue": 95e9, "revenueEstimate": 94e9},
            {"date": "2025-02-01", "symbol": symbol, "time": "amc",
             "eps": 1.5, "epsEstimate": 1.6, "revenue": 120e9, "revenueEstimate": 121e9},
        ]
        
    def get_earnings_reactions(self, symbol):
        return [
            {"date": "2025-05-01",
             "eps": {"surprisePercent": 5.26, "yoy": 10.0, "beat": True},
             "revenue": {"surprisePercent": 1.06, "yoy": 8.0, "beat": True},
             "reactions": [{"date": "2025-05-02", "priceChange": 3.0, "volume": 80e6},
                           {"date": "2025-05-03", "priceChange": 1.0, "volume": 50e6}]},
            {"date": "2025-02-01",
             "eps": {"surprisePercent": -6.25, "yoy": -2.0, "beat": False},
             "revenue": {"surprisePercent": -0.83, "yoy": 3.0, "beat": False},
             "reactions": [{"date": "2025-02-02", "priceChange": -4.0, "volume": 90e6}]},
        ]
        
    def disconnect(self):
        pass


# ---------- pure summary math ----------
def test_compute_reaction_summary_math():
    rows = [
        {"reaction_1d_pct": 3.0, "eps_beat": True},
        {"reaction_1d_pct": -4.0, "eps_beat": False},
    ]
    s = compute_reaction_summary(rows)
    assert s["n"] == 2
    assert s["avg_1d_pct"] == -0.5
    assert s["avg_abs_1d_pct"] == 3.5
    assert s["min_1d_pct"] == -4.0 and s["max_1d_pct"] == 3.0
    assert s["beat_move_avg"] == 3.0
    assert s["miss_move_avg"] == -4.0


def test_compute_reaction_summary_empty():
    assert compute_reaction_summary([]) is None
    assert compute_reaction_summary([{"reaction_1d_pct": None, "eps_beat": True}]) is None


# ---------- reaction ordering (guards the flagged risk) ----------
def test_summarize_reaction_uses_first_session_ascending():
    from data.earningsapi_source import summarize_reaction
    reactions = [  # descending by date to test sorting robustness
        {"date": "2025-05-03", "priceChange": 1.0, "volume": 50e6},
        {"date": "2025-05-02", "priceChange": 3.0, "volume": 80e6},
    ]
    out = summarize_reaction(reactions)
    assert out["reaction_1d_pct"] == 3.0                      # first session after sorting ascending, not last
    assert out["reaction_volume"] == 80e6
    # 5d cumulative compounding: (1.03 * 1.01 - 1) * 100 ≈ 4.03
    assert abs(out["reaction_5d_pct"] - 4.03) < 0.05


# ---------- idempotent upsert + summary from DB ----------
def test_sync_is_idempotent(mem_session):
    src = FakeSource()
    n1 = sync_ticker_history(mem_session, "AAPL", src)
    n2 = sync_ticker_history(mem_session, "AAPL", src)   # second run must not duplicate
    total = len(mem_session.exec(select(EarningsHistory).where(EarningsHistory.ticker == "AAPL")).all())
    assert total == 2, f"expected 2 rows after two syncs, got {total}"


def test_summary_from_db(mem_session):
    sync_ticker_history(mem_session, "AAPL", FakeSource())
    summary, rows = get_reaction_summary_and_history(mem_session, "AAPL")
    assert len(rows) == 2
    assert summary["avg_1d_pct"] == -0.5
    assert summary["beat_move_avg"] == 3.0 and summary["miss_move_avg"] == -4.0
    
    latest = rows[0]
    assert latest["revenue_surprise_pct"] is not None
    assert latest["eps_yoy"] is not None


# ---------- the enrichment actually reaches the LLM prompt ----------
def test_format_prompt_includes_reaction_section():
    from config.settings import AgentConfig
    from agents.huggingface_agents import QuantAgent
    from data.base import CompanyData

    company = CompanyData(
        ticker="AAPL", company_name="Apple Inc.", sector="Tech", industry="Consumer Electronics",
        market_cap=3.7e12, report_date=date(2025, 8, 1), consensus_eps=1.95, consensus_revenue=90e9,
        enriched_history=[{
            "report_date": "2025-05-01", "eps_beat": True, "revenue_beat": True,
            "eps_surprise_pct": 5.26, "eps_yoy": 10.0, "revenue_surprise_pct": 1.06,
            "revenue_yoy": 8.0, "reaction_1d_pct": 3.0,
        }],
        reaction_summary={"n": 8, "avg_1d_pct": -0.5, "avg_abs_1d_pct": 3.5, "std_1d_pct": 2.1,
                          "min_1d_pct": -4.0, "max_1d_pct": 3.0, "beat_move_avg": 3.0, "miss_move_avg": -4.0},
        implied_move_pct=0.06,
    )
    agent = QuantAgent(AgentConfig(provider="gemini", api_key="test"))
    prompt = agent._format_prompt(company, [])

    assert "Post-Earnings Reaction Pattern" in prompt
    assert "implied move" in prompt.lower()
    assert "6.0%" in prompt              # implied move rendered
    assert "Next-day move" in prompt     # per-quarter reaction rendered
    assert "YoY" in prompt               # revenue/eps YoY rendered


# ---------- optional live smoke ----------
@pytest.mark.skipif(not os.getenv("EARNINGSAPI_API_KEY"), reason="no API key")
def test_live_reactions_smoke():
    from config.settings import load_config
    from data.earningsapi_source import EarningsAPIDataSource, summarize_reaction
    src = EarningsAPIDataSource(load_config().earningsapi); src.connect()
    r = src.get_earnings_reactions("AAPL")
    assert r and r[0].get("reactions")
    dates = [x["date"] for x in r[0]["reactions"]]
    assert dates == sorted(dates), "reactions must be ascending before summarize_reaction slices [0]"
