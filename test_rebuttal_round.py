import unittest
import inspect
import huggingface_agents as ha

def test1():
    src = inspect.getsource(ha.ThreeAgentSystem.predict)

    # The assignment must read from self directly
    assert "do_rebuttals = self.enable_rebuttals" in src, \
        "predict() still reads do_rebuttals from self.config"

    # Must NOT contain the old broken read in executable code
    code_lines = [
        l for l in src.splitlines()
        if "``" not in l and not l.strip().startswith("#")
    ]
    assert not any("self.config.enable_rebuttals" in l for l in code_lines), \
        "predict() still contains self.config.enable_rebuttals in executable code"

    print("PASS  Test 1 — do_rebuttals reads self.enable_rebuttals")

def test2():
    src = inspect.getsource(ha.ThreeAgentSystem.predict)

    assert "time.sleep" not in src, \
        "time.sleep() still present in predict() — latency bug not fixed"

    print("PASS  Test 2 — time.sleep removed from rebuttal block")

def test3():
    from unittest.mock import MagicMock
    ha.LLMClient = MagicMock

    from settings import AgentConfig
    cfg = AgentConfig()

    system_off = ha.ThreeAgentSystem(cfg, enable_rebuttals=False)
    assert system_off.enable_rebuttals is False

    system_on = ha.ThreeAgentSystem(cfg, enable_rebuttals=True)
    assert system_on.enable_rebuttals is True

    print("PASS  Test 3 — enable_rebuttals stored correctly on ThreeAgentSystem")

def test4():
    from unittest.mock import MagicMock, patch
    from datetime import date
    ha.LLMClient = MagicMock

    from settings import AgentConfig, CompanyData, PredictionDirection

    cfg = AgentConfig()
    system = ha.ThreeAgentSystem(cfg, enable_rebuttals=False)

    mock_response = ha.AgentResponse(
        direction=PredictionDirection.BEAT,
        confidence=75.0,
        expected_price_move="positive",
        move_vs_implied="inside implied move",
        guidance_expectation="positive",
        reasoning="Strong beat signals.",
        bull_factors=["Factor A"],
        bear_factors=["Risk B"],
        key_signals={"deciding_factor": "momentum", "bull_strength": "7",
                     "bear_strength": "4", "estimate_momentum": "up",
                     "beat_rate": "75%", "estimate_risk": "low",
                     "headwinds": "none", "beat_probability": "75%",
                     "historical_beat_rate": "3/4", "revision_trend": "up"},
    )

    company = CompanyData(
        ticker="AAPL", company_name="Apple", sector="Tech",
        industry="Consumer", market_cap=3e12, report_date=date(2026, 7, 30),
    )

    rebuttal_analyze_calls = []

    def fake_rebuttal_analyze(*args, **kwargs):
        rebuttal_analyze_calls.append(1)
        return mock_response

    with patch.object(ha.BullAgent, 'analyze', return_value=mock_response), \
         patch.object(ha.BearAgent, 'analyze', return_value=mock_response), \
         patch.object(ha.QuantAgent, 'analyze', return_value=mock_response), \
         patch.object(ha.ConsensusAgent, 'synthesize', return_value=mock_response), \
         patch.object(ha.BullAgent, 'rebuttal_analyze', side_effect=fake_rebuttal_analyze), \
         patch.object(ha.BearAgent, 'rebuttal_analyze', side_effect=fake_rebuttal_analyze):

        system.predict(company, news=[], prediction_date=date(2026, 7, 29))

    assert len(rebuttal_analyze_calls) == 0, \
        f"rebuttal_analyze was called {len(rebuttal_analyze_calls)} times with enable_rebuttals=False"

    print("PASS  Test 4 — rebuttal_analyze never called when enable_rebuttals=False")

