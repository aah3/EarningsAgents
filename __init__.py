"""
Earnings Prediction POC

Simplified earnings prediction using:
- Bloomberg BQL for data
- Hugging Face for LLM agents
- Three-agent debate system (Bull, Bear, Quant + Consensus)
"""

__version__ = "0.1.0"

from config import (
    PipelineConfig,
    AgentConfig,
    BloombergConfig,
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

from data import BloombergDataSource
from output import OutputWriter
from pipeline import EarningsPipeline

__all__ = [
    # Config
    "PipelineConfig",
    "AgentConfig",
    "BloombergConfig",
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
    
    # Data
    "BloombergDataSource",
    
    # Output
    "OutputWriter",
    
    # Pipeline
    "EarningsPipeline",
]
