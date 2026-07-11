def test1():
    from settings import AgentConfig, load_config
    import os

    cfg = AgentConfig()
    assert hasattr(cfg, "sec_user_agent"), "AgentConfig missing sec_user_agent"
    assert "EarningsAgents" in cfg.sec_user_agent, \
        f"Unexpected default sec_user_agent: {cfg.sec_user_agent}"

    os.environ["SEC_USER_AGENT"] = "TestApp/2.0 (test@test.com)"
    loaded = load_config()
    assert loaded.agent.sec_user_agent == "TestApp/2.0 (test@test.com)", \
        f"load_config did not read SEC_USER_AGENT: {loaded.agent.sec_user_agent}"
    del os.environ["SEC_USER_AGENT"]
    print("PASS  Test 1 — AgentConfig.sec_user_agent and load_config")

def test2():
    from agents.agent_tools import AgentToolRegistry
    from settings import CompanyData
    from datetime import date

    company = CompanyData(
        ticker="AAPL", company_name="Apple", sector="Tech",
        industry="Consumer", market_cap=3e12, report_date=date(2026, 7, 30),
    )
    # Old call signature — must not raise
    r1 = AgentToolRegistry(company, news=[])
    assert r1.sec_source is None

    # New call signature with explicit None
    r2 = AgentToolRegistry(company, news=[], sec_source=None)
    assert r2.sec_source is None

    # New call signature with a mock
    from unittest.mock import MagicMock
    mock_sec = MagicMock()
    r3 = AgentToolRegistry(company, news=[], sec_source=mock_sec)
    assert r3.sec_source is mock_sec
    print("PASS  Test 2 — AgentToolRegistry backward-compatible sec_source param")

def test3():
    from agents.agent_tools import AgentToolRegistry, ToolResult
    from settings import CompanyData
    from datetime import date

    company = CompanyData(
        ticker="MSFT", company_name="Microsoft", sector="Tech",
        industry="Software", market_cap=3e12, report_date=date(2026, 7, 23),
    )
    registry = AgentToolRegistry(company, news=[])   # sec_source=None
    result = registry.dispatch("get_sec_transcript_by_period", {})

    assert isinstance(result, ToolResult)
    assert result.result is None
    assert result.error is not None
    assert "not available" in result.error.lower() or "sec edgar" in result.error.lower()
    print("PASS  Test 3 — get_sec_transcript_by_period returns error when sec_source=None")

def test4():
    from agents.agent_tools import AgentToolRegistry
    from settings import CompanyData
    from datetime import date
    from unittest.mock import MagicMock

    company = CompanyData(
        ticker="NVDA", company_name="Nvidia", sector="Tech",
        industry="Semiconductors", market_cap=3e12, report_date=date(2026, 4, 23),
    )
    mock_sec = MagicMock()
    registry = AgentToolRegistry(company, news=[], sec_source=mock_sec)

    # Invalid quarter value
    result = registry.dispatch("get_sec_transcript_by_period",
                               {"fiscal_quarter": "Q5"})
    assert result.error is not None
    assert "q5" in result.error.lower() or "invalid" in result.error.lower()

    # Valid quarter — mock returns empty list (no transcript found)
    mock_sec.get_earnings_transcripts.return_value = []
    result = registry.dispatch("get_sec_transcript_by_period",
                               {"fiscal_year": 2025, "fiscal_quarter": "Q4"})
    assert result.result is None
    assert result.error is not None
    assert "no transcript" in result.error.lower()
    print("PASS  Test 4 — get_sec_transcript_by_period validates fiscal_quarter")

