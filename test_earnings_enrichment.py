import os
import pytest
from datetime import date, datetime
from zoneinfo import ZoneInfo
from data.market_hours import is_market_open, _ET
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


# ---------- market open/hours tests ----------
def test_market_open_weekday_regular_hours():
    assert is_market_open(datetime(2026, 7, 6, 11, 0, tzinfo=_ET)) is True    # Mon 11:00 ET

def test_market_closed_weekend():
    assert is_market_open(datetime(2026, 7, 5, 11, 0, tzinfo=_ET)) is False   # Sun

def test_market_closed_premarket_and_afterhours():
    assert is_market_open(datetime(2026, 7, 6, 9, 0, tzinfo=_ET)) is False    # 09:00
    assert is_market_open(datetime(2026, 7, 6, 16, 30, tzinfo=_ET)) is False  # 16:30

def test_market_closed_on_holiday():
    hol = {date(2026, 7, 6)}
    assert is_market_open(datetime(2026, 7, 6, 11, 0, tzinfo=_ET), holidays=hol) is False

def test_sample_depth_classification():
    from database.earnings_repo import compute_reaction_summary
    rows = lambda k: [{"reaction_1d_pct": 1.0, "eps_beat": True} for _ in range(k)]
    assert compute_reaction_summary(rows(9))["sample_depth"] == "high"
    assert compute_reaction_summary(rows(5))["sample_depth"] == "moderate"
    assert compute_reaction_summary(rows(2))["sample_depth"] == "low"

def test_format_prompt_shows_market_state():
    from config.settings import AgentConfig
    from agents.huggingface_agents import QuantAgent
    from data.base import CompanyData
    base = dict(ticker="AAPL", company_name="Apple", sector="Tech", industry="CE",
                market_cap=3.7e12, report_date=date(2025,8,1), consensus_eps=1.95, consensus_revenue=90e9,
                live_options={"implied_move_pct":0.06,"put_call_ratio":0.8,"avg_iv":0.35,
                              "confidence_score":8.0,"days_to_expiry":5})
    agent = QuantAgent(AgentConfig(provider="gemini", api_key="test"))
    open_prompt = agent._format_prompt(CompanyData(market_open=True, **base), [])
    closed_prompt = agent._format_prompt(CompanyData(market_open=False, **base), [])
    assert "market OPEN" in open_prompt
    assert "CLOSED" in closed_prompt
    assert "Implied move (straddle)" in open_prompt


def test_history_route_non_blocking_and_enqueues():
    from fastapi.testclient import TestClient
    from api.routers.earnings import router
    from fastapi import FastAPI
    from unittest.mock import MagicMock
    
    app = FastAPI()
    app.include_router(router)
    
    from database.db import get_session
    from sqlmodel import Session
    
    mock_session = MagicMock(spec=Session)
    mock_session.exec.return_value.all.return_value = []
    
    app.dependency_overrides[get_session] = lambda: mock_session
    
    from api import tasks
    original_delay = tasks.sync_ticker_history_task.delay
    tasks.sync_ticker_history_task.delay = MagicMock()
    
    try:
        client = TestClient(app)
        response = client.get("/earnings/history/NEWTKR")
        
        assert response.status_code == 202
        assert response.json() == {"status": "queued", "data": []}
        
        tasks.sync_ticker_history_task.delay.assert_called_once_with("NEWTKR")
    finally:
        tasks.sync_ticker_history_task.delay = original_delay
        app.dependency_overrides.clear()


def test_surprise_normal_case():
    from data.metrics import safe_surprise_pct
    assert round(safe_surprise_pct(1.10, 1.00), 1) == 10.0
    assert round(safe_surprise_pct(0.90, 1.00), 1) == -10.0


def test_surprise_near_zero_base_returns_none():
    from data.metrics import safe_surprise_pct, dollar_surprise
    # the INTC-class bug: $0.10 actual vs $0.02 est must NOT become +400%
    assert safe_surprise_pct(0.10, 0.02) is None
    assert dollar_surprise(0.10, 0.02) == pytest.approx(0.08)


def test_surprise_capped():
    from data.metrics import safe_surprise_pct
    assert safe_surprise_pct(5.0, 1.0) == 100.0          # not +400
    assert safe_surprise_pct(-5.0, 1.0) == -100.0


def test_surprise_none_inputs():
    from data.metrics import safe_surprise_pct, dollar_surprise
    assert safe_surprise_pct(None, 1.0) is None
    assert dollar_surprise(1.0, None) is None


