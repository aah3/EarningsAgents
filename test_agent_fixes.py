"""
test_agent_fixes.py
Self-contained smoke test for the 8 bug fixes.
Run from the project root:  python test_agent_fixes.py
No live API credentials required.
"""


def test1():
    from settings import AgentConfig
    cfg = AgentConfig()
    assert hasattr(cfg, 'use_react'), "AgentConfig missing use_react"
    assert hasattr(cfg, 'react_max_turns'), "AgentConfig missing react_max_turns"
    assert cfg.use_react == False
    assert cfg.react_max_turns == 6
    cfg2 = AgentConfig(use_react=True, react_max_turns=8)
    assert cfg2.use_react == True
    assert cfg2.react_max_turns == 8
    print("PASS  Test 1 — AgentConfig.use_react and react_max_turns")


def test2():
    from settings import EarningsPrediction, PredictionDirection
    from datetime import date
    ep = EarningsPrediction(
        ticker="TEST", company_name="Test Co",
        report_date=date.today(), prediction_date=date.today(),
        direction=PredictionDirection.BEAT, confidence=75.0,
        rebuttal_summary="Bull refuted bear on margins.",
    )
    assert ep.rebuttal_summary == "Bull refuted bear on margins."
    ep2 = EarningsPrediction(
        ticker="T2", company_name="T2",
        report_date=date.today(), prediction_date=date.today(),
        direction=PredictionDirection.MISS, confidence=60.0,
    )
    assert ep2.rebuttal_summary is None   # default
    print("PASS  Test 2 — EarningsPrediction.rebuttal_summary")


def test3():
    from agent_tools import AgentToolRegistry, ToolResult
    from settings import CompanyData, ReportTime
    from datetime import date

    company = CompanyData(
        ticker="AAPL", company_name="Apple Inc.", sector="Tech",
        industry="Consumer Electronics", market_cap=3e12,
        report_date=date(2026, 7, 30),
        options_features={"put_call_volume_ratio": 0.85, "iv_skew": 0.02,
                          "net_gamma_exposure": 1234567.0, "max_pain_to_spot": 0.98},
        historical_eps=[{"date": "2025-Q4", "surprise_pct": 3.2},
                        {"date": "2025-Q3", "surprise_pct": -1.1}],
        estimate_revisions=[{"date": "2026-06-01", "direction": "up",
                              "old_estimate": 1.50, "new_estimate": 1.58}],
        company_facts={
            "NetIncome": {"value": 25e9, "period_end": "2025-12-31", "form": "10-K"},
            "Revenues":  4.5e11,        # raw scalar — should NOT crash
            "SomeStr":   "N/A",         # string fallback
        },
    )
    registry = AgentToolRegistry(company, news=[])

    # dispatch all tools and confirm no exceptions
    for tool_name in ["get_company_summary", "get_earnings_history", "get_estimate_revisions",
                      "get_options_signals", "get_price_momentum", "get_sec_transcript",
                      "get_sec_facts", "get_news_sentiment"]:
        result = registry.dispatch(tool_name, {})
        assert isinstance(result, ToolResult), f"{tool_name} did not return ToolResult"

    # unknown tool returns error, does not raise
    bad = registry.dispatch("nonexistent_tool", {})
    assert bad.error is not None
    print("PASS  Test 3 — AgentToolRegistry dispatches all tools without crash")


def test4():
    import importlib, sys
    # Remove any cached partial import
    for mod in list(sys.modules.keys()):
        if "huggingface_agents" in mod:
            del sys.modules[mod]
    import huggingface_agents as ha
    assert hasattr(ha, "ThreeAgentSystem")
    assert hasattr(ha, "BullAgent")
    assert hasattr(ha, "ConsensusAgent")
    assert hasattr(ha, "AgentResponseError")
    assert hasattr(ha, "ConsensusError")
    print("PASS  Test 4 — huggingface_agents imports without ModuleNotFoundError")


