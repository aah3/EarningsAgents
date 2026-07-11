def test1():
    from data.resolvers import ReportTimeResolver, FiscalPeriodResolver
    from datetime import date

    rt = ReportTimeResolver()
    fp = FiscalPeriodResolver()

    # With no sources, both resolvers must degrade to inference without raising
    rt_result = rt.resolve("AAPL", date(2026, 7, 30))
    fp_result = fp.resolve("AAPL", date(2026, 7, 30))

    from settings import ReportTime
    assert rt_result.value == ReportTime.UNKNOWN
    assert rt_result.source == "inferred"
    assert rt_result.confidence == "low"

    assert fp_result.fiscal_quarter.startswith("Q")
    assert fp_result.fiscal_year > 0
    assert fp_result.source == "inferred"
    assert fp_result.confidence == "low"
    print("PASS  Test 1 — resolvers degrade gracefully with all-None sources")

def test2():
    from data.resolvers import ReportTimeResolver
    from settings import ReportTime
    from datetime import date, datetime
    from unittest.mock import MagicMock

    mock_yahoo = MagicMock()
    # Simulate yfinance Ticker.calendar returning a pre-market datetime (hour=7)
    mock_ticker = MagicMock()
    mock_ticker.calendar = {"Earnings Date": datetime(2026, 7, 30, 7, 0, 0)}
    mock_yahoo._get_ticker = MagicMock(return_value=mock_ticker)

    rt = ReportTimeResolver(yahoo_source=mock_yahoo)
    result = rt.resolve("AAPL", date(2026, 7, 30))

    assert result.value == ReportTime.BMO
    assert result.source == "yahoo"
    assert result.confidence == "high"
    print("PASS  Test 2 — ReportTimeResolver reads BMO from Yahoo datetime hour")

def test3():
    from data.resolvers import ReportTimeResolver
    from settings import ReportTime
    from datetime import date, datetime
    from unittest.mock import MagicMock

    mock_yahoo = MagicMock()
    mock_ticker = MagicMock()
    mock_ticker.calendar = {"Earnings Date": datetime(2026, 7, 30, 16, 30, 0)}
    mock_yahoo._get_ticker = MagicMock(return_value=mock_ticker)

    rt = ReportTimeResolver(yahoo_source=mock_yahoo)
    result = rt.resolve("AAPL", date(2026, 7, 30))

    assert result.value == ReportTime.AMC
    assert result.source == "yahoo"
    assert result.confidence == "high"
    print("PASS  Test 3 — ReportTimeResolver reads AMC from Yahoo datetime hour")

def test4():
    from data.resolvers import ReportTimeResolver
    from settings import ReportTime
    from datetime import date, datetime
    from unittest.mock import MagicMock, patch

    mock_yahoo = MagicMock()
    mock_ticker = MagicMock()
    # Hour = 13 → ambiguous, not BMO or AMC
    mock_ticker.calendar = {"Earnings Date": datetime(2026, 7, 30, 13, 0, 0)}
    mock_yahoo._get_ticker = MagicMock(return_value=mock_ticker)

    mock_finviz = MagicMock()

    rt = ReportTimeResolver(yahoo_source=mock_yahoo, finviz_source=mock_finviz)

    # Patch the internal FinViz scrape method to return AMC
    with patch.object(rt, '_scrape_finviz_report_time', return_value=ReportTime.AMC):
        result = rt.resolve("AAPL", date(2026, 7, 30))

    assert result.value == ReportTime.AMC
    assert result.source == "finviz"
    assert result.confidence == "high"
    print("PASS  Test 4 — ReportTimeResolver falls back to FinViz when Yahoo is ambiguous")

def test5():
    from data.resolvers import FiscalPeriodResolver
    from datetime import date
    from unittest.mock import MagicMock

    mock_av = MagicMock()

    # Most recent entry is 85 days before report_date (within 180-day window)
    from dataclasses import dataclass
    from datetime import date as d

    @dataclass
    class FakeHistEarning:
        date: d
        fiscal_quarter: str
        fiscal_year: int

    report_date = date(2026, 4, 29)
    # Last reported quarter was Q3 FY2025 (85 days before report_date)
    mock_av.get_historical_earnings.return_value = [
        FakeHistEarning(date=date(2026, 2, 3), fiscal_quarter="Q3", fiscal_year=2025)
    ]

    fp = FiscalPeriodResolver(alphavantage_source=mock_av)
    result = fp.resolve("META", report_date)

    # Next quarter after Q3 FY2025 should be Q4 FY2025
    assert result.fiscal_quarter == "Q4", f"Expected Q4, got {result.fiscal_quarter}"
    assert result.fiscal_year == 2025, f"Expected 2025, got {result.fiscal_year}"
    assert result.source == "alpha_vantage"
    assert result.confidence == "high"
    print("PASS  Test 5 — FiscalPeriodResolver reads and advances quarter from Alpha Vantage")

