"""
Base classes and common utilities for data sources.

Provides abstract base class for all data sources and common Pydantic models.
"""

from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import List, Dict, Any, Optional
from enum import Enum
import logging
from pydantic import BaseModel, Field, validator


# ============================================================================
# ENUMS
# ============================================================================

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


class RevisionDirection(Enum):
    """Direction of estimate revision."""
    UP = "up"
    DOWN = "down"
    UNCHANGED = "unchanged"


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class HistoricalEarning(BaseModel):
    """Historical earnings result."""
    date: date
    actual_eps: float
    estimate_eps: float
    surprise_pct: float
    beat: bool
    fiscal_quarter: Optional[str] = None
    fiscal_year: Optional[int] = None
    
    @validator('surprise_pct', pre=True, always=True)
    def calculate_surprise(cls, v, values):
        """Calculate surprise percentage if not provided."""
        if v is None and 'actual_eps' in values and 'estimate_eps' in values:
            actual = values['actual_eps']
            estimate = values['estimate_eps']
            if estimate != 0:
                return ((actual - estimate) / abs(estimate)) * 100
        return v or 0.0


class EstimateRevision(BaseModel):
    """Analyst estimate revision."""
    date: date
    old_estimate: float
    new_estimate: float
    direction: RevisionDirection
    change_pct: float
    analyst_name: Optional[str] = None
    firm: Optional[str] = None
    
    @validator('change_pct', pre=True, always=True)
    def calculate_change(cls, v, values):
        """Calculate change percentage if not provided."""
        if v is None and 'old_estimate' in values and 'new_estimate' in values:
            old = values['old_estimate']
            new = values['new_estimate']
            if old != 0:
                return ((new - old) / abs(old)) * 100
        return v or 0.0


class AnalystRecommendation(BaseModel):
    """Analyst recommendation."""
    date: date
    firm: str
    analyst: Optional[str] = None
    rating: str  # Buy, Hold, Sell, etc.
    rating_score: Optional[float] = None  # Normalized 1-5 scale
    price_target: Optional[float] = None
    previous_rating: Optional[str] = None


class ConsensusEstimate(BaseModel):
    """Consensus estimates for a company."""
    eps_mean: float
    eps_median: float
    eps_high: float
    eps_low: float
    eps_std: float
    revenue_mean: Optional[float] = None
    revenue_median: Optional[float] = None
    num_analysts: int
    as_of_date: date


class PriceData(BaseModel):
    """Price and momentum data."""
    current_price: float
    price_change_1d: Optional[float] = None
    price_change_5d: Optional[float] = None
    price_change_21d: Optional[float] = None
    price_change_63d: Optional[float] = None
    volume: Optional[float] = None
    avg_volume_30d: Optional[float] = None
    short_interest: Optional[float] = None
    beta: Optional[float] = None
    as_of_date: date


class NewsArticle(BaseModel):
    """News article."""
    headline: str
    body: Optional[str] = None
    source: str
    published_at: datetime
    url: Optional[str] = None
    sentiment_score: Optional[float] = Field(None, ge=-1.0, le=1.0)
    relevance_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    keywords: List[str] = Field(default_factory=list)


class CompanyInfo(BaseModel):
    """Basic company information."""
    ticker: str
    company_name: str
    sector: str
    industry: str
    market_cap: float
    exchange: Optional[str] = None
    currency: str = "USD"
    country: Optional[str] = None
    description: Optional[str] = None


class EarningsEvent(BaseModel):
    """Earnings announcement event."""
    ticker: str
    report_date: date
    report_time: ReportTime = ReportTime.UNKNOWN
    fiscal_quarter: Optional[str] = None
    fiscal_year: Optional[int] = None
    consensus_eps: Optional[float] = None
    consensus_revenue: Optional[float] = None


class EarningsCallTranscript(BaseModel):
    """Earnings call transcript."""
    ticker: str
    year: int
    quarter: str
    transcript: str


class CompanyData(BaseModel):
    """Complete company data structure."""
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
    historical_eps: List[Dict[str, Any]] = Field(default_factory=list)
    beat_rate_4q: Optional[float] = None
    avg_surprise_4q: Optional[float] = None
    
    # Price data
    current_price: Optional[float] = None
    price_change_5d: Optional[float] = None
    price_change_21d: Optional[float] = None
    
    # Additional signals
    short_interest: Optional[float] = None
    estimate_revisions: List[Dict[str, Any]] = Field(default_factory=list)
    analyst_recommendations: List[Dict[str, Any]] = Field(default_factory=list)
    recent_transcripts: List[Dict[str, Any]] = Field(default_factory=list)
    company_facts: Dict[str, Any] = Field(default_factory=dict)
    options_features: Optional[Dict[str, Any]] = None


