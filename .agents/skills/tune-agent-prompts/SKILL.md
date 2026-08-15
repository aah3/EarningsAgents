---
name: tune-agent-prompts
description: Workflow for modifying agent system prompts, ReAct tool definitions, debate structures, JSON response schema enforcement, and LLM provider configurations.
---

# Agent Prompt & Multi-LLM Tuning Workflow

Follow this procedure when modifying prompt templates, agent debate roles (Bull/Bear/Quant/Consensus), tool definitions, or multi-provider LLM schemas.

## 1. Prompt & Agent Modifications (`agents/huggingface_agents.py`)
1. Edit agent system prompts or execution methods in [`agents/huggingface_agents.py`](file:///c:/Users/alfredo/Project/EarningsAgents/agents/huggingface_agents.py).
2. Ensure strict JSON schema compliance:
   - All 4 agent roles output JSON conforming to `AGENT_RESPONSE_SCHEMA`.
   - Use `clean_json_response(...)` to sanitize common LLM syntax errors (trailing commas, control characters, unescaped quotes).
3. Preserve dual-import shims:
   ```python
   try:
       from settings import load_config
       from llm_client import LLMClient
   except ImportError:
       from config.settings import load_config
       from agents.llm_client import LLMClient
   ```

## 2. ReAct Tools & Rebuttal Loops
1. If extending ReAct tool capabilities, register tools in [`agents/agent_tools.py`](file:///c:/Users/alfredo/Project/EarningsAgents/agents/agent_tools.py) (`AgentToolRegistry`).
2. Test tool execution under `AgentConfig.use_react = True`.
3. If modifying cross-examination logic, test Pass 2 under `AgentConfig.enable_rebuttals = True`.

## 3. Multi-Provider Fallbacks (`agents/llm_client.py`)
1. Verify compatibility across supported providers (`gemini`, `anthropic`, `openai`).
2. Ensure provider-specific schema handlers in [`agents/llm_client.py`](file:///c:/Users/alfredo/Project/EarningsAgents/agents/llm_client.py) strip unhandled JSON-Schema keys (e.g. Gemini `additionalProperties` handling).

## 4. Verification
1. Run agent tests:
   ```bash
   python -m pytest tests/test_agents.py -v
   ```
2. Test a single ticker debate run in dry-run or verify settings mode:
   ```bash
   python verify_settings.py
   python run_googl_debate.py
   ```