def test5():
    from unittest.mock import MagicMock, patch
    from datetime import date
    ha.LLMClient = MagicMock

    from settings import AgentConfig, CompanyData, PredictionDirection

    cfg = AgentConfig()
    system = ha.ThreeAgentSystem(cfg, enable_rebuttals=True)

    mock_response = ha.AgentResponse(
        direction=PredictionDirection.BEAT,
        confidence=75.0,
        expected_price_move="positive",
        move_vs_implied="inside implied move",
        guidance_expectation="positive",
        reasoning="Strong beat signals.",
        bull_factors=["Factor A"],
        bear_factors=["Risk B"],
        key_signals={"deciding_factor": "momentum", "bull_strength": "7",
                     "bear_strength": "4", "estimate_momentum": "up",
                     "beat_rate": "75%", "estimate_risk": "low",
                     "headwinds": "none", "beat_probability": "75%",
                     "historical_beat_rate": "3/4", "revision_trend": "up"},
    )

    company = CompanyData(
        ticker="MSFT", company_name="Microsoft", sector="Tech",
        industry="Software", market_cap=3e12, report_date=date(2026, 7, 30),
    )

    rebuttal_calls = {"bull": 0, "bear": 0}

    def bull_rebuttal(*args, **kwargs):
        rebuttal_calls["bull"] += 1
        return mock_response

    def bear_rebuttal(*args, **kwargs):
        rebuttal_calls["bear"] += 1
        return mock_response

    with patch.object(ha.BullAgent, 'analyze', return_value=mock_response), \
         patch.object(ha.BearAgent, 'analyze', return_value=mock_response), \
         patch.object(ha.QuantAgent, 'analyze', return_value=mock_response), \
         patch.object(ha.ConsensusAgent, 'synthesize', return_value=mock_response), \
         patch.object(ha.BullAgent, 'rebuttal_analyze', side_effect=bull_rebuttal), \
         patch.object(ha.BearAgent, 'rebuttal_analyze', side_effect=bear_rebuttal):

        result = system.predict(company, news=[], prediction_date=date(2026, 7, 29))

    assert rebuttal_calls["bull"] == 1, \
        f"Bull rebuttal_analyze called {rebuttal_calls['bull']} times, expected 1"
    assert rebuttal_calls["bear"] == 1, \
        f"Bear rebuttal_analyze called {rebuttal_calls['bear']} times, expected 1"

    print("PASS  Test 5 — both rebuttal_analyze calls fire when enable_rebuttals=True")

def test6():
    from unittest.mock import MagicMock, patch
    from datetime import date
    ha.LLMClient = MagicMock

    from settings import AgentConfig, CompanyData, PredictionDirection

    cfg = AgentConfig()
    company = CompanyData(
        ticker="NVDA", company_name="Nvidia", sector="Tech",
        industry="Semiconductors", market_cap=3e12, report_date=date(2026, 5, 28),
    )

    base_response = ha.AgentResponse(
        direction=PredictionDirection.BEAT, confidence=80.0,
        expected_price_move="positive", move_vs_implied="inside implied move",
        guidance_expectation="positive", reasoning="Beat signals strong.",
        bull_factors=["GPU demand"], bear_factors=["Supply risk"],
        key_signals={"deciding_factor": "demand", "bull_strength": "8",
                     "bear_strength": "3", "estimate_momentum": "up",
                     "beat_rate": "80%", "estimate_risk": "low",
                     "headwinds": "minor", "beat_probability": "80%",
                     "historical_beat_rate": "4/4", "revision_trend": "up"},
    )

    # --- Without rebuttals ---
    system_off = ha.ThreeAgentSystem(cfg, enable_rebuttals=False)
    with patch.object(ha.BullAgent, 'analyze', return_value=base_response), \
         patch.object(ha.BearAgent, 'analyze', return_value=base_response), \
         patch.object(ha.QuantAgent, 'analyze', return_value=base_response), \
         patch.object(ha.ConsensusAgent, 'synthesize', return_value=base_response):
        result_off = system_off.predict(company, news=[])

    assert result_off.rebuttal_summary is None, \
        "rebuttal_summary should be None when rebuttals disabled"

    # --- With rebuttals ---
    rebuttal_response = ha.AgentResponse(
        direction=PredictionDirection.BEAT, confidence=82.0,
        expected_price_move="positive", move_vs_implied="inside implied move",
        guidance_expectation="positive",
        reasoning="Bear's supply argument overstated; demand is robust.",
        bull_factors=["Sustained demand"], bear_factors=["Supply conceded minor"],
        key_signals={"deciding_factor": "demand", "bull_strength": "8",
                     "bear_strength": "3", "estimate_momentum": "up",
                     "beat_rate": "80%", "estimate_risk": "low",
                     "headwinds": "minor", "beat_probability": "82%",
                     "historical_beat_rate": "4/4", "revision_trend": "up"},
    )

    system_on = ha.ThreeAgentSystem(cfg, enable_rebuttals=True)
    with patch.object(ha.BullAgent, 'analyze', return_value=base_response), \
         patch.object(ha.BearAgent, 'analyze', return_value=base_response), \
         patch.object(ha.QuantAgent, 'analyze', return_value=base_response), \
         patch.object(ha.ConsensusAgent, 'synthesize', return_value=base_response), \
         patch.object(ha.BullAgent, 'rebuttal_analyze', return_value=rebuttal_response), \
         patch.object(ha.BearAgent, 'rebuttal_analyze', return_value=rebuttal_response):
        result_on = system_on.predict(company, news=[])

    assert result_on.rebuttal_summary is not None, \
        "rebuttal_summary should be populated when rebuttals ran"
    assert "REBUTTAL" in result_on.rebuttal_summary.upper(), \
        "rebuttal_summary should contain 'REBUTTAL' header"
    assert "Bear's supply argument overstated" in result_on.rebuttal_summary or \
           "BULL REBUTTAL" in result_on.rebuttal_summary, \
        "rebuttal_summary should contain rebuttal content"

    print("PASS  Test 6 — rebuttal_summary is None without rebuttals, populated with them")