# ============================================================================
# BASE DATA SOURCE
# ============================================================================

class BaseDataSource(ABC):
    """
    Abstract base class for all data sources.
    
    All data sources must implement these methods to ensure consistency.
    """
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"DataSource.{name}")
        self._connected = False
    
    @abstractmethod
    def connect(self) -> bool:
        """
        Establish connection to the data source.
        
        Returns:
            True if connection successful
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Close connection to the data source."""
        pass
    
    def _ensure_connected(self) -> None:
        """Ensure connection is established."""
        if not self._connected:
            raise RuntimeError(f"{self.name} not connected. Call connect() first.")
    
    @abstractmethod
    def get_company_info(self, ticker: str) -> Optional[CompanyInfo]:
        """
        Get basic company information.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            CompanyInfo or None if not found
        """
        pass
    
    @abstractmethod
    def get_price_data(self, ticker: str) -> Optional[PriceData]:
        """
        Get current price and momentum data.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            PriceData or None if not found
        """
        pass
    
    @abstractmethod
    def get_consensus_estimates(self, ticker: str) -> Optional[ConsensusEstimate]:
        """
        Get consensus analyst estimates.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            ConsensusEstimate or None if not found
        """
        pass
    
    @abstractmethod
    def get_historical_earnings(
        self, 
        ticker: str, 
        num_quarters: int = 8
    ) -> List[HistoricalEarning]:
        """
        Get historical earnings results.
        
        Args:
            ticker: Stock ticker symbol
            num_quarters: Number of quarters to retrieve
            
        Returns:
            List of HistoricalEarning
        """
        pass
    
    @abstractmethod
    def get_estimate_revisions(
        self, 
        ticker: str, 
        days_back: int = 90
    ) -> List[EstimateRevision]:
        """
        Get recent estimate revisions.
        
        Args:
            ticker: Stock ticker symbol
            days_back: Number of days to look back
            
        Returns:
            List of EstimateRevision
        """
        pass
    
    def get_analyst_recommendations(
        self, 
        ticker: str,
        days_back: int = 90
    ) -> List[AnalystRecommendation]:
        """
        Get analyst recommendations (optional for some sources).
        
        Args:
            ticker: Stock ticker symbol
            days_back: Number of days to look back
            
        Returns:
            List of AnalystRecommendation
        """
        return []
    
    def get_earnings_calendar(
        self,
        tickers: List[str],
        start_date: date,
        end_date: date
    ) -> List[EarningsEvent]:
        """
        Get earnings calendar (optional for some sources).
        
        Args:
            tickers: List of ticker symbols
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            List of EarningsEvent
        """
        return []


# ============================================================================
# RATE LIMITER
# ============================================================================

class RateLimiter:
    """
    Simple rate limiter for API calls.
    
    Usage:
        limiter = RateLimiter(max_calls=5, period=60)
        limiter.wait_if_needed()  # Will sleep if rate limit exceeded
    """
    
    def __init__(self, max_calls: int, period: float):
        """
        Initialize rate limiter.
        
        Args:
            max_calls: Maximum number of calls allowed
            period: Time period in seconds
        """
        import time
        from collections import deque
        
        self.max_calls = max_calls
        self.period = period
        self.calls = deque()
        self.time = time
    
    def wait_if_needed(self) -> None:
        """Wait if rate limit would be exceeded."""
        now = self.time.time()
        
        # Remove old calls outside the period
        while self.calls and self.calls[0] < now - self.period:
            self.calls.popleft()
        
        # Check if we need to wait
        if len(self.calls) >= self.max_calls:
            sleep_time = self.period - (now - self.calls[0])
            if sleep_time > 0:
                logging.debug(f"Rate limit reached, sleeping for {sleep_time:.2f}s")
                self.time.sleep(sleep_time)
                # Clean up after sleep
                now = self.time.time()
                while self.calls and self.calls[0] < now - self.period:
                    self.calls.popleft()
        
        # Record this call
        self.calls.append(now)


# ============================================================================
# DATA SOURCE CONFIGURATION
# ============================================================================

class DataSourceConfig(BaseModel):
    """Configuration for a data source."""
    enabled: bool = True
    api_key: Optional[str] = None
    rate_limit_calls: int = 5
    rate_limit_period: float = 60.0  # seconds
    timeout: int = 30
    max_retries: int = 3


# ============================================================================
# UTILITIES
# ============================================================================

def normalize_ticker(ticker: str) -> str:
    """Normalize ticker symbol to uppercase, strip whitespace."""
    return ticker.strip().upper()


def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float."""
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert value to int."""
    try:
        return int(value) if value is not None else default
    except (ValueError, TypeError):
        return default
