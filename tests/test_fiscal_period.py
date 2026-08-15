"""
Unit tests for database/fiscal_period.py — the reporting-period helpers backing
the history ledger's "Period" column and filter.
"""

import sys
import os
from datetime import date, datetime

import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.fiscal_period import (
    infer_fiscal_period,
    normalize_quarter,
    format_fiscal_period,
    parse_fiscal_period,
    resolve_fiscal_period,
)


@pytest.mark.parametrize(
    "report_date,expected",
    [
        # A company reporting in August is reporting the quarter that ended in June.
        (date(2026, 8, 13), ("Q2", 2026)),
        (date(2026, 7, 30), ("Q2", 2026)),
        (date(2026, 10, 28), ("Q3", 2026)),
        (date(2026, 4, 15), ("Q1", 2026)),
        # January/February reporters roll back into the prior calendar year.
        (date(2026, 1, 28), ("Q4", 2025)),
        (date(2026, 2, 3), ("Q4", 2025)),
    ],
)
def test_infer_fiscal_period_uses_reported_quarter_not_report_quarter(report_date, expected):
    assert infer_fiscal_period(report_date) == expected


def test_infer_fiscal_period_accepts_datetime_and_iso_string():
    assert infer_fiscal_period(datetime(2026, 8, 13, 16, 30)) == ("Q2", 2026)
    assert infer_fiscal_period("2026-08-13") == ("Q2", 2026)


def test_infer_fiscal_period_degrades_on_bad_input():
    assert infer_fiscal_period(None) == (None, None)
    assert infer_fiscal_period("not-a-date") == (None, None)


@pytest.mark.parametrize(
    "raw,expected",
    [("Q1", "Q1"), ("q3", "Q3"), (2, "Q2"), ("4", "Q4"), (" q1 ", "Q1")],
)
def test_normalize_quarter_accepts_common_shapes(raw, expected):
    assert normalize_quarter(raw) == expected


@pytest.mark.parametrize("raw", [None, "", "Q5", "0", "Q0", "banana"])
def test_normalize_quarter_rejects_invalid(raw):
    assert normalize_quarter(raw) is None


def test_format_fiscal_period():
    assert format_fiscal_period("Q1", 2026) == "2026Q1"
    assert format_fiscal_period("q3", 2025) == "2025Q3"
    # Missing or nonsensical parts yield no token rather than a broken one
    assert format_fiscal_period(None, 2026) is None
    assert format_fiscal_period("Q1", None) is None
    assert format_fiscal_period("Q9", 2026) is None
    assert format_fiscal_period("Q1", 0) is None


def test_parse_fiscal_period_roundtrips_format():
    assert parse_fiscal_period("2026Q1") == ("Q1", 2026)
    assert parse_fiscal_period(format_fiscal_period("Q4", 2025)) == ("Q4", 2025)
    assert parse_fiscal_period("2026q2") == ("Q2", 2026)


@pytest.mark.parametrize("raw", [None, "", "2026", "Q1", "abcQ1", "2026Q9"])
def test_parse_fiscal_period_rejects_invalid(raw):
    assert parse_fiscal_period(raw) == (None, None)


def test_resolve_prefers_earnings_history_over_hint_and_inference():
    """A matching EarningsHistory row wins over both the hint and the date heuristic."""

    class FakeRow:
        report_date = date(2026, 8, 13)
        fiscal_quarter = "Q3"      # deliberately disagrees with inference (Q2)
        fiscal_year = 2027         # MSFT-style offset fiscal year

    class FakeSession:
        def exec(self, _statement):
            class Result:
                @staticmethod
                def all():
                    return [FakeRow()]
            return Result()

    got = resolve_fiscal_period(
        FakeSession(), "MSFT", date(2026, 8, 13), hint_quarter="Q1", hint_year=2026
    )
    assert got == ("Q3", 2027)


def test_resolve_falls_back_to_hint_when_history_empty():
    class EmptySession:
        def exec(self, _statement):
            class Result:
                @staticmethod
                def all():
                    return []
            return Result()

    got = resolve_fiscal_period(
        EmptySession(), "AAPL", date(2026, 8, 13), hint_quarter="Q3", hint_year=2026
    )
    assert got == ("Q3", 2026)


def test_resolve_falls_back_to_inference_without_session_or_hint():
    assert resolve_fiscal_period(None, "AAPL", date(2026, 8, 13)) == ("Q2", 2026)
    # A blank/zero hint is not usable and must not suppress inference
    assert resolve_fiscal_period(
        None, "AAPL", date(2026, 8, 13), hint_quarter="", hint_year=0
    ) == ("Q2", 2026)


def test_resolve_survives_a_broken_session():
    """A DB failure must degrade to hint/inference rather than propagate."""

    class BrokenSession:
        def exec(self, _statement):
            raise RuntimeError("connection lost")

    assert resolve_fiscal_period(BrokenSession(), "AAPL", date(2026, 8, 13)) == ("Q2", 2026)


def test_resolve_returns_none_for_missing_report_date():
    assert resolve_fiscal_period(None, "AAPL", None) == (None, None)


if __name__ == "__main__":
    pytest.main(["-v", __file__])