def test7():
    from unittest.mock import MagicMock, patch, call
    from datetime import date
    ha.LLMClient = MagicMock

    from settings import AgentConfig, CompanyData, PredictionDirection

    cfg = AgentConfig()
    system = ha.ThreeAgentSystem(cfg, enable_rebuttals=True)

    base_response = ha.AgentResponse(
        direction=PredictionDirection.BEAT, confidence=75.0,
        expected_price_move="positive", move_vs_implied="inside implied move",
        guidance_expectation="positive", reasoning="Base thesis.",
        bull_factors=["F1"], bear_factors=["R1"],
        key_signals={"deciding_factor": "x", "bull_strength": "7",
                     "bear_strength": "4", "estimate_momentum": "up",
                     "beat_rate": "75%", "estimate_risk": "low",
                     "headwinds": "none", "beat_probability": "75%",
                     "historical_beat_rate": "3/4", "revision_trend": "up"},
    )
    bull_reb = ha.AgentResponse(**{**base_response.__dict__, "reasoning": "Bull rebuttal reasoning."})
    bear_reb = ha.AgentResponse(**{**base_response.__dict__, "reasoning": "Bear rebuttal reasoning."})

    company = CompanyData(
        ticker="AMZN", company_name="Amazon", sector="Consumer",
        industry="E-Commerce", market_cap=2e12, report_date=date(2026, 2, 6),
    )

    synthesize_calls = []

    def capture_synthesize(*args, **kwargs):
        synthesize_calls.append(kwargs)
        return base_response

    with patch.object(ha.BullAgent, 'analyze', return_value=base_response), \
         patch.object(ha.BearAgent, 'analyze', return_value=base_response), \
         patch.object(ha.QuantAgent, 'analyze', return_value=base_response), \
         patch.object(ha.ConsensusAgent, 'synthesize', side_effect=capture_synthesize), \
         patch.object(ha.BullAgent, 'rebuttal_analyze', return_value=bull_reb), \
         patch.object(ha.BearAgent, 'rebuttal_analyze', return_value=bear_reb):
        system.predict(company, news=[])

    assert len(synthesize_calls) == 1, "synthesize should be called exactly once"
    kwargs = synthesize_calls[0]
    assert kwargs.get("bull_rebuttal") is bull_reb, \
        "synthesize did not receive bull_rebuttal"
    assert kwargs.get("bear_rebuttal") is bear_reb, \
        "synthesize did not receive bear_rebuttal"

    print("PASS  Test 7 — ConsensusAgent.synthesize receives both rebuttal responses")

def test8():
    from unittest.mock import MagicMock, patch
    from datetime import date
    ha.LLMClient = MagicMock

    from settings import AgentConfig, CompanyData, PredictionDirection

    cfg = AgentConfig()
    system = ha.ThreeAgentSystem(cfg, enable_rebuttals=True)

    base_response = ha.AgentResponse(
        direction=PredictionDirection.MISS, confidence=65.0,
        expected_price_move="negative", move_vs_implied="inside implied move",
        guidance_expectation="negative", reasoning="Miss signals.",
        bull_factors=[], bear_factors=["Risk A"],
        key_signals={"deciding_factor": "risk", "bull_strength": "3",
                     "bear_strength": "7", "estimate_momentum": "down",
                     "beat_rate": "25%", "estimate_risk": "high",
                     "headwinds": "macro", "beat_probability": "25%",
                     "historical_beat_rate": "1/4", "revision_trend": "down"},
    )

    company = CompanyData(
        ticker="INTC", company_name="Intel", sector="Tech",
        industry="Semiconductors", market_cap=9e10, report_date=date(2026, 4, 24),
    )

    rebuttal_called = []

    def fail_bull(*args, **kwargs):
        raise ha.AgentResponseError(agent="BullAgent", cause=Exception("Network timeout"))

    with patch.object(ha.BullAgent, 'analyze', side_effect=fail_bull), \
         patch.object(ha.BearAgent, 'analyze', return_value=base_response), \
         patch.object(ha.QuantAgent, 'analyze', return_value=base_response), \
         patch.object(ha.ConsensusAgent, 'synthesize', return_value=base_response), \
         patch.object(ha.BullAgent, 'rebuttal_analyze',
                      side_effect=lambda *a, **kw: rebuttal_called.append(1) or base_response), \
         patch.object(ha.BearAgent, 'rebuttal_analyze',
                      side_effect=lambda *a, **kw: rebuttal_called.append(1) or base_response):
        result = system.predict(company, news=[])

    assert len(rebuttal_called) == 0, \
        "Rebuttal should be skipped when Bull failed in Pass 1"
    assert result.rebuttal_summary is None, \
        "rebuttal_summary should be None when rebuttal pass was skipped"

    print("PASS  Test 8 — rebuttal pass skipped gracefully when Pass 1 agent fails")

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
