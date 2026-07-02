"""
test_bloomberg_removal.py
Verifies that all Bloomberg stubs have been cleanly removed.
Run from project root: python test_bloomberg_removal.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test1():
    """bloomberg.py no longer exists."""
    assert not os.path.exists("bloomberg.py"), \
        "bloomberg.py still exists — it should have been deleted"
    print("PASS  Test 1 — bloomberg.py deleted")


def test2():
    """BloombergConfig is not importable from settings."""
    from settings import PipelineConfig, AgentConfig, DataSourceConfig
    try:
        from settings import BloombergConfig
        assert False, "BloombergConfig still importable from settings"
    except ImportError:
        pass
    print("PASS  Test 2 — BloombergConfig removed from settings.py")


def test3():
    """PipelineConfig has no bloomberg field."""
    from settings import PipelineConfig
    fields = PipelineConfig.__dataclass_fields__
    assert "bloomberg" not in fields, \
        "PipelineConfig still has a 'bloomberg' field"
    print("PASS  Test 3 — PipelineConfig.bloomberg field removed")


def test4():
    """settings.py still imports and PipelineConfig still has all other fields."""
    from settings import (
        PipelineConfig, AgentConfig, DataSourceConfig,
        CompanyData, EarningsPrediction, PredictionDirection,
        ReportTime, load_config,
    )
    cfg = PipelineConfig()
    assert hasattr(cfg, "yahoo")
    assert hasattr(cfg, "alphavantage")
    assert hasattr(cfg, "sec")
    assert hasattr(cfg, "agent")
    assert hasattr(cfg, "newsapi")
    print("PASS  Test 4 — settings.py intact with all non-Bloomberg fields present")


def test5():
    """No Bloomberg references remain in any .py file in the project root."""
    import glob
    bloomberg_terms = [
        "bloomberg", "Bloomberg", "BloombergConfig",
        "BloombergDataSource", "bql",
    ]
    hits = []
    for filepath in glob.glob("*.py"):
        if filepath == "test_bloomberg_removal.py":
            continue
        with open(filepath, encoding="utf-8", errors="ignore") as f:
            for lineno, line in enumerate(f, 1):
                for term in bloomberg_terms:
                    if term in line:
                        hits.append(f"  {filepath}:{lineno}: {line.rstrip()}")
    assert not hits, "Bloomberg references still present:\n" + "\n".join(hits)
    print("PASS  Test 5 — no Bloomberg references remain in any .py file")


def test6():
    """All six existing test suites still import cleanly after the removal."""
    import importlib, subprocess
    suites = [
        "test_agent_fixes",
        "test_sec_tool",
        "test_pipeline_sec_wiring",
        "test_resolvers",
        "test_provider_chain",
        "test_rebuttal_round",
    ]
    for suite in suites:
        try:
            if suite in sys.modules:
                del sys.modules[suite]
            importlib.import_module(suite)
            print(f"  import OK: {suite}.py")
        except Exception as e:
            assert False, f"{suite}.py failed to import after Bloomberg removal: {e}"
    print("PASS  Test 6 — all existing test suites import cleanly")


if __name__ == "__main__":
    tests = [test1, test2, test3, test4, test5, test6]
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
        print("All 6 tests passed.")
        sys.exit(0)
    else:
        print(f"{failed} test(s) FAILED.")
        sys.exit(1)
