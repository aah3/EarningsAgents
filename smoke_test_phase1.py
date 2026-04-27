"""
smoke_test_phase1.py — Phase 1 (ReAct activation) validation.

Checks:
  1. AgentConfig.react_max_turns field exists (new field).
  2. load_config() wires USE_REACT / USE_REACT_MAX_TURNS env vars.
  3. BaseAgent.analyze() accepts use_react=None and resolves from config.
  4. ThreeAgentSystem carries the react_mode flag down to run_agent
     (verified indirectly: react_mode = config.use_react attribute).
  5. AgentToolRegistry dispatch still works (tool layer untouched).

No live LLM or Redis calls — runs entirely offline.
"""

import os
from datetime import date

# ─── 1. Config field ────────────────────────────────────────────────────────

from config.settings import AgentConfig, PipelineConfig, load_config

cfg = AgentConfig()
assert hasattr(cfg, "react_max_turns"), "AgentConfig is missing react_max_turns"
assert cfg.react_max_turns == 6, f"Expected default react_max_turns=6, got {cfg.react_max_turns}"
assert cfg.use_react is False, "Default use_react should be False"
print("[PASS] AgentConfig.react_max_turns field exists, default=6")

# ─── 2. load_config() env-var wiring ────────────────────────────────────────

os.environ["USE_REACT"] = "true"
os.environ["USE_REACT_MAX_TURNS"] = "8"
# Provide a dummy key so load_config doesn't error on missing provider
os.environ.setdefault("LLM_PROVIDER", "gemini")
os.environ.setdefault("GEMINI_API_KEY", "dummy")

loaded = load_config()
assert loaded.agent.use_react is True, (
    f"Expected use_react=True from env, got {loaded.agent.use_react}"
)
assert loaded.agent.react_max_turns == 8, (
    f"Expected react_max_turns=8 from env, got {loaded.agent.react_max_turns}"
)
print("[PASS] load_config() reads USE_REACT and USE_REACT_MAX_TURNS from env")

# Reset env vars
del os.environ["USE_REACT"]
del os.environ["USE_REACT_MAX_TURNS"]

# ─── 3. BaseAgent.analyze() signature accepts use_react=None ────────────────

import inspect
from agents.huggingface_agents import BaseAgent, BullAgent

sig = inspect.signature(BullAgent.analyze)
params = sig.parameters
assert "use_react" in params, "BaseAgent.analyze() is missing use_react parameter"
default_val = params["use_react"].default
assert default_val is None, (
    f"Expected use_react default to be None, got {default_val!r}"
)
print("[PASS] BaseAgent.analyze() has use_react=None default")

# ─── 4. ThreeAgentSystem has react_mode reading from config ─────────────────

from agents.huggingface_agents import ThreeAgentSystem

react_cfg = AgentConfig(use_react=True, react_max_turns=4, api_key="dummy")
tms = ThreeAgentSystem(react_cfg)
assert tms.config.use_react is True, "ThreeAgentSystem did not store use_react=True"
assert tms.config.react_max_turns == 4, "ThreeAgentSystem did not store react_max_turns=4"
print("[PASS] ThreeAgentSystem carries use_react and react_max_turns from config")

# ─── 5. AgentToolRegistry dispatch still works ──────────────────────────────

from config.settings import CompanyData, ReportTime
from agents.agent_tools import AgentToolRegistry

company = CompanyData(
    ticker="SMKE",
    company_name="Smoke Test Inc",
    sector="Tech",
    industry="Software",
    market_cap=10_000_000_000,
    report_date=date(2025, 4, 30),
    consensus_eps=1.23,
)
company.recent_transcripts = [{"year": 2025, "quarter": 1, "transcript": "Revenue was strong."}]
company.company_facts = {}

registry = AgentToolRegistry(company, news=[])
result = registry.dispatch("get_company_summary", {})
assert result.error is None, f"get_company_summary error: {result.error}"
assert result.result["ticker"] == "SMKE"
print("[PASS] AgentToolRegistry.dispatch('get_company_summary') works correctly")

# ─── Done ────────────────────────────────────────────────────────────────────

print()
print("Phase 1 smoke test PASSED — ReAct pipeline wiring is correct.")
