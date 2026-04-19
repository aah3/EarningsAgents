"""
test_react_loop.py — Phase 2, Step D integration test.

Validates AgentToolRegistry dispatch with a fully hardcoded CompanyData stub.
No LLM calls, no external API calls.
"""

from datetime import date

from config.settings import CompanyData, ReportTime
from agents.agent_tools import AgentToolRegistry


# ---------------------------------------------------------------------------
# 1. Construct minimal CompanyData
# ---------------------------------------------------------------------------

company = CompanyData(
    ticker="TEST",
    company_name="Test Corp",
    sector="Tech",
    industry="Software",
    market_cap=50_000_000_000,
    report_date=date(2025, 1, 30),
    report_time=ReportTime.UNKNOWN,
    consensus_eps=2.50,
    consensus_revenue=10_000_000_000,
    num_analysts=10,
    historical_eps=[{"date": "2024-Q3", "surprise_pct": 3.5}],
    estimate_revisions=[],
    options_features={},
)
# Attach fields that aren't in the dataclass constructor (added ad-hoc)
company.recent_transcripts = [
    {"year": 2024, "quarter": 3, "transcript": "Revenue grew strongly."}
]
company.company_facts = {}

# ---------------------------------------------------------------------------
# 2. Instantiate registry
# ---------------------------------------------------------------------------

registry = AgentToolRegistry(company, news=[])

# ---------------------------------------------------------------------------
# 3. Test: get_company_summary — should succeed with no error
# ---------------------------------------------------------------------------

result = registry.dispatch("get_company_summary", {})
assert result.error is None, (
    f"get_company_summary returned an error: {result.error}"
)
assert result.result is not None, "get_company_summary result data is None"
assert result.result.get("ticker") == "TEST", (
    f"Expected ticker='TEST', got {result.result.get('ticker')!r}"
)
print("  [PASS] get_company_summary — no error, ticker='TEST'")

# ---------------------------------------------------------------------------
# 4. Test: get_sec_transcript with max_chars=50 — data must contain "Revenue"
# ---------------------------------------------------------------------------

result_t = registry.dispatch("get_sec_transcript", {"max_chars": 50})
assert result_t.error is None, (
    f"get_sec_transcript returned an error: {result_t.error}"
)
snippet = result_t.result.get("snippet", "")
assert "Revenue" in snippet, (
    f"Expected 'Revenue' in transcript snippet, got: {snippet!r}"
)
print(f"  [PASS] get_sec_transcript — snippet contains 'Revenue': {snippet!r}")

# ---------------------------------------------------------------------------
# 5. Test: nonexistent_tool — must return a non-None error
# ---------------------------------------------------------------------------

result_bad = registry.dispatch("nonexistent_tool", {})
assert result_bad.error is not None, (
    "Expected an error for unknown tool, but error was None"
)
print(f"  [PASS] nonexistent_tool — error reported: {result_bad.error!r}")

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------

print("\nAll AgentToolRegistry tests passed.")
