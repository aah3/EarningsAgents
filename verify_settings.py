"""
verify_settings.py — Confirms settings.py is complete after recent rewrites.
Run from project root: python verify_settings.py
No API keys or network access required.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("VERIFICATION: settings.py completeness")
print("=" * 60)

# ── 1. Import ────────────────────────────────────────────────
try:
    from settings import (
        AgentConfig, CompanyData, EarningsPrediction,
        PredictionDirection, ReportTime, load_config,
        PipelineConfig, DataSourceConfig,
    )
    print("PASS  settings.py imports cleanly")
except ImportError as e:
    print(f"FAIL  settings.py import error: {e}")
    sys.exit(1)

# ── 2. AgentConfig fields ────────────────────────────────────
required_agent_fields = {
    "provider": str,
    "model_name": str,
    "api_key": type(None),   # Optional
    "temperature": float,
    "max_tokens": int,
    "use_react": bool,
    "react_max_turns": int,
}
fields = {f.name: f for f in AgentConfig.__dataclass_fields__.values()}
for name, _ in required_agent_fields.items():
    if name in fields:
        print(f"PASS  AgentConfig.{name} present (default={fields[name].default!r})")
    else:
        print(f"FAIL  AgentConfig.{name} MISSING")

# ── 3. EarningsPrediction.rebuttal_summary ───────────────────
ep_fields = EarningsPrediction.__dataclass_fields__
if "rebuttal_summary" in ep_fields:
    print(f"PASS  EarningsPrediction.rebuttal_summary present")
else:
    print("FAIL  EarningsPrediction.rebuttal_summary MISSING")

# ── 4. CompanyData fields required by data_aggregator.py ────
required_company_fields = [
    "ticker", "company_name", "sector", "industry", "market_cap",
    "report_date", "report_time", "consensus_eps", "consensus_revenue",
    "num_analysts", "historical_eps", "beat_rate_4q", "avg_surprise_4q",
    "current_price", "price_change_5d", "price_change_21d",
    "short_interest", "estimate_revisions", "options_features",
    "analyst_recommendations",
    "recent_transcripts",
    "company_facts",
]
cd_fields = CompanyData.__dataclass_fields__
all_present = True
for name in required_company_fields:
    if name in cd_fields:
        print(f"PASS  CompanyData.{name} present")
    else:
        print(f"FAIL  CompanyData.{name} MISSING  <- will crash DataAggregator at runtime")
        all_present = False

# ── 5. load_config() smoke-test (no real env vars needed) ────
os.environ.pop("LLM_PROVIDER", None)
os.environ.pop("LLM_MODEL_NAME", None)
os.environ.pop("GEMINI_API_KEY", None)
os.environ.pop("ANTHROPIC_API_KEY", None)
os.environ.pop("OPENAI_API_KEY", None)

try:
    cfg = load_config()
    assert isinstance(cfg, PipelineConfig), "load_config() did not return PipelineConfig"
    assert isinstance(cfg.agent, AgentConfig), "cfg.agent is not AgentConfig"
    assert cfg.agent.provider in ("gemini", "anthropic", "openai"), \
        f"Unexpected default provider: {cfg.agent.provider}"
    print(f"PASS  load_config() returns PipelineConfig (default provider={cfg.agent.provider!r})")
except Exception as e:
    print(f"FAIL  load_config() raised: {e}")

for provider, key_var in [
    ("gemini",    "GEMINI_API_KEY"),
    ("anthropic", "ANTHROPIC_API_KEY"),
    ("openai",    "OPENAI_API_KEY"),
]:
    os.environ["LLM_PROVIDER"] = provider
    os.environ[key_var] = "test-key-123"
    try:
        cfg = load_config()
        assert cfg.agent.provider == provider
        assert cfg.agent.api_key == "test-key-123", \
            f"api_key not set for provider {provider}: got {cfg.agent.api_key!r}"
        print(f"PASS  load_config() correctly maps LLM_PROVIDER={provider!r} -> {key_var}")
    except Exception as e:
        print(f"FAIL  load_config() provider={provider}: {e}")
    finally:
        os.environ.pop("LLM_PROVIDER", None)
        os.environ.pop(key_var, None)

print()
print("=" * 60)
print("Done. Fix any FAIL lines before proceeding to Prompt 2.")
print("=" * 60)
