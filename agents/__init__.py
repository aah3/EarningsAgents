"""Agents module for earnings predictions."""

from .llm_client import LLMClient
from .huggingface_agents import (
    AgentResponse,
    BaseAgent,
    BullAgent,
    BearAgent,
    QuantAgent,
    ConsensusAgent,
    ThreeAgentSystem,
)

__all__ = [
    "LLMClient",
    "AgentResponse",
    "BaseAgent",
    "BullAgent",
    "BearAgent",
    "QuantAgent",
    "ConsensusAgent",
    "ThreeAgentSystem",
]