def test_prompt_has_no_absurd_surprise():
    # a low-base historical quarter must not render a giant % in the agent prompt
    from datetime import date
    from settings import AgentConfig
    from agents.huggingface_agents import QuantAgent
    from data.base import CompanyData
    company = CompanyData(
        ticker="INTC", company_name="Intel", sector="Tech", industry="Semis",
        market_cap=6e11, report_date=date(2026,7,23), consensus_eps=1.56, consensus_revenue=13e9,
        enriched_history=[{
            "report_date":"2025-07-01","eps_beat":True,"revenue_beat":True,
            "eps_actual":0.10,"eps_estimate":0.02,          # low base
            "eps_surprise_pct":None,"eps_yoy":5.0,
            "revenue_surprise_pct":1.0,"revenue_yoy":2.0,"reaction_1d_pct":-4.0,
        }],
        reaction_summary={"n":8,"avg_1d_pct":-1.0,"avg_abs_1d_pct":6.0,"std_1d_pct":5.0,
                          "min_1d_pct":-12.0,"max_1d_pct":8.0,"sample_depth":"high",
                          "beat_move_avg":3.0,"miss_move_avg":-7.0},
    )
    prompt = QuantAgent(AgentConfig(provider="gemini", api_key="test"))._format_prompt(company, [])
    import re
    # no surprise percentage above 100% anywhere in the prompt
    assert not re.search(r"[1-9]\d{2,}\.\d%|[2-9]\d{2}%", prompt), "absurd surprise % still rendering"
    assert "Next-day move" in prompt   # reaction data present (Bug 1 guard)


class FakeSourceRev:
    """Fake source that returns distinct per-quarter revenue/EPS actuals/estimates,
    but does NOT return yoy or surprisePercent, forcing local calculations."""
    
    def connect(self):
        return True
        
    def get_profile(self, symbol):
        return {
            "company_name": "Test Corp",
            "sector": "Tech",
            "industry": "Software",
            "market_cap": 1.5e11,
            "exchange": "NASDAQ",
            "country": "US",
            "cik": "0000000000",
            "outstanding_shares": 1e9,
        }
        
    def get_company_earnings(self, symbol):
        # We need quarters that are ~1 year apart to test compute_yoy
        return [
            {"date": "2026-05-01", "symbol": symbol, "time": "amc",
             "eps": 2.2, "epsEstimate": 2.0, "revenue": 105e9, "revenueEstimate": 100e9},
            {"date": "2026-02-01", "symbol": symbol, "time": "amc",
             "eps": 1.8, "epsEstimate": 1.7, "revenue": 130e9, "revenueEstimate": 125e9},
            {"date": "2025-05-01", "symbol": symbol, "time": "amc",
              "eps": 2.0, "epsEstimate": 1.9, "revenue": 95e9, "revenueEstimate": 94e9},
            {"date": "2025-02-01", "symbol": symbol, "time": "amc",
              "eps": 1.5, "epsEstimate": 1.6, "revenue": 120e9, "revenueEstimate": 121e9},
        ]
        
    def get_earnings_reactions(self, symbol):
        # Return reactions but without parsed surprise/yoy to test fallback calculations
        return [
            {"date": "2026-05-01", "reactions": [{"date": "2026-05-02", "priceChange": 2.0, "volume": 10e6}]},
            {"date": "2026-02-01", "reactions": [{"date": "2026-02-02", "priceChange": -1.0, "volume": 10e6}]},
            {"date": "2025-05-01", "reactions": [{"date": "2025-05-02", "priceChange": 3.0, "volume": 10e6}]},
            {"date": "2025-02-01", "reactions": [{"date": "2025-02-02", "priceChange": -4.0, "volume": 10e6}]},
        ]


def test_revenue_surprise_is_per_quarter(mem_session):
    from database.earnings_repo import sync_ticker_history, get_reaction_summary_and_history
    sync_ticker_history(mem_session, "TST", FakeSourceRev())
    _, rows = get_reaction_summary_and_history(mem_session, "TST")
    vals = [r["revenue_surprise_pct"] for r in rows]
    assert len(set(vals)) > 1, "revenue surprise identical across quarters — broadcast bug"
    assert vals[0] == pytest.approx(5.0) # 105e9 vs 100e9 estimate = +5%
    assert vals[1] == pytest.approx(4.0) # 130e9 vs 125e9 estimate = +4%


def test_yoy_populated(mem_session):
    from database.earnings_repo import sync_ticker_history, get_reaction_summary_and_history
    sync_ticker_history(mem_session, "TST", FakeSourceRev())
    _, rows = get_reaction_summary_and_history(mem_session, "TST")
    # For 2026-05-01: yoy compared to 2025-05-01 (EPS 2.2 vs 2.0 -> +10%, Rev 105e9 vs 95e9 -> +10.53%)
    row_2026_05 = [r for r in rows if r["report_date"] == date(2026, 5, 1)][0]
    assert row_2026_05.get("eps_yoy") == pytest.approx(10.0)
    assert row_2026_05.get("revenue_yoy") == pytest.approx(10.526, abs=0.01)