def test5():
    from agents.agent_tools import AgentToolRegistry
    from settings import CompanyData
    from datetime import date
    from unittest.mock import MagicMock, patch

    company = CompanyData(
        ticker="META", company_name="Meta Platforms", sector="Comms",
        industry="Internet", market_cap=1.4e12, report_date=date(2026, 4, 29),
    )
    mock_sec = MagicMock()

    # Build a mock EarningsTranscript-like object
    mock_transcript = MagicMock()
    mock_transcript.ticker = "META"
    mock_transcript.fiscal_year = 2025
    mock_transcript.fiscal_quarter = "Q4"
    mock_transcript.date = date(2026, 1, 29)
    mock_transcript.full_text = "A" * 6000     # longer than default max_chars=4000
    mock_transcript.url = "https://sec.gov/fake"

    mock_sec.get_earnings_transcripts.return_value = [mock_transcript]

    registry = AgentToolRegistry(company, news=[], sec_source=mock_sec)
    result = registry.dispatch("get_sec_transcript_by_period",
                               {"fiscal_year": 2025, "fiscal_quarter": "Q4"})

    assert result.error is None, f"Unexpected error: {result.error}"
    r = result.result
    assert r["ticker"] == "META"
    assert r["fiscal_year"] == 2025
    assert r["fiscal_quarter"] == "Q4"
    assert r["filing_date"] == "2026-01-29"
    assert len(r["snippet"]) == 4000          # capped at max_chars
    assert r["truncated"] is True
    assert r["source"] == "SEC_EDGAR"
    assert r["url"] == "https://sec.gov/fake"

    # Verify SEC was called with correct args
    mock_sec.get_earnings_transcripts.assert_called_once_with(
        "META", year=2025, quarter="Q4"
    )
    print("PASS  Test 5 — get_sec_transcript_by_period returns correct structure")

def test6():
    from agents.agent_tools import AgentToolRegistry
    from settings import CompanyData
    from datetime import date
    from unittest.mock import MagicMock

    # report_date is 2026 → fiscal_year default should be 2025
    company = CompanyData(
        ticker="AMZN", company_name="Amazon", sector="Consumer",
        industry="E-Commerce", market_cap=2e12, report_date=date(2026, 2, 6),
    )
    mock_sec = MagicMock()
    mock_sec.get_earnings_transcripts.return_value = []  # empty is fine for this test

    registry = AgentToolRegistry(company, news=[], sec_source=mock_sec)
    registry.dispatch("get_sec_transcript_by_period", {})   # no args — use defaults

    call_args = mock_sec.get_earnings_transcripts.call_args
    assert call_args[1]["year"] == 2025, \
        f"Expected year=2025, got {call_args[1]['year']}"
    assert call_args[1]["quarter"] is None
    print("PASS  Test 6 — fiscal_year defaults to report_date.year - 1")

def test7():
    from agents.agent_tools import AgentToolRegistry
    from settings import CompanyData
    from datetime import date

    company = CompanyData(
        ticker="TSLA", company_name="Tesla", sector="Auto",
        industry="EVs", market_cap=1e12, report_date=date(2026, 4, 22),
    )
    registry = AgentToolRegistry(company, news=[])

    assert "get_sec_transcript_by_period" in registry._TOOL_MAP, \
        "get_sec_transcript_by_period missing from _TOOL_MAP"

    descriptions = registry.get_tool_descriptions()
    names = [d["name"] for d in descriptions]
    assert "get_sec_transcript_by_period" in names, \
        "get_sec_transcript_by_period missing from get_tool_descriptions()"

    desc_entry = next(d for d in descriptions if d["name"] == "get_sec_transcript_by_period")
    assert "fiscal_year" in desc_entry["description"]
    assert "fiscal_quarter" in desc_entry["description"]
    print("PASS  Test 7 — new tool registered in _TOOL_MAP and get_tool_descriptions()")

def test8():
    from unittest.mock import MagicMock
    import agents.huggingface_agents as ha
    ha.LLMClient = MagicMock

    from settings import AgentConfig
    cfg = AgentConfig()

    # BaseAgent subclasses
    for cls in [ha.BullAgent, ha.BearAgent, ha.QuantAgent, ha.ConsensusAgent]:
        agent = cls(cfg)
        assert hasattr(agent, "sec_source"), f"{cls.__name__} missing sec_source"
        assert agent.sec_source is None, f"{cls.__name__}.sec_source should default to None"

    # ThreeAgentSystem
    system = ha.ThreeAgentSystem(cfg)
    assert hasattr(system, "sec_source"), "ThreeAgentSystem missing sec_source"
    assert system.sec_source is None

    # Can be set externally without errors
    mock_sec = MagicMock()
    system.sec_source = mock_sec
    assert system.sec_source is mock_sec
    print("PASS  Test 8 — BaseAgent and ThreeAgentSystem expose sec_source=None")

if __name__ == "__main__":
    import sys, logging
    logging.basicConfig(level=logging.WARNING)

    tests = [test1, test2, test3, test4, test5, test6, test7, test8]
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
        print("All 8 tests passed.")
        sys.exit(0)
    else:
        print(f"{failed} test(s) FAILED.")
        sys.exit(1)
