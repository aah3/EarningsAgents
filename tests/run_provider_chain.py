def test1():
    import logging
    from data.provider_chain import ProviderChain

    log = logging.getLogger("test")
    chain = ProviderChain(log)

    called = {"second": False}

    def second():
        called["second"] = True
        return "second_value"

    result = chain.fetch("test_label", [
        ("primary",   lambda: "primary_value"),
        ("secondary", second),
    ])

    assert result.value == "primary_value"
    assert result.source == "primary"
    assert "primary" in result.attempted
    assert called["second"] is False, "Second source should not have been called"
    print("PASS  Test 1 — first source succeeds, second never called")

def test2():
    import logging
    from data.provider_chain import ProviderChain

    log = logging.getLogger("test")
    chain = ProviderChain(log)

    result = chain.fetch("test_label", [
        ("primary",   lambda: None),
        ("secondary", lambda: "fallback_value"),
    ])

    assert result.value == "fallback_value"
    assert result.source == "secondary"
    assert result.attempted == ["primary", "secondary"]
    print("PASS  Test 2 — first source returns None, second source used")

def test3():
    import logging
    from data.provider_chain import ProviderChain

    log = logging.getLogger("test")
    chain = ProviderChain(log)

    def bad_source():
        raise ConnectionError("timeout")

    result = chain.fetch("test_label", [
        ("primary",   bad_source),
        ("secondary", lambda: {"eps": 1.5}),
    ])

    assert result.value == {"eps": 1.5}
    assert result.source == "secondary"
    assert "primary" in result.errors
    assert "timeout" in result.errors["primary"]
    print("PASS  Test 3 — first source raises, second source used, error recorded")

def test4():
    import logging
    from data.provider_chain import ProviderChain

    log = logging.getLogger("test")
    chain = ProviderChain(log)

    result = chain.fetch("test_label", [
        ("s1", lambda: None),
        ("s2", lambda: []),
        ("s3", lambda: {}),
    ])

    assert result.value is None
    assert result.source == "none"
    assert result.attempted == ["s1", "s2", "s3"]
    print("PASS  Test 4 — all sources fail, value is None and source is 'none'")

def test5():
    import logging
    from data.provider_chain import ProviderChain

    log = logging.getLogger("test")
    chain = ProviderChain(log)

    # Empty list → fallback
    result = chain.fetch("test_label", [
        ("s1", lambda: []),
        ("s2", lambda: [{"item": 1}, {"item": 2}]),
    ])
    assert result.value == [{"item": 1}, {"item": 2}]
    assert result.source == "s2"

    # Non-empty list → no fallback
    result2 = chain.fetch("test_label", [
        ("s1", lambda: [{"item": 1}]),
        ("s2", lambda: [{"item": 99}]),
    ])
    assert result2.value == [{"item": 1}]
    assert result2.source == "s1"
    print("PASS  Test 5 — empty list triggers fallback, non-empty list does not")

def test6():
    import logging
    from data.provider_chain import ProviderChain

    log = logging.getLogger("test")
    # Treat zero as empty
    chain = ProviderChain(log, empty_sentinel=lambda v: v is None or v == 0)

    result = chain.fetch("eps", [
        ("s1", lambda: 0),        # zero → treated as empty
        ("s2", lambda: 1.5),
    ])
    assert result.value == 1.5
    assert result.source == "s2"
    print("PASS  Test 6 — custom empty_sentinel treats 0 as empty")

def test7():
    import inspect
    import data.data_aggregator as da

    src = inspect.getsource(da.DataAggregator.get_company_data)

    # All seven cascade blocks must now use ProviderChain
    assert src.count('chain.fetch(') >= 6, \
        f"Expected at least 6 chain.fetch() calls, found {src.count('chain.fetch(')}"
    assert 'ProviderChain(' in src, \
        "get_company_data() does not instantiate ProviderChain"

    # Old-style cascade patterns must be gone from the seven replaced blocks
    # (check for the most distinctive old patterns)
    assert 'if self.yahoo:\n            company_info' not in src, \
        "Old company_info cascade block still present"
    assert 'if not consensus and self.alphavantage:' not in src, \
        "Old consensus cascade block still present"
    print("PASS  Test 7 — data_aggregator uses ProviderChain for cascade logic")

def test8():
    """
    Simulates Yahoo returning None for consensus and verifies Alpha Vantage
    fallback fires — the bug that the old elif-based cascade had silently.
    """
    import logging
    from unittest.mock import MagicMock, patch
    from datetime import date
    from data.provider_chain import ProviderChain

    log = logging.getLogger("test")
    chain = ProviderChain(log)

    yahoo_consensus = None      # Yahoo fails to return consensus
    av_consensus = MagicMock()
    av_consensus.eps_mean = 2.45
    av_consensus.revenue_mean = 1.2e11
    av_consensus.num_analysts = 38

    result = chain.fetch("consensus_estimates", [
        ("yahoo",         lambda: yahoo_consensus),
        ("alpha_vantage", lambda: av_consensus),
    ])

    assert result.value is av_consensus, \
        "Expected Alpha Vantage consensus when Yahoo returns None"
    assert result.source == "alpha_vantage"
    assert result.attempted == ["yahoo", "alpha_vantage"]
    print("PASS  Test 8 — Alpha Vantage fallback fires when Yahoo consensus is None")

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
