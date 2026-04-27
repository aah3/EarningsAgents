"""
Simplified Configuration for Earnings Prediction POC.
Uses only Hugging Face agents and Bloomberg BQL data.
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Optional, List, Dict, Any
from pathlib import Path


class PredictionDirection(Enum):
    """Earnings prediction direction."""
    BEAT = "beat"
    MISS = "miss"
    MEET = "meet"


class ReportTime(Enum):
    """When company reports earnings."""
    BMO = "before_market_open"
    AMC = "after_market_close"
    UNKNOWN = "unknown"


@dataclass
class BloombergConfig:
    """Bloomberg BQL connection settings."""
    timeout: int = 30
    max_retries: int = 3
    rate_limit_per_minute: int = 100


@dataclass
class AgentConfig:
    """Agent configuration for LLMs."""
    provider: str = "gemini"  # or "anthropic", "openai"
    model_name: str = "gemini-2.0-flash"
    api_key: Optional[str] = None
    temperature: float = 0.3
    max_tokens: int = 2048
    use_local: bool = False
    use_react: bool = False           # when True, analyze() delegates to _react_analyze()
    react_max_turns: int = 6          # maximum tool-call turns per ReAct loop
    enable_rebuttals: bool = False    # when True, ThreeAgentSystem runs a rebuttal pass


@dataclass
class DataSourceConfig:
    """Generic data source configuration."""
    api_key: Optional[str] = None
    rate_limit_calls: int = 5
    rate_limit_period: float = 60.0  # seconds
    enabled: bool = True
    timeout: int = 30
    max_retries: int = 3


@dataclass
class PipelineConfig:
    """Master configuration for the pipeline."""
    # Universe settings
    benchmark: str = "SPX"
    start_date: date = field(default_factory=lambda: date(2024, 1, 1))
    end_date: date = field(default_factory=lambda: date(2024, 12, 31))
    
    # Component configs
    yahoo: DataSourceConfig = field(default_factory=lambda: DataSourceConfig(rate_limit_calls=2000))
    newsapi: DataSourceConfig = field(default_factory=DataSourceConfig)
    alphavantage: DataSourceConfig = field(default_factory=DataSourceConfig)
    sec: DataSourceConfig = field(default_factory=lambda: DataSourceConfig(enabled=False))
    
    # Bloomberg is legacy or optional now
    bloomberg: BloombergConfig = field(default_factory=BloombergConfig)
    
    agent: AgentConfig = field(default_factory=AgentConfig)
    
    # Multi-agent settings
    enable_debate: bool = True
    debate_rounds: int = 2
    
    # Output settings
    output_dir: Path = field(default_factory=lambda: Path("./output"))
    
    # News settings
    news_lookback_days: int = 30
    max_news_articles: int = 50
    redis_url: str = "redis://localhost:6379/0"


@dataclass
class CompanyData:
    """Company data structure."""
    ticker: str
    company_name: str
    sector: str
    industry: str
    market_cap: float
    
    # Earnings info
    report_date: date
    report_time: ReportTime = ReportTime.UNKNOWN
    fiscal_quarter: str = ""
    fiscal_year: int = 0
    
    # Consensus estimates
    consensus_eps: float = 0.0
    consensus_revenue: float = 0.0
    num_analysts: int = 0
    
    # Historical
    historical_eps: List[Dict[str, Any]] = field(default_factory=list)
    beat_rate_4q: Optional[float] = None
    avg_surprise_4q: Optional[float] = None
    
    # Price data
    current_price: Optional[float] = None
    price_change_5d: Optional[float] = None
    price_change_21d: Optional[float] = None
    
    # Additional signals
    short_interest: Optional[float] = None
    estimate_revisions: List[Dict[str, Any]] = field(default_factory=list)
    options_features: Optional[Dict[str, Any]] = None


@dataclass
class NewsArticle:
    """News article structure."""
    headline: str
    body: Optional[str] = None
    source: str = ""
    published_at: datetime = field(default_factory=datetime.now)
    sentiment_score: Optional[float] = None  # -1 to 1
    relevance_score: Optional[float] = None  # 0 to 1


@dataclass
class EarningsPrediction:
    """Prediction output structure."""
    ticker: str
    company_name: str
    report_date: date
    prediction_date: date

    # Prediction
    direction: PredictionDirection
    confidence: float  # 0 to 1

    # Extended predictions
    expected_price_move: str = ""
    move_vs_implied: str = ""
    guidance_expectation: str = ""

    # Reasoning
    reasoning_summary: str = ""
    bull_factors: List[str] = field(default_factory=list)
    bear_factors: List[str] = field(default_factory=list)

    # Multi-agent votes
    agent_votes: Optional[Dict[str, str]] = None
    debate_summary: Optional[str] = None

    # Rebuttal cross-examination transcript (populated when enable_rebuttals=True)
    rebuttal_summary: Optional[str] = None


def load_config() -> PipelineConfig:
    """Load configuration from environment variables."""
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    
    # Select the appropriate API key based on the provider
    if provider == "gemini":
        agent_api_key = os.getenv("GEMINI_API_KEY")
    elif provider == "anthropic":
        agent_api_key = os.getenv("ANTHROPIC_API_KEY")
    elif provider == "openai":
        agent_api_key = os.getenv("OPENAI_API_KEY")
    else:
        agent_api_key = None

    return PipelineConfig(
        newsapi=DataSourceConfig(
            api_key=os.getenv("NEWSAPI_API_KEY"),
            enabled=os.getenv("NEWSAPI_API_KEY") is not None
        ),
        alphavantage=DataSourceConfig(
            api_key=os.getenv("ALPHAVANTAGE_API_KEY"),
            enabled=os.getenv("ALPHAVANTAGE_API_KEY") is not None
        ),
        agent=AgentConfig(
            provider=provider,
            model_name=os.getenv("LLM_MODEL_NAME") or "gemini-2.5-flash",
            api_key=agent_api_key,
            use_react=os.getenv("USE_REACT", "false").lower() in ("1", "true", "yes"),
            react_max_turns=int(os.getenv("USE_REACT_MAX_TURNS", "6")),
            enable_rebuttals=os.getenv("ENABLE_REBUTTALS", "false").lower() in ("1", "true", "yes"),
        ),
        redis_url=os.getenv("REDIS_URL") or "redis://localhost:6379/0"
    )
