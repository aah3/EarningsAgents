"""
Integration tests for the paginated GET /earnings/history endpoint and its
companion GET /earnings/history/filters.

Covers paging, each filter dimension, sorting, validation, and the invariant
that `stats` are computed over the whole filtered set rather than the page.
"""

import sys
import os
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set ENV=dev for test_ clerk bearer authentication bypass
os.environ["ENV"] = "dev"

from main_api import app
from database.db import engine, init_db
from database.models import Prediction, CompanyProfile

init_db()  # TestClient() alone doesn't trigger the FastAPI lifespan
client = TestClient(app)

HEADERS = {"Authorization": "Bearer test_history_pagination_user"}

# All fixture rows share this ticker prefix so cleanup can't touch real data.
TICKER_PREFIX = "ZZTST"


def _mk(ticker, report_date, direction, confidence, actual_direction=None,
        brier=None, fiscal_quarter="Q2", fiscal_year=2026):
    return Prediction(
        ticker=ticker,
        company_name=f"{ticker} Test Corp",
        report_date=report_date,
        report_timing="AMC",
        fiscal_quarter=fiscal_quarter,
        fiscal_year=fiscal_year,
        direction=direction,
        confidence=confidence,
        reasoning_summary="fixture",
        bull_factors=[],
        bear_factors=[],
        actual_direction=actual_direction,
        accuracy_score=brier,
    )


@pytest.fixture(scope="module", autouse=True)
def seeded_rows():
    """
    Seed a known set of predictions, yield, then remove them.

    Composition (12 rows):
      - 8 BEAT, 3 MISS, 1 INLINE
      - 9 scored (5 correct, 4 wrong), 3 unverified
      - periods: 9x 2026Q2, 2x 2026Q1, 1x 2025Q4
      - sectors: 6x Technology (ZZTSTA), 6x Health Care (ZZTSTB)
    """
    base = datetime(2026, 8, 12)
    rows = [
        # ── ZZTSTA* : Technology ──────────────────────────────────────────────
        _mk(f"{TICKER_PREFIX}A1", base, "BEAT", 0.80, "beat", 0.04),      # correct
        _mk(f"{TICKER_PREFIX}A2", base, "BEAT", 0.70, "miss", 0.49),      # wrong
        _mk(f"{TICKER_PREFIX}A3", base, "MISS", 0.60, "miss", 0.16),      # correct
        _mk(f"{TICKER_PREFIX}A4", base, "BEAT", 0.90, None, None),        # unverified
        _mk(f"{TICKER_PREFIX}A5", base - timedelta(days=1), "BEAT", 0.75, "beat", 0.0625),
        _mk(f"{TICKER_PREFIX}A6", base - timedelta(days=1), "INLINE", 0.55, "beat", 0.30),  # wrong
        # ── ZZTSTB* : Health Care ─────────────────────────────────────────────
        _mk(f"{TICKER_PREFIX}B1", base, "MISS", 0.65, "beat", 0.42),      # wrong
        _mk(f"{TICKER_PREFIX}B2", base, "BEAT", 0.85, "beat", 0.0225),    # correct
        _mk(f"{TICKER_PREFIX}B3", base, "BEAT", 0.50, None, None),        # unverified
        _mk(f"{TICKER_PREFIX}B4", datetime(2026, 5, 6), "BEAT", 0.72, "beat", 0.0784,
            fiscal_quarter="Q1", fiscal_year=2026),
        _mk(f"{TICKER_PREFIX}B5", datetime(2026, 5, 6), "MISS", 0.68, "beat", 0.46,
            fiscal_quarter="Q1", fiscal_year=2026),                        # wrong
        _mk(f"{TICKER_PREFIX}B6", datetime(2026, 2, 4), "BEAT", 0.77, None, None,
            fiscal_quarter="Q4", fiscal_year=2025),                        # unverified
    ]

    profiles = [
        CompanyProfile(ticker=f"{TICKER_PREFIX}A{i}", company_name="T", sector="Technology")
        for i in range(1, 7)
    ] + [
        CompanyProfile(ticker=f"{TICKER_PREFIX}B{i}", company_name="H", sector="Health Care")
        for i in range(1, 7)
    ]

    with Session(engine) as session:
        for r in rows:
            session.add(r)
        for p in profiles:
            existing = session.get(CompanyProfile, p.ticker)
            if not existing:
                session.add(p)
        session.commit()

    yield

    with Session(engine) as session:
        for p in session.exec(
            select(Prediction).where(Prediction.ticker.like(f"{TICKER_PREFIX}%"))
        ).all():
            session.delete(p)
        for c in session.exec(
            select(CompanyProfile).where(CompanyProfile.ticker.like(f"{TICKER_PREFIX}%"))
        ).all():
            session.delete(c)
        session.commit()


