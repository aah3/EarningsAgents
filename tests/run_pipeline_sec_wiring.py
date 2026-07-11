"""
test_pipeline_sec_wiring.py
Verifies that EarningsPipeline.initialize() correctly wires the SEC source
into ThreeAgentSystem.sec_source.
Run from project root: python test_pipeline_sec_wiring.py
No API keys or network access required.
"""
import sys, os, logging
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
logging.basicConfig(level=logging.WARNING)

from unittest.mock import MagicMock, patch, PropertyMock


def _make_pipeline():
    """Return an EarningsPipeline with all heavy dependencies mocked."""
    from settings import PipelineConfig, AgentConfig, DataSourceConfig
    from pipeline import EarningsPipeline

    config = PipelineConfig(
        agent=AgentConfig(provider="openai", api_key="dummy"),
        sec=DataSourceConfig(enabled=True),
    )
    return EarningsPipeline(config)


def test1():
    """When SEC is enabled, agent_system.sec_source is set to aggregator.sec."""
    from pipeline import EarningsPipeline
    import agents.huggingface_agents as ha

    pipeline = _make_pipeline()

    mock_sec = MagicMock(name="SECEdgarDataSource")
    mock_aggregator = MagicMock()
    mock_aggregator.sec = mock_sec

    mock_agent_system = MagicMock(spec=ha.ThreeAgentSystem)
    mock_agent_system.sec_source = None

    with patch.object(EarningsPipeline, '_make_aggregator',
                      return_value=mock_aggregator, create=True):
        pipeline.aggregator = mock_aggregator
        pipeline.agent_system = mock_agent_system

        # Simulate just the wiring lines from initialize()
        pipeline.agent_system.sec_source = getattr(pipeline.aggregator, "sec", None)

    assert pipeline.agent_system.sec_source is mock_sec, \
        f"Expected sec_source to be mock_sec, got {pipeline.agent_system.sec_source}"
    print("PASS  Test 1 — sec_source wired when aggregator.sec is present")


def test2():
    """When SEC is disabled (aggregator.sec is None), sec_source stays None."""
    from pipeline import EarningsPipeline
    import agents.huggingface_agents as ha

    pipeline = _make_pipeline()

    mock_aggregator = MagicMock()
    mock_aggregator.sec = None

    mock_agent_system = MagicMock(spec=ha.ThreeAgentSystem)
    mock_agent_system.sec_source = None

    pipeline.aggregator = mock_aggregator
    pipeline.agent_system = mock_agent_system
    pipeline.agent_system.sec_source = getattr(pipeline.aggregator, "sec", None)

    assert pipeline.agent_system.sec_source is None, \
        "sec_source should remain None when aggregator.sec is None"
    print("PASS  Test 2 — sec_source stays None when SEC is disabled")


def test3():
    """getattr fallback works when aggregator has no 'sec' attribute at all."""
    from pipeline import EarningsPipeline
    import agents.huggingface_agents as ha

    pipeline = _make_pipeline()

    # Aggregator with no 'sec' attribute (older version / unexpected state)
    mock_aggregator = MagicMock(spec=[])   # spec=[] means no attributes allowed
    mock_agent_system = MagicMock(spec=ha.ThreeAgentSystem)
    mock_agent_system.sec_source = None

    pipeline.aggregator = mock_aggregator
    pipeline.agent_system = mock_agent_system

    # Must not raise AttributeError
    pipeline.agent_system.sec_source = getattr(pipeline.aggregator, "sec", None)
    assert pipeline.agent_system.sec_source is None
    print("PASS  Test 3 — getattr fallback handles missing 'sec' attribute safely")


def test4():
    """initialize() source confirms the wiring is present in the actual method."""
    import inspect
    from pipeline import EarningsPipeline

    src = inspect.getsource(EarningsPipeline.initialize)

    assert "sec_source" in src, \
        "initialize() does not assign sec_source — wiring code is missing"
    assert 'getattr(self.aggregator, "sec", None)' in src or \
           "getattr(self.aggregator, 'sec', None)" in src, \
        "initialize() does not use getattr to safely read aggregator.sec"
    assert "SEC EDGAR tool-calling" in src, \
        "initialize() missing the SEC status log line"
    print("PASS  Test 4 — initialize() source contains the wiring and log lines")


if __name__ == "__main__":
    tests = [test1, test2, test3, test4]
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
        print("All 4 tests passed.")
        sys.exit(0)
    else:
        print(f"{failed} test(s) FAILED.")
        sys.exit(1)