def test_compute_yoy_math():
    from database.earnings_repo import compute_yoy
    assert round(compute_yoy(1.20, 1.00, min_base=0.05), 1) == 20.0
    assert compute_yoy(1.0, None, min_base=0.05) is None


# --- provenance & options availability ---

class FakeSourceMixedProvenance:
    def connect(self):
        return True
    def get_profile(self, symbol):
        return {"company_name": "Test", "market_cap": 1e9}
    def get_company_earnings(self, symbol):
        return [
            {"date": "2026-05-01", "symbol": symbol, "time": "amc",
             "eps": 2.2, "epsEstimate": 2.0, "revenue": 105e9, "revenueEstimate": 100e9},
            {"date": "2026-02-01", "symbol": symbol, "time": "amc",
             "eps": 1.8, "epsEstimate": 1.7, "revenue": 130e9, "revenueEstimate": 125e9},
        ]
    def get_earnings_reactions(self, symbol):
        return [
            {"date": "2026-05-01", "reactions": []},
            {"date": "2026-02-01", "eps": {"surprisePercent": 5.88, "yoy": 10.0, "beat": True},
             "revenue": {"surprisePercent": 4.0, "yoy": 8.3, "beat": True}, "reactions": []},
        ]

class FakeSourceNoRevenue:
    def connect(self):
        return True
    def get_profile(self, symbol):
        return {"company_name": "Test", "market_cap": 1e9}
    def get_company_earnings(self, symbol):
        return [
            {"date": "2026-05-01", "symbol": symbol, "time": "amc",
             "eps": 2.2, "epsEstimate": 2.0, "revenue": None, "revenueEstimate": None},
        ]
    def get_earnings_reactions(self, symbol):
        return [
            {"date": "2026-05-01", "reactions": []},
        ]

def test_reported_vs_computed_provenance(mem_session):
    from database.earnings_repo import sync_ticker_history, get_reaction_summary_and_history
    sync_ticker_history(mem_session, "TST", FakeSourceMixedProvenance())
    _, rows = get_reaction_summary_and_history(mem_session, "TST")
    provs = [r["provenance"] for r in rows]
    assert any(p.get("revenue_surprise_pct") == "reported" for p in provs if p)
    assert any(p.get("revenue_surprise_pct") == "computed" for p in provs if p)

def test_no_fabrication_when_inputs_missing(mem_session):
    from database.earnings_repo import sync_ticker_history, get_reaction_summary_and_history
    sync_ticker_history(mem_session, "TST", FakeSourceNoRevenue())
    _, rows = get_reaction_summary_and_history(mem_session, "TST")
    for r in rows:
        assert r["revenue_surprise_pct"] is None
        assert "revenue_surprise_pct" not in (r["provenance"] or {})

def test_prompt_tags_computed_values():
    from datetime import date
    from settings import AgentConfig
    from agents.huggingface_agents import QuantAgent
    from data.base import CompanyData
    c = CompanyData(ticker="TST", company_name="T", sector="X", industry="Y", market_cap=1e11,
        report_date=date(2026,7,23), consensus_eps=1.0, consensus_revenue=1e10,
        enriched_history=[{"report_date":"2026-04-23","eps_beat":True,"revenue_beat":True,
            "eps_actual":1.0,"eps_estimate":0.9,
            "eps_surprise_pct":10.0,"eps_yoy":45.0,"revenue_surprise_pct":2.0,"revenue_yoy":11.0,
            "reaction_1d_pct":4.2,
            "provenance":{"eps_surprise_pct":"reported","eps_yoy":"computed",
                          "revenue_surprise_pct":"reported","revenue_yoy":"computed"}}])
    p = QuantAgent(AgentConfig(provider="gemini", api_key="test"))._format_prompt(c, [])
    assert p.count("(computed)") >= 2
    assert "10.0% (computed)" not in p

def test_options_unavailable_not_rendered_as_live():
    from datetime import date
    from settings import AgentConfig
    from agents.huggingface_agents import QuantAgent
    from data.base import CompanyData
    c = CompanyData(ticker="TST", company_name="T", sector="X", industry="Y", market_cap=1e11,
        report_date=date(2026,7,23), consensus_eps=1.0, consensus_revenue=1e10,
        market_open=True, live_options=None, implied_move_pct=None)
    p = QuantAgent(AgentConfig(provider="gemini", api_key="test"))._format_prompt(c, [])
    assert "DATA UNAVAILABLE" in p
    assert "Implied move (straddle): 0.0%" not in p