def get_history(**params):
    """Query the endpoint scoped to the fixture rows via the search filter."""
    params.setdefault("q", TICKER_PREFIX)
    resp = client.get("/earnings/history", params=params, headers=HEADERS)
    assert resp.status_code == 200, resp.text
    return resp.json()


# ── Envelope & paging ────────────────────────────────────────────────────────

def test_response_envelope_shape():
    data = get_history()
    for key in ("items", "total", "limit", "offset", "stats"):
        assert key in data, f"missing '{key}' in response"
    assert data["total"] == 12
    assert isinstance(data["items"], list)


def test_default_page_size_is_ten():
    data = get_history()
    assert data["limit"] == 10
    assert len(data["items"]) == 10, "default page should return at most 10 rows"
    assert data["total"] == 12, "total must reflect the full filtered set, not the page"


def test_paging_covers_every_row_exactly_once():
    seen = []
    offset = 0
    while True:
        data = get_history(limit=5, offset=offset)
        if not data["items"]:
            break
        seen.extend(item["id"] for item in data["items"])
        offset += 5
    assert len(seen) == 12
    assert len(set(seen)) == 12, "paging returned duplicate rows"


def test_offset_past_end_returns_empty_page_not_error():
    data = get_history(limit=10, offset=500)
    assert data["items"] == []
    assert data["total"] == 12


# ── Stats are computed over the full filtered set ────────────────────────────

def test_stats_reflect_full_filtered_set_not_current_page():
    """The KPI cards must not change as the user pages through results."""
    page1 = get_history(limit=3, offset=0)
    page3 = get_history(limit=3, offset=6)
    assert page1["stats"] == page3["stats"]

    stats = page1["stats"]
    assert stats["total"] == 12
    assert stats["scored_count"] == 9
    assert stats["correct_count"] == 5
    assert stats["win_rate"] == pytest.approx(5 / 9)


def test_stats_follow_the_active_filters():
    all_stats = get_history()["stats"]
    tech_stats = get_history(sector="Technology")["stats"]
    assert tech_stats["total"] == 6
    assert tech_stats["total"] < all_stats["total"]
    assert tech_stats["scored_count"] == 5


def test_avg_brier_averages_over_scored_rows_only():
    stats = get_history()["stats"]
    expected = (0.04 + 0.49 + 0.16 + 0.0625 + 0.30 + 0.42 + 0.0225 + 0.0784 + 0.46) / 9
    assert stats["avg_brier"] == pytest.approx(expected)


def test_stats_are_null_when_nothing_is_scored():
    stats = get_history(status="PENDING")["stats"]
    assert stats["scored_count"] == 0
    assert stats["win_rate"] is None
    assert stats["avg_brier"] is None


# ── Filters ──────────────────────────────────────────────────────────────────

def test_prediction_filter_buckets_inline_directions():
    assert get_history(prediction="BEAT")["total"] == 8
    assert get_history(prediction="MISS")["total"] == 3
    assert get_history(prediction="INLINE")["total"] == 1


def test_outcome_filter_partitions_the_set():
    correct = get_history(outcome="CORRECT")["total"]
    wrong = get_history(outcome="WRONG")["total"]
    unverified = get_history(outcome="UNVERIFIED")["total"]
    assert (correct, wrong, unverified) == (5, 4, 3)
    assert correct + wrong + unverified == 12


def test_status_filter_partitions_the_set():
    scored = get_history(status="SCORED")["total"]
    pending = get_history(status="PENDING")["total"]
    assert (scored, pending) == (9, 3)
    assert scored + pending == 12


def test_sector_filter():
    assert get_history(sector="Technology")["total"] == 6
    assert get_history(sector="Health Care")["total"] == 6


def test_fiscal_period_filter():
    assert get_history(fiscal_period="2026Q2")["total"] == 9
    assert get_history(fiscal_period="2026Q1")["total"] == 2
    assert get_history(fiscal_period="2025Q4")["total"] == 1


