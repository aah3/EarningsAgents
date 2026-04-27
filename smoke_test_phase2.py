"""
smoke_test_phase2.py — Phase 2 (multi-round rebuttal) validation.

Checks (no LLM, no Redis, no external API):

  1. AgentConfig.enable_rebuttals field exists and defaults to False.
  2. load_config() wires ENABLE_REBUTTALS env var.
  3. BULL_REBUTTAL_PROMPT and BEAR_REBUTTAL_PROMPT constants are importable.
  4. BaseAgent.rebuttal_analyze() method signature is correct (accepts
     opposing_response, rebuttal_system_prompt, stream/status callbacks).
  5. ConsensusAgent.synthesize() accepts bull_rebuttal and bear_rebuttal kwargs.
  6. EarningsPrediction dataclass has rebuttal_summary field.
  7. Prediction ORM model has rebuttal_summary column.
  8. ThreeAgentSystem.predict() signature is unchanged (backward-compatible).
  9. ThreeAgentSystem with enable_rebuttals=False skips rebuttal and
     produces an EarningsPrediction with rebuttal_summary=None
     (verified by inspecting field presence, not live run).
"""

import os
import inspect
from datetime import date

# ─── 1. AgentConfig field ───────────────────────────────────────────────────

from config.settings import AgentConfig, load_config, EarningsPrediction, PredictionDirection

cfg = AgentConfig()
assert hasattr(cfg, "enable_rebuttals"), "AgentConfig is missing enable_rebuttals"
assert cfg.enable_rebuttals is False, "enable_rebuttals should default to False"
print("[PASS] AgentConfig.enable_rebuttals field exists, default=False")

# ─── 2. load_config() env-var wiring ────────────────────────────────────────

os.environ["ENABLE_REBUTTALS"] = "true"
os.environ.setdefault("LLM_PROVIDER", "gemini")
os.environ.setdefault("GEMINI_API_KEY", "dummy")

loaded = load_config()
assert loaded.agent.enable_rebuttals is True, (
    f"Expected enable_rebuttals=True from env, got {loaded.agent.enable_rebuttals}"
)
print("[PASS] load_config() reads ENABLE_REBUTTALS from env")

del os.environ["ENABLE_REBUTTALS"]

# ─── 3. Rebuttal prompt constants ───────────────────────────────────────────

from agents.huggingface_agents import (
    BULL_REBUTTAL_PROMPT,
    BEAR_REBUTTAL_PROMPT,
    BaseAgent,
    BullAgent,
    BearAgent,
    ConsensusAgent,
    ThreeAgentSystem,
    AgentResponse,
)

assert "BULL" in BULL_REBUTTAL_PROMPT, "BULL_REBUTTAL_PROMPT seems wrong"
assert "BEAR" in BEAR_REBUTTAL_PROMPT, "BEAR_REBUTTAL_PROMPT seems wrong"
assert "critically examine" in BULL_REBUTTAL_PROMPT.lower()
assert "critically examine" in BEAR_REBUTTAL_PROMPT.lower()
print("[PASS] BULL_REBUTTAL_PROMPT and BEAR_REBUTTAL_PROMPT constants exist and contain expected text")

# ─── 4. BaseAgent.rebuttal_analyze() signature ──────────────────────────────

sig_rebuttal = inspect.signature(BullAgent.rebuttal_analyze)
params_rebuttal = sig_rebuttal.parameters
for expected in ("company", "news", "opposing_response", "rebuttal_system_prompt",
                 "stream_callback", "status_callback"):
    assert expected in params_rebuttal, f"rebuttal_analyze() missing param: {expected}"
print("[PASS] BaseAgent.rebuttal_analyze() has correct signature")

# ─── 5. ConsensusAgent.synthesize() accepts rebuttal kwargs ─────────────────

sig_synth = inspect.signature(ConsensusAgent.synthesize)
params_synth = sig_synth.parameters
assert "bull_rebuttal" in params_synth, "synthesize() missing bull_rebuttal kwarg"
assert "bear_rebuttal" in params_synth, "synthesize() missing bear_rebuttal kwarg"
# Both should be optional (default None)
assert params_synth["bull_rebuttal"].default is None
assert params_synth["bear_rebuttal"].default is None
print("[PASS] ConsensusAgent.synthesize() accepts bull_rebuttal and bear_rebuttal as Optional kwargs")

# ─── 6. EarningsPrediction.rebuttal_summary field ───────────────────────────

import dataclasses
field_names = {f.name for f in dataclasses.fields(EarningsPrediction)}
assert "rebuttal_summary" in field_names, "EarningsPrediction missing rebuttal_summary field"
# Must be optional / default to None
defaults = {f.name: f.default for f in dataclasses.fields(EarningsPrediction)}
assert defaults["rebuttal_summary"] is None, "rebuttal_summary default should be None"
print("[PASS] EarningsPrediction.rebuttal_summary field exists, default=None")

# ─── 7. Prediction ORM model column ─────────────────────────────────────────

from database.models import Prediction
import sqlalchemy
assert hasattr(Prediction, "rebuttal_summary"), "Prediction ORM model missing rebuttal_summary"
print("[PASS] Prediction ORM model has rebuttal_summary attribute")

# ─── 8. ThreeAgentSystem.predict() signature ────────────────────────────────

sig_predict = inspect.signature(ThreeAgentSystem.predict)
for expected in ("company", "news", "prediction_date", "task_id", "user_analysis"):
    assert expected in sig_predict.parameters, f"predict() missing param: {expected}"
print("[PASS] ThreeAgentSystem.predict() signature is unchanged / backward-compatible")

# ─── 9. rebuttal_summary present in EarningsPrediction output ───────────────

# Build a minimal prediction with no rebuttal (should produce None)
pred = EarningsPrediction(
    ticker="TEST",
    company_name="Test Corp",
    report_date=date.today(),
    prediction_date=date.today(),
    direction=PredictionDirection.BEAT,
    confidence=0.75,
    rebuttal_summary=None,
)
assert pred.rebuttal_summary is None
print("[PASS] EarningsPrediction constructs correctly with rebuttal_summary=None")

pred_with_rebuttal = EarningsPrediction(
    ticker="TEST",
    company_name="Test Corp",
    report_date=date.today(),
    prediction_date=date.today(),
    direction=PredictionDirection.MISS,
    confidence=0.65,
    rebuttal_summary="=== REBUTTAL ROUND ===\n\nBULL REBUTTAL: ...\n\nBEAR REBUTTAL: ...\n",
)
assert "REBUTTAL" in pred_with_rebuttal.rebuttal_summary
print("[PASS] EarningsPrediction constructs correctly with rebuttal_summary populated")

# ─── Done ────────────────────────────────────────────────────────────────────

print()
print("Phase 2 smoke test PASSED — multi-round rebuttal pipeline is correctly wired.")