def test5():
    import inspect
    import huggingface_agents as ha

    src = inspect.getsource(ha.ThreeAgentSystem.predict)
    # The assignment line must read self.enable_rebuttals
    assert "do_rebuttals = self.enable_rebuttals" in src, \
        "predict() still reads do_rebuttals from self.config"
    # Must NOT contain the old broken read (excluding docstring lines)
    code_lines = [l for l in src.splitlines()
                  if "``" not in l and not l.strip().startswith("#")]
    assert not any("self.config.enable_rebuttals" in l for l in code_lines), \
        "predict() still contains self.config.enable_rebuttals in executable code"
    print("PASS  Test 5 — ThreeAgentSystem.predict reads self.enable_rebuttals")


def test6():
    import huggingface_agents as ha
    from settings import AgentConfig, CompanyData, NewsArticle, ReportTime
    from datetime import date
    from unittest.mock import MagicMock

    # Patch LLMClient so no API key is needed
    ha.LLMClient = MagicMock

    agent = ha.BullAgent.__new__(ha.BullAgent)
    agent.config = AgentConfig()
    agent.system_prompt = ha.BULL_PROMPT
    agent.logger = __import__("logging").getLogger("test")
    agent.llm = MagicMock()

    company = CompanyData(
        ticker="MSFT", company_name="Microsoft Corp.", sector="Tech",
        industry="Software", market_cap=3.1e12, report_date=date(2026, 7, 23),
        company_facts={
            "NetIncome": {"value": 72e9, "period_end": "2025-12-31", "form": "10-K"},
            "Revenues":  2.45e11,          # raw float — previously caused AttributeError
            "OtherItem": "not a number",   # string fallback
            "NullItem":  None,             # None scalar
        },
    )
    # Must not raise
    prompt = agent._format_prompt(company, news=[])
    assert "MSFT" in prompt
    assert "$72.00B" in prompt        # dict fact formatted correctly
    assert "$245.00B" in prompt       # raw float formatted correctly
    assert "not a number" in prompt   # string passed through
    print("PASS  Test 6 — _format_prompt handles mixed company_facts value types")


def test7():
    import llm_client as lc
    import inspect

    src = inspect.getsource(lc.LLMClient._stream_anthropic)
    # Must contain the early-exit guard for tool_choice
    assert '"tools" in kwargs and "tool_choice" in kwargs' in src or \
           "'tools' in kwargs and 'tool_choice' in kwargs" in src, \
        "_stream_anthropic missing tool_choice fallback guard"
    # Must delegate to _call_anthropic, not open a stream directly
    assert "_call_anthropic" in src, \
        "_stream_anthropic does not fall back to _call_anthropic for tool-use"
    print("PASS  Test 7 — _stream_anthropic has tool-use streaming fallback")


def test8():
    import huggingface_agents as ha
    from settings import AgentConfig, CompanyData
    from datetime import date
    from unittest.mock import MagicMock

    ha.LLMClient = MagicMock

    agent = ha.ConsensusAgent.__new__(ha.ConsensusAgent)
    agent.config = AgentConfig()
    agent.system_prompt = ha.CONSENSUS_PROMPT
    agent.logger = __import__("logging").getLogger("test")
    agent.llm = MagicMock()

    company = CompanyData(
        ticker="TEST", company_name="Test Co.", sector="X", industry="Y",
        market_cap=1e9, report_date=date.today(),
    )
    try:
        agent.synthesize(company, bull_response=None, bear_response=None, quant_response=None)
        assert False, "Should have raised ConsensusError"
    except ha.ConsensusError:
        pass
    print("PASS  Test 8 — ConsensusAgent.synthesize raises ConsensusError with 0 agents")


if __name__ == "__main__":
    import sys
    import logging
    logging.basicConfig(level=logging.WARNING)   # suppress agent loggers during test

    tests = [test1, test2, test3, test4, test5, test6, test7, test8]
    failed = 0
    for t in tests:
        try:
            t()
        except Exception as e:
            print(f"FAIL  {t.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print()
    if failed == 0:
        print("All 8 tests passed.")
        sys.exit(0)
    else:
        print(f"{failed} test(s) FAILED.")
        sys.exit(1)