def test_report_date_filter():
    data = get_history(report_date="2026-05-06")
    assert data["total"] == 2
    assert {i["ticker"] for i in data["items"]} == {f"{TICKER_PREFIX}B4", f"{TICKER_PREFIX}B5"}


def test_search_matches_ticker_and_company_case_insensitively():
    assert get_history(q=f"{TICKER_PREFIX.lower()}a1")["total"] == 1
    # company_name is "<TICKER> Test Corp" for every fixture row
    assert get_history(q="test corp")["total"] >= 12


def test_filters_compose():
    data = get_history(sector="Technology", prediction="BEAT", status="SCORED")
    assert data["total"] == 3
    for item in data["items"]:
        assert item["sector"] == "Technology"
        assert item["direction"] == "BEAT"
        assert item["actual_direction"] is not None


def test_all_sentinel_is_treated_as_no_filter():
    assert get_history(prediction="ALL", outcome="ALL", sector="ALL",
                       fiscal_period="ALL", status="ALL")["total"] == 12


# ── Sorting ──────────────────────────────────────────────────────────────────

def test_sort_by_confidence_both_directions():
    asc = [i["confidence"] for i in get_history(sort_by="confidence", sort_dir="asc", limit=12)["items"]]
    desc = [i["confidence"] for i in get_history(sort_by="confidence", sort_dir="desc", limit=12)["items"]]
    assert asc == sorted(asc)
    assert desc == sorted(desc, reverse=True)


def test_sort_by_fiscal_period_orders_by_year_then_quarter():
    items = get_history(sort_by="fiscal_period", sort_dir="asc", limit=12)["items"]
    periods = [i["fiscal_period"] for i in items]
    assert periods[0] == "2025Q4", "oldest period should sort first ascending"
    assert periods[-1] == "2026Q2"
    assert periods == sorted(periods), "lexical order matches chronological for YYYYQn"


def test_sort_by_ticker():
    tickers = [i["ticker"] for i in get_history(sort_by="ticker", sort_dir="asc", limit=12)["items"]]
    assert tickers == sorted(tickers)


# ── Row payload ──────────────────────────────────────────────────────────────

def test_items_carry_formatted_fiscal_period_and_joined_sector():
    data = get_history(q=f"{TICKER_PREFIX}A1")
    item = data["items"][0]
    assert item["fiscal_period"] == "2026Q2"
    assert item["fiscal_quarter"] == "Q2"
    assert item["fiscal_year"] == 2026
    assert item["sector"] == "Technology"


# ── Validation ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "params",
    [
        {"sort_by": "; DROP TABLE prediction"},
        {"sort_by": "unknown_column"},
        {"sort_dir": "sideways"},
        {"fiscal_period": "not-a-period"},
        {"fiscal_period": "2026Q7"},
        {"report_date": "13-13-2026"},
        {"limit": 0},
        {"limit": 100000},
        {"offset": -1},
    ],
)
def test_invalid_params_are_rejected_with_422(params):
    resp = client.get("/earnings/history", params=params, headers=HEADERS)
    assert resp.status_code == 422, f"{params} -> {resp.status_code}: {resp.text}"


def test_history_requires_authentication():
    resp = client.get("/earnings/history")
    assert resp.status_code in (401, 403), resp.text


# ── Filter options endpoint ──────────────────────────────────────────────────

def test_filters_endpoint_returns_distinct_options_over_whole_table():
    resp = client.get("/earnings/history/filters", headers=HEADERS)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert set(data) == {"sectors", "fiscal_periods", "report_dates"}
    assert "Technology" in data["sectors"]
    assert "Health Care" in data["sectors"]
    assert len(data["sectors"]) == len(set(data["sectors"])), "sectors must be distinct"

    for period in ("2026Q2", "2026Q1", "2025Q4"):
        assert period in data["fiscal_periods"]
    # Newest first so the dropdown opens on recent periods
    assert data["fiscal_periods"] == sorted(data["fiscal_periods"], reverse=True)
    assert data["report_dates"] == sorted(data["report_dates"], reverse=True)


def test_filters_route_is_not_shadowed_by_the_ticker_route():
    """/history/filters must not be parsed as /history/{ticker}."""
    resp = client.get("/earnings/history/filters", headers=HEADERS)
    assert resp.status_code == 200
    assert "sectors" in resp.json(), "route resolved to the per-ticker history handler"


if __name__ == "__main__":
    pytest.main(["-v", __file__])
