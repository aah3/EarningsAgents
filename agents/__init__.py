"""Agents module - Hugging Face only."""

from .huggingface_agents import (
    AgentResponse,
    HuggingFaceAgent,
    BullAgent,
    BearAgent,
    QuantAgent,
    ConsensusAgent,
    ThreeAgentSystem,
)

__all__ = [
    "AgentResponse",
    "HuggingFaceAgent",
    "BullAgent",
    "BearAgent",
    "QuantAgent",
    "ConsensusAgent",
    "ThreeAgentSystem",
]