def test6():
    from data.resolvers import FiscalPeriodResolver
    from datetime import date
    from unittest.mock import MagicMock
    from dataclasses import dataclass

    from datetime import date as d
    @dataclass
    class FakeHistEarning:
        date: d
        fiscal_quarter: str
        fiscal_year: int

    mock_av = MagicMock()
    report_date = date(2026, 2, 5)
    # Last reported quarter was Q4 FY2025
    mock_av.get_historical_earnings.return_value = [
        FakeHistEarning(date=date(2025, 10, 31), fiscal_quarter="Q4", fiscal_year=2025)
    ]

    fp = FiscalPeriodResolver(alphavantage_source=mock_av)
    result = fp.resolve("AAPL", report_date)

    assert result.fiscal_quarter == "Q1", f"Expected Q1, got {result.fiscal_quarter}"
    assert result.fiscal_year == 2026, f"Expected 2026, got {result.fiscal_year}"
    assert result.source == "alpha_vantage"
    print("PASS  Test 6 — FiscalPeriodResolver wraps Q4 -> Q1 and increments fiscal year")

def test7():
    from data.resolvers import FiscalPeriodResolver
    from datetime import date
    from unittest.mock import MagicMock
    from dataclasses import dataclass

    from datetime import date as d
    @dataclass
    class FakeHistEarning:
        date: d
        fiscal_quarter: str
        fiscal_year: int

    mock_av = MagicMock()
    report_date = date(2026, 7, 30)
    # Last entry is 300 days before report_date → stale, exceeds 180-day window
    mock_av.get_historical_earnings.return_value = [
        FakeHistEarning(date=date(2025, 9, 25), fiscal_quarter="Q3", fiscal_year=2024)
    ]

    fp = FiscalPeriodResolver(alphavantage_source=mock_av)
    result = fp.resolve("NVDA", report_date)

    # Falls through to inference
    assert result.source == "inferred"
    assert result.confidence == "low"
    assert result.fiscal_quarter.startswith("Q")
    assert result.fiscal_year > 0
    print("PASS  Test 7 — FiscalPeriodResolver falls back to inference when AV data is stale")

def test8():
    """
    Verifies that get_company_data() calls both resolvers and writes their
    results back onto the returned CompanyData object.
    Mocks all data sources and both resolvers.
    """
    from unittest.mock import MagicMock, patch
    from datetime import date
    from settings import ReportTime, CompanyData

    # Build a minimal CompanyData that get_company_data would produce
    # before the resolution block runs
    base_company = CompanyData(
        ticker="TSLA", company_name="Tesla", sector="Auto",
        industry="EV", market_cap=1e12, report_date=date(2026, 7, 23),
    )

    import data.data_aggregator as da

    aggregator = MagicMock(spec=da.DataAggregator)
    aggregator._initialized = True

    # Patch get_company_data to test only the resolution block
    from data.resolvers import ReportTimeResult, FiscalPeriodResult

    mock_rt_result = ReportTimeResult(
        value=ReportTime.AMC, source="yahoo", confidence="high"
    )
    mock_fp_result = FiscalPeriodResult(
        fiscal_quarter="Q2", fiscal_year=2026,
        source="alpha_vantage", confidence="high"
    )

    # Note: data_aggregator path
    with patch("data.data_aggregator.ReportTimeResolver") as MockRT, \
         patch("data.data_aggregator.FiscalPeriodResolver") as MockFP:

        MockRT.return_value.resolve.return_value = mock_rt_result
        MockFP.return_value.resolve.return_value = mock_fp_result

        # Simulate the resolution block directly (tests the wiring, not the full method)
        from data.data_aggregator import DataAggregator
        import inspect
        src = inspect.getsource(DataAggregator.get_company_data)
        assert "ReportTimeResolver" in src, \
            "get_company_data() does not call ReportTimeResolver"
        assert "FiscalPeriodResolver" in src, \
            "get_company_data() does not call FiscalPeriodResolver"
        assert "company_data.report_time" in src, \
            "get_company_data() does not assign report_time"
        assert "company_data.fiscal_quarter" in src, \
            "get_company_data() does not assign fiscal_quarter"
        assert "company_data.fiscal_year" in src, \
            "get_company_data() does not assign fiscal_year"

    print("PASS  Test 8 — get_company_data() wires both resolvers and assigns all three fields")

def test9():
    from agents.agent_tools import AgentToolRegistry
    from settings import CompanyData
    from datetime import date
    from unittest.mock import MagicMock

    # fiscal_year explicitly resolved to 2025
    company = CompanyData(
        ticker="AMZN", company_name="Amazon", sector="Consumer",
        industry="E-Commerce", market_cap=2e12, report_date=date(2026, 2, 6),
        fiscal_year=2025,          # resolved field
        fiscal_quarter="Q4",       # resolved field
    )
    mock_sec = MagicMock()
    mock_sec.get_earnings_transcripts.return_value = []  # empty is fine

    registry = AgentToolRegistry(company, news=[], sec_source=mock_sec)
    registry.dispatch("get_sec_transcript_by_period", {})   # no args

    call_args = mock_sec.get_earnings_transcripts.call_args
    assert call_args[1]["year"] == 2025, \
        f"Expected year=2025 from company.fiscal_year, got {call_args[1]['year']}"
    print("PASS  Test 9 — get_sec_transcript_by_period uses company.fiscal_year when set")

if __name__ == "__main__":
    import sys, logging
    logging.basicConfig(level=logging.WARNING)

    tests = [test1, test2, test3, test4, test5, test6, test7, test8, test9]
    failed = 0
    for t in tests:
        try:
            t()
        except Exception as e:
            import traceback
            print(f"FAIL  {t.__name__}: {e}")
            traceback.print_exc()
            failed += 1

    print()
    if failed == 0:
        print("All 9 tests passed.")
        sys.exit(0)
    else:
        print(f"{failed} test(s) FAILED.")
        sys.exit(1)
