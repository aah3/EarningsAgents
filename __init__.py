"""
Earnings Prediction POC

Simplified earnings prediction using:
- Hugging Face for LLM agents
- Three-agent debate system (Bull, Bear, Quant + Consensus)
"""

__version__ = "0.1.0"

from config import (
    PipelineConfig,
    AgentConfig,
    CompanyData,
    NewsArticle,
    EarningsPrediction,
    PredictionDirection,
)

from agents import (
    BullAgent,
    BearAgent,
    QuantAgent,
    ConsensusAgent,
    ThreeAgentSystem,
)


from output import OutputWriter
from pipeline import EarningsPipeline

__all__ = [
    # Config
    "PipelineConfig",
    "AgentConfig",
    "CompanyData",
    "NewsArticle",
    "EarningsPrediction",
    "PredictionDirection",
    
    # Agents
    "BullAgent",
    "BearAgent",
    "QuantAgent",
    "ConsensusAgent",
    "ThreeAgentSystem",
    

    # Output
    "OutputWriter",
    
    # Pipeline
    "EarningsPipeline",
]