def test_option_analytics_flags_unavailable_on_empty_chain():
    from unittest.mock import MagicMock
    from data.data_aggregator import DataAggregator
    from settings import load_config
    config = load_config()
    agg = DataAggregator(
        yahoo_config=config.yahoo,
        newsapi_config=config.newsapi,
        alphavantage_config=config.alphavantage,
        sec_config=config.sec,
        enable_yahoo=config.yahoo.enabled,
        enable_newsapi=config.newsapi.enabled,
        enable_alphavantage=config.alphavantage.enabled,
        enable_sec=config.sec.enabled,
    )
    agg.yahoo = MagicMock()
    agg.yahoo.get_option_chain.return_value = ([], {})
    agg._initialized = True
    res = agg.get_option_analytics("TST")
    assert res.get("available") is False
    assert res.get("implied_move", {}).get("straddle_implied_move_pct") is None


def _mk(opt_type, strike, exp, mid, underlying=50.0):
    from data.options import OptionData, OptionType
    return OptionData(ticker="TST", option_type=opt_type, strike=strike, expiration=exp,
                      underlying_price=underlying, bid=mid-0.05, ask=mid+0.05, last_price=mid,
                      mid_price=mid, volume=100, open_interest=100)

def test_implied_move_skips_0dte_and_uses_event_expiration():
    from datetime import date, timedelta
    from data.options import OptionChainAnalyzer, OptionType
    today = date.today()
    zero_dte = today                      # nearest weekly, must be SKIPPED (dte=0)
    event_exp = today + timedelta(days=10)  # first expiration after earnings, must be SELECTED
    earnings = today + timedelta(days=7)
    opts = []
    for exp, mid in [(zero_dte, 0.5), (event_exp, 2.0)]:
        for k in (48, 49, 50, 51, 52):
            opts.append(_mk(OptionType.CALL, k, exp, mid))
            opts.append(_mk(OptionType.PUT, k, exp, mid))
    im = OptionChainAnalyzer("TST", 50.0, opts).get_implied_move(earnings_date=earnings)
    assert im is not None, "valid straddle exists but calc returned None"
    assert im.days_to_expiry == 10, "did not select the post-earnings event expiration"
    # ATM straddle ~ 2.0 call + 2.0 put = 4.0 on a $50 underlying → ~8%
    assert 0.06 < im.implied_move_pct < 0.10

def test_implied_move_uses_bidask_when_mid_missing():
    from datetime import date, timedelta
    from data.options import OptionChainAnalyzer, OptionType, OptionData
    exp = date.today() + timedelta(days=14)
    def mk(t, k):
        return OptionData(ticker="TST", option_type=t, strike=k, expiration=exp, underlying_price=50.0,
                          bid=1.9, ask=2.1, last_price=None, mid_price=None, volume=10, open_interest=10)
    opts = [mk(OptionType.CALL, k) for k in (49,50,51)] + [mk(OptionType.PUT, k) for k in (49,50,51)]
    im = OptionChainAnalyzer("TST", 50.0, opts).get_implied_move()
    assert im is not None and im.implied_move_pct > 0, "bid/ask fallback not used"

def test_implied_move_none_only_when_truly_unusable():
    from datetime import date, timedelta
    from data.options import OptionChainAnalyzer, OptionType
    exp = date.today() + timedelta(days=5)
    calls_only = [_mk(OptionType.CALL, k, exp, 2.0) for k in (49,50,51,52)]  # no puts → no straddle
    assert OptionChainAnalyzer("TST", 50.0, calls_only).get_implied_move() is None


def test_put_call_ratio_has_total_aggregate():
    from datetime import date, timedelta
    from data.options import OptionChainAnalyzer, OptionType, OptionData
    exp = date.today() + timedelta(days=7)
    def mk(t, k, vol):
        return OptionData(ticker="TST", option_type=t, strike=k, expiration=exp, underlying_price=50.0,
                          bid=1.9, ask=2.1, last_price=2.0, mid_price=2.0, volume=vol, open_interest=vol*2)
    opts = [mk(OptionType.CALL, k, 100) for k in (49,50,51)] + [mk(OptionType.PUT, k, 150) for k in (49,50,51)]
    ratios = OptionChainAnalyzer("TST", 50.0, opts).get_put_call_ratios()
    assert "total" in ratios, "no aggregate 'total' key — consumer will read null"
    # 450 put volume / 300 call volume = 1.5
    assert abs(ratios["total"]["volume_ratio"] - 1.5) < 1e-6


