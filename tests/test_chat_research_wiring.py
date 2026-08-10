"""
Unit test for interactive Consensus AI Chat Box fundamental research prompt wiring.
"""

import sys
import os
import pytest
from unittest.mock import MagicMock, patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import load_config
from agents.huggingface_agents import ConsensusAgent


def test_consensus_chat_prompt_injection():
    config = load_config().agent
    agent = ConsensusAgent(config)

    captured_prompt = []
    def mock_llm_chat(system_prompt, messages, **kwargs):
        captured_prompt.append(system_prompt)
        return "I am the consensus analyst. Based on our fundamental research..."

    agent.llm.chat = mock_llm_chat

    messages = [{"role": "user", "content": "What are the key catalysts?"}]

    # 1. Without research_context
    agent.chat(messages, research_context=None)
    assert len(captured_prompt) == 1
    assert "FUNDAMENTAL RESEARCH THESIS CONTEXT" not in captured_prompt[0]

    # 2. WITH research_context
    research_ctx = "Headline View: Dominant AI cloud moat.\nBusiness Viability: 75% gross margins."
    agent.chat(messages, research_context=research_ctx)
    assert len(captured_prompt) == 2
    assert "FUNDAMENTAL RESEARCH THESIS CONTEXT" in captured_prompt[1]
    assert research_ctx in captured_prompt[1]

    print("\n[PASS] ConsensusAgent.chat fundamental research prompt injection verified successfully!")


if __name__ == "__main__":
    test_consensus_chat_prompt_injection()
