"""
Yahoo Finance Data Source for Earnings Prediction.

Provides:
- Historical price data
- Fundamental data (income statement, balance sheet, cash flow)
- Analyst estimates and recommendations
- Earnings calendar
- Company information
- Option chains with Greeks and implied volatility

Requires: yfinance, scipy
Install: pip install yfinance scipy
"""

from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
import warnings
import math

import numpy as np
import pandas as pd


# ============================================================================
# BASE TYPES AND UTILITIES
# ============================================================================

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


@dataclass
class DataSourceConfig:
    """Configuration for data sources."""
    rate_limit_calls: int = 100
    rate_limit_period: int = 60  # seconds
    timeout: int = 30
    max_retries: int = 3


@dataclass
class RateLimiter:
    """Simple rate limiter."""
    calls: int
    period: int
    _timestamps: List[float] = field(default_factory=list)
    
    def wait_if_needed(self):
        """Wait if rate limit reached."""
        import time
        now = time.time()
        self._timestamps = [t for t in self._timestamps if now - t < self.period]
        if len(self._timestamps) >= self.calls:
            sleep_time = self.period - (now - self._timestamps[0]) + 0.1
            if sleep_time > 0:
                time.sleep(sleep_time)
        self._timestamps.append(time.time())


@dataclass
class CompanyInfo:
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


@dataclass
class PriceData:
    """Price and momentum data."""
    current_price: float
    open_price: Optional[float] = None # TO DO: INCLUDE OPEN, HIGH, LOW...
    price_change_1d: Optional[float] = None
    price_change_5d: Optional[float] = None
    price_change_21d: Optional[float] = None
    price_change_63d: Optional[float] = None
    volume: Optional[float] = None
    avg_volume_30d: Optional[float] = None
    short_interest: Optional[float] = None
    beta: Optional[float] = None
    as_of_date: date = field(default_factory=date.today)


@dataclass
class ConsensusEstimate:
    """Consensus analyst estimates."""
    eps_mean: Optional[float] = None
    eps_median: Optional[float] = None
    eps_high: Optional[float] = None
    eps_low: Optional[float] = None
    eps_std: Optional[float] = None
    revenue_mean: Optional[float] = None
    revenue_median: Optional[float] = None
    num_analysts: int = 0
    as_of_date: date = field(default_factory=date.today)


@dataclass
class HistoricalEarning:
    """Historical earnings result."""
    date: date
    actual_eps: float
    estimate_eps: float
    surprise_pct: float
    beat: bool


@dataclass
class EstimateRevision:
    """Analyst estimate revision."""
    date: date
    old_estimate: float
    new_estimate: float
    direction: RevisionDirection
    change_pct: float


@dataclass
class AnalystRecommendation:
    """Analyst recommendation."""
    date: date
    firm: str
    analyst: Optional[str]
    rating: str
    rating_score: float
    price_target: Optional[float]
    previous_rating: Optional[str] = None


@dataclass 
class EarningsEvent:
    """Upcoming earnings event."""
    ticker: str
    report_date: date
    report_time: ReportTime = ReportTime.UNKNOWN
    consensus_eps: Optional[float] = None


def normalize_ticker(ticker: str) -> str:
    """Normalize ticker symbol."""
    return ticker.upper().strip()


def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert to float."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert to int."""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


# ============================================================================
# OPTION DATA STRUCTURES
# ============================================================================

class OptionType(Enum):
    """Option type: Call or Put."""
    CALL = "c"
    PUT = "p"
    
    @classmethod
    def from_string(cls, value: str) -> "OptionType":
        """Convert string to OptionType."""
        val = value.lower().strip()
        if val in ("c", "call"):
            return cls.CALL
        elif val in ("p", "put"):
            return cls.PUT
        raise ValueError(f"Invalid option type: {value}")


@dataclass
class OptionContract:
    """
    Single option contract with all relevant fields.
    
    Contains market data, Greeks, and derived analytics for agent analysis.
    """
    # Identifiers
    ticker: str
    occ_symbol: str
    option_type: OptionType
    strike: float
    expiration: date
    
    # Underlying data
    underlying_price: float
    
    # Market data
    bid: float = 0.0
    ask: float = 0.0
    last_price: float = 0.0
    mid_price: float = 0.0
    volume: int = 0
    open_interest: int = 0
    
    # Implied volatility
    implied_volatility: float = 0.0
    
    # Greeks
    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0
    vega: float = 0.0
    rho: float = 0.0
    
    # Derived analytics
    days_to_expiry: int = 0
    in_the_money: bool = False
    moneyness: float = 1.0  # S/K
    time_value: float = 0.0
    intrinsic_value: float = 0.0
    
    # Volatility analytics
    iv_daily: float = 0.0  # IV per day
    iv_to_expiry: float = 0.0  # IV scaled to expiry
    historical_vol_1m: Optional[float] = None
    iv_premium: Optional[float] = None  # IV - HV
    
    # Capture timestamp
    capture_date: date = field(default_factory=date.today)
    capture_time: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for DataFrame creation."""
        return {
            "ticker": self.ticker,
            "occ": self.occ_symbol,
            "right": self.option_type.value,
            "strike": self.strike,
            "exp": self.expiration.isoformat(),
            "stock_price": self.underlying_price,
            "bid": self.bid,
            "ask": self.ask,
            "last_price": self.last_price,
            "mid": self.mid_price,
            "volume": self.volume,
            "open_interest": self.open_interest,
            "implied_volatility": self.implied_volatility,
            "delta": self.delta,
            "gamma": self.gamma,
            "theta": self.theta,
            "vega": self.vega,
            "rho": self.rho,
            "days2exp": self.days_to_expiry,
            "in_the_money": self.in_the_money,
            "moneyness": self.moneyness,
            "timeValue": self.time_value,
            "intrinsicValue": self.intrinsic_value,
            "ivDaily": self.iv_daily,
            "ivExp": self.iv_to_expiry,
            "hvExp": self.historical_vol_1m,
            "ivPremium": self.iv_premium,
            "date": self.capture_date.isoformat(),
            "time": self.capture_time,
        }


@dataclass
class OptionChainSummary:
    """
    Summary statistics for option chain analysis.
    
    Features designed for earnings prediction agents.
    """
    ticker: str
    capture_date: date
    underlying_price: float
    
    # Chain statistics
    num_contracts: int = 0
    num_expirations: int = 0
    expirations: List[date] = field(default_factory=list)
    
    # Volume and open interest
    total_call_volume: int = 0
    total_put_volume: int = 0
    total_call_oi: int = 0
    total_put_oi: int = 0
    put_call_volume_ratio: float = 0.0
    put_call_oi_ratio: float = 0.0
    
    # Implied volatility summary
    atm_iv_call: Optional[float] = None
    atm_iv_put: Optional[float] = None
    iv_skew: Optional[float] = None  # OTM put IV - OTM call IV
    iv_term_structure: Dict[str, float] = field(default_factory=dict)
    
    # Implied move (from ATM straddle)
    implied_move_pct: Optional[float] = None
    implied_move_upper: Optional[float] = None
    implied_move_lower: Optional[float] = None
    nearest_expiry_days: Optional[int] = None
    
    # Greeks aggregates
    total_delta_calls: float = 0.0
    total_delta_puts: float = 0.0
    total_gamma: float = 0.0
    total_vega: float = 0.0
    
    # Historical vol comparison
    historical_vol_1m: Optional[float] = None
    iv_hv_spread: Optional[float] = None  # ATM IV - HV
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "ticker": self.ticker,
            "date": self.capture_date.isoformat(),
            "stock_price": self.underlying_price,
            "num_contracts": self.num_contracts,
            "num_expirations": self.num_expirations,
            "call_volume": self.total_call_volume,
            "put_volume": self.total_put_volume,
            "call_oi": self.total_call_oi,
            "put_oi": self.total_put_oi,
            "pcVolumeRatio": self.put_call_volume_ratio,
            "pcOIRatio": self.put_call_oi_ratio,
            "atmIVCall": self.atm_iv_call,
            "atmIVPut": self.atm_iv_put,
            "ivSkew": self.iv_skew,
            "impliedMovePct": self.implied_move_pct,
            "impliedMoveUpper": self.implied_move_upper,
            "impliedMoveLower": self.implied_move_lower,
            "nearestExpiryDays": self.nearest_expiry_days,
            "totalDeltaCalls": self.total_delta_calls,
            "totalDeltaPuts": self.total_delta_puts,
            "totalGamma": self.total_gamma,
            "totalVega": self.total_vega,
            "hv1m": self.historical_vol_1m,
            "ivHVSpread": self.iv_hv_spread,
        }


# ============================================================================
# OPTION PRICING (Black-Scholes)
# ============================================================================

from scipy.stats import norm


class OptionPricer:
    """
    Black-Scholes option pricer with Greeks.
    
    Thread-safe and efficient for batch calculations.
    """
    
    TRADING_DAYS_PER_YEAR = 252
    CALENDAR_DAYS_PER_YEAR = 365
    MIN_TIME = 1e-10
    MIN_VOL = 1e-10
    MAX_VOL = 5.0
    
    @staticmethod
    def calculate_greeks(
        option_type: OptionType,
        S: float,
        K: float,
        T: float,
        sigma: float,
        r: float = 0.05,
        q: float = 0.0
    ) -> Dict[str, float]:
        """
        Calculate option price and Greeks.
        
        Args:
            option_type: CALL or PUT
            S: Underlying price
            K: Strike price
            T: Time to expiry (years)
            sigma: Volatility (annualized)
            r: Risk-free rate
            q: Dividend yield
        
        Returns:
            Dict with price, delta, gamma, theta, vega, rho
        """
        T = max(T, OptionPricer.MIN_TIME)
        sigma = max(sigma, OptionPricer.MIN_VOL)
        
        sqrt_t = math.sqrt(T)
        d1 = (math.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * sqrt_t)
        d2 = d1 - sigma * sqrt_t
        
        discount = math.exp(-r * T)
        div_discount = math.exp(-q * T)
        pdf_d1 = norm.pdf(d1)
        
        if option_type == OptionType.CALL:
            price = S * div_discount * norm.cdf(d1) - K * discount * norm.cdf(d2)
            delta = div_discount * norm.cdf(d1)
            theta_term = (
                -S * div_discount * pdf_d1 * sigma / (2 * sqrt_t) +
                q * S * div_discount * norm.cdf(d1) -
                r * K * discount * norm.cdf(d2)
            )
            rho = K * T * discount * norm.cdf(d2) / 100
        else:
            price = K * discount * norm.cdf(-d2) - S * div_discount * norm.cdf(-d1)
            delta = -div_discount * norm.cdf(-d1)
            theta_term = (
                -S * div_discount * pdf_d1 * sigma / (2 * sqrt_t) -
                q * S * div_discount * norm.cdf(-d1) +
                r * K * discount * norm.cdf(-d2)
            )
            rho = -K * T * discount * norm.cdf(-d2) / 100
        
        gamma = div_discount * pdf_d1 / (S * sigma * sqrt_t)
        vega = S * div_discount * sqrt_t * pdf_d1 / 100
        theta = theta_term / OptionPricer.CALENDAR_DAYS_PER_YEAR
        
        return {
            "price": price,
            "delta": delta,
            "gamma": gamma,
            "theta": theta,
            "vega": vega,
            "rho": rho,
        }
    
    @staticmethod
    def calculate_implied_volatility(
        option_type: OptionType,
        S: float,
        K: float,
        T: float,
        market_price: float,
        r: float = 0.05,
        q: float = 0.0,
        max_iterations: int = 100,
        tolerance: float = 1e-6
    ) -> float:
        """
        Calculate implied volatility using Newton-Raphson.
        
        Args:
            option_type: CALL or PUT
            S: Underlying price
            K: Strike price  
            T: Time to expiry (years)
            market_price: Market price of option
            r: Risk-free rate
            q: Dividend yield
            max_iterations: Maximum iterations
            tolerance: Convergence tolerance
        
        Returns:
            Implied volatility
        """
        if market_price <= 0:
            return 0.0
        
        T = max(T, OptionPricer.MIN_TIME)
        
        # Initial guess based on ATM approximation
        sigma = math.sqrt(2 * math.pi / T) * market_price / S
        sigma = max(0.01, min(sigma, 2.0))
        
        for _ in range(max_iterations):
            greeks = OptionPricer.calculate_greeks(option_type, S, K, T, sigma, r, q)
            price = greeks["price"]
            vega = greeks["vega"] * 100  # Adjust back from per-percent
            
            if vega < 1e-10:
                break
            
            diff = price - market_price
            if abs(diff) < tolerance:
                return sigma
            
            sigma = sigma - diff / vega
            sigma = max(OptionPricer.MIN_VOL, min(sigma, OptionPricer.MAX_VOL))
        
        # Fallback to bisection
        return OptionPricer._bisection_iv(option_type, S, K, T, market_price, r, q)
    
    @staticmethod
    def _bisection_iv(
        option_type: OptionType,
        S: float, K: float, T: float,
        market_price: float,
        r: float, q: float,
        max_iterations: int = 100
    ) -> float:
        """Bisection fallback for IV."""
        low, high = 0.001, 3.0
        
        for _ in range(max_iterations):
            mid = (low + high) / 2
            greeks = OptionPricer.calculate_greeks(option_type, S, K, T, mid, r, q)
            
            if greeks["price"] > market_price:
                high = mid
            else:
                low = mid
            
            if high - low < 1e-6:
                return mid
        
        return mid


def get_occ_symbol(ticker: str, expiration: date, option_type: OptionType, strike: float) -> str:
    """Generate OCC standardized option symbol."""
    date_str = expiration.strftime("%y%m%d")
    type_char = "C" if option_type == OptionType.CALL else "P"
    strike_int = int(strike * 1000)
    strike_str = f"{strike_int:08d}"
    return f"{ticker.upper()}{date_str}{type_char}{strike_str}"


# ============================================================================
# BASE DATA SOURCE CLASS
# ============================================================================

class BaseDataSource:
    """Base class for data sources."""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"DataSource.{name}")
        self._connected = False
    
    def connect(self) -> bool:
        raise NotImplementedError
    
    def disconnect(self) -> None:
        raise NotImplementedError
    
    def _ensure_connected(self):
        if not self._connected:
            raise RuntimeError(f"{self.name} not connected. Call connect() first.")


# ============================================================================
# YAHOO FINANCE DATA SOURCE
# ============================================================================

class YahooFinanceDataSource(BaseDataSource):
    """
    Yahoo Finance data source with option chain support.
    
    Features for earnings prediction agents:
    - Comprehensive option chain extraction with Greeks
    - Implied volatility and skew analysis
    - Put/call ratios for sentiment
    - Implied move calculations
    
    Usage:
        config = DataSourceConfig(rate_limit_calls=100, rate_limit_period=60)
        yahoo = YahooFinanceDataSource(config)
        yahoo.connect()
        
        # Get option chain with all analytics
        chain, summary = yahoo.get_option_chain("AAPL", num_expirations=4)
        
        # Access features for agents
        print(f"Implied move: {summary.implied_move_pct:.2%}")
        print(f"Put/Call ratio: {summary.put_call_volume_ratio:.2f}")
        print(f"IV Skew: {summary.iv_skew:.4f}")
    """
    
    def __init__(self, config: DataSourceConfig):
        super().__init__("YahooFinance")
        self.config = config
        self.rate_limiter = RateLimiter(
            config.rate_limit_calls,
            config.rate_limit_period
        )
        self.yf = None
        self._risk_free_rate = 0.05  # Default, can be updated
    
    def connect(self) -> bool:
        """Connect to Yahoo Finance (initialize library)."""
        try:
            import yfinance as yf
            self.yf = yf
            self._connected = True
            self.logger.info("Yahoo Finance initialized")
            return True
        except ImportError:
            self.logger.error("yfinance not installed. Install with: pip install yfinance")
            raise
    
    def disconnect(self) -> None:
        """Disconnect from Yahoo Finance."""
        self._connected = False
        self.yf = None
        self.logger.info("Yahoo Finance disconnected")
    
    def _get_ticker(self, ticker: str):
        """Get yfinance Ticker object with rate limiting."""
        self._ensure_connected()
        self.rate_limiter.wait_if_needed()
        ticker = normalize_ticker(ticker)
        return self.yf.Ticker(ticker)
    
    def get_company_info(self, ticker: str) -> Optional[CompanyInfo]:
        """Get basic company information."""
        try:
            tick = self._get_ticker(ticker)
            info = tick.info
            
            if not info or 'symbol' not in info:
                return None
            
            return CompanyInfo(
                ticker=normalize_ticker(ticker),
                company_name=info.get('longName', info.get('shortName', ticker)),
                sector=info.get('sector', 'Unknown'),
                industry=info.get('industry', 'Unknown'),
                market_cap=safe_float(info.get('marketCap', 0)),
                exchange=info.get('exchange'),
                currency=info.get('currency', 'USD'),
                country=info.get('country'),
                description=info.get('longBusinessSummary'),
            )
        except Exception as e:
            self.logger.error(f"Failed to get company info for {ticker}: {e}")
            return None
    
    def get_price_data(self, ticker: str) -> Optional[PriceData]:
        """Get current price and momentum data."""
        try:
            tick = self._get_ticker(ticker)
            info = tick.info
            hist = tick.history(period="3mo")
            
            if hist.empty:
                return None
            
            current_price = safe_float(info.get('currentPrice', hist['Close'].iloc[-1]))
            
            price_change_1d = None
            price_change_5d = None
            price_change_21d = None
            price_change_63d = None
            
            if len(hist) >= 2:
                price_change_1d = (hist['Close'].iloc[-1] / hist['Close'].iloc[-2] - 1)
            if len(hist) >= 6:
                price_change_5d = (hist['Close'].iloc[-1] / hist['Close'].iloc[-6] - 1)
            if len(hist) >= 22:
                price_change_21d = (hist['Close'].iloc[-1] / hist['Close'].iloc[-22] - 1)
            if len(hist) >= 64:
                price_change_63d = (hist['Close'].iloc[-1] / hist['Close'].iloc[-64] - 1)
            
            avg_volume_30d = hist['Volume'].tail(30).mean() if len(hist) >= 30 else None
            
            return PriceData(
                current_price=current_price,
                price_change_1d=price_change_1d,
                price_change_5d=price_change_5d,
                price_change_21d=price_change_21d,
                price_change_63d=price_change_63d,
                volume=safe_float(hist['Volume'].iloc[-1]),
                avg_volume_30d=avg_volume_30d,
                short_interest=safe_float(info.get('shortPercentOfFloat')),
                beta=safe_float(info.get('beta')),
            )
        except Exception as e:
            self.logger.error(f"Failed to get price data for {ticker}: {e}")
            return None
    
    def get_historical_volatility(
        self,
        ticker: str,
        window: int = 22
    ) -> Optional[float]:
        """
        Calculate historical volatility.
        
        Args:
            ticker: Stock ticker
            window: Number of trading days for calculation
        
        Returns:
            Annualized historical volatility
        """
        try:
            tick = self._get_ticker(ticker)
            hist = tick.history(period="3mo")
            
            if len(hist) < window + 1:
                return None
            
            returns = hist['Close'].pct_change().dropna()
            hv = returns.tail(window).std() * math.sqrt(252)
            return float(hv)
        except Exception as e:
            self.logger.error(f"Failed to get historical volatility for {ticker}: {e}")
            return None
    
    def get_option_chain(
        self,
        ticker: str,
        num_expirations: Optional[int] = None,
        min_days_to_expiry: int = 0,
        strike_range_pct: Optional[float] = None,
        min_volume: int = 0,
        calculate_greeks: bool = True,
    ) -> Tuple[List[OptionContract], OptionChainSummary]:
        """
        Extract complete option chain with analytics for agent analysis.
        
        Args:
            ticker: Stock ticker symbol
            num_expirations: Maximum number of expirations to include
            min_days_to_expiry: Minimum days until expiration
            strike_range_pct: Filter strikes within this % of underlying (0.15 = ±15%)
            min_volume: Minimum volume filter
            calculate_greeks: Whether to calculate Greeks
        
        Returns:
            Tuple of (list of OptionContract, OptionChainSummary)
        
        Example:
            yahoo = YahooFinanceDataSource(config)
            yahoo.connect()
            
            contracts, summary = yahoo.get_option_chain("AAPL", num_expirations=4)
            
            # Use summary for agent features
            features = {
                "implied_move": summary.implied_move_pct,
                "put_call_ratio": summary.put_call_volume_ratio,
                "iv_skew": summary.iv_skew,
                "iv_hv_spread": summary.iv_hv_spread,
            }
        """
        self._ensure_connected()
        
        ticker = normalize_ticker(ticker)
        tick = self._get_ticker(ticker)
        
        # Get available expirations
        try:
            available_expirations = tick.options
        except Exception as e:
            self.logger.error(f"No options available for {ticker}: {e}")
            return [], OptionChainSummary(
                ticker=ticker,
                capture_date=date.today(),
                underlying_price=0.0
            )
        
        if not available_expirations:
            return [], OptionChainSummary(
                ticker=ticker,
                capture_date=date.today(),
                underlying_price=0.0
            )
        
        # Get current price and historical data
        hist = tick.history(period="1mo")
        if hist.empty:
            self.logger.error(f"No price data for {ticker}")
            return [], OptionChainSummary(
                ticker=ticker,
                capture_date=date.today(),
                underlying_price=0.0
            )
        
        underlying_price = float(hist['Close'].iloc[-1])
        historical_vol = hist['Close'].pct_change().dropna().std() * math.sqrt(252)
        
        # Filter expirations
        today = date.today()
        valid_expirations = []
        for exp_str in available_expirations:
            exp_date = datetime.strptime(exp_str, '%Y-%m-%d').date()
            days = (exp_date - today).days
            if days >= min_days_to_expiry:
                valid_expirations.append(exp_str)
        
        if num_expirations is not None:
            valid_expirations = valid_expirations[:num_expirations]
        
        # Price bounds for filtering
        if strike_range_pct is not None:
            price_low = underlying_price * (1 - strike_range_pct)
            price_high = underlying_price * (1 + strike_range_pct)
        else:
            price_low = 0.0
            price_high = float('inf')
        
        contracts = []
        capture_time = datetime.now().strftime("%H:%M:%S")
        
        # Process each expiration
        for exp_str in valid_expirations:
            self.rate_limiter.wait_if_needed()
            
            try:
                chain_data = tick.option_chain(exp_str)
            except Exception as e:
                self.logger.warning(f"Failed to get chain for {ticker} {exp_str}: {e}")
                continue
            
            exp_date = datetime.strptime(exp_str, '%Y-%m-%d').date()
            days_to_exp = (exp_date - today).days
            time_to_expiry = days_to_exp / 365
            
            # Process calls
            for _, row in chain_data.calls.iterrows():
                contract = self._process_option_row(
                    row=row,
                    ticker=ticker,
                    option_type=OptionType.CALL,
                    expiration=exp_date,
                    underlying_price=underlying_price,
                    days_to_exp=days_to_exp,
                    time_to_expiry=time_to_expiry,
                    historical_vol=historical_vol,
                    capture_time=capture_time,
                    calculate_greeks=calculate_greeks,
                )
                
                if contract and price_low <= contract.strike <= price_high:
                    if contract.volume >= min_volume:
                        contracts.append(contract)
            
            # Process puts
            for _, row in chain_data.puts.iterrows():
                contract = self._process_option_row(
                    row=row,
                    ticker=ticker,
                    option_type=OptionType.PUT,
                    expiration=exp_date,
                    underlying_price=underlying_price,
                    days_to_exp=days_to_exp,
                    time_to_expiry=time_to_expiry,
                    historical_vol=historical_vol,
                    capture_time=capture_time,
                    calculate_greeks=calculate_greeks,
                )
                
                if contract and price_low <= contract.strike <= price_high:
                    if contract.volume >= min_volume:
                        contracts.append(contract)
        
        # Calculate summary
        summary = self._calculate_chain_summary(
            ticker=ticker,
            underlying_price=underlying_price,
            contracts=contracts,
            historical_vol=historical_vol,
        )
        
        return contracts, summary
    
    def _process_option_row(
        self,
        row: pd.Series,
        ticker: str,
        option_type: OptionType,
        expiration: date,
        underlying_price: float,
        days_to_exp: int,
        time_to_expiry: float,
        historical_vol: float,
        capture_time: str,
        calculate_greeks: bool,
    ) -> Optional[OptionContract]:
        """Process a single option row into OptionContract."""
        try:
            strike = safe_float(row.get('strike', 0))
            if strike <= 0:
                return None
            
            bid = safe_float(row.get('bid', 0))
            ask = safe_float(row.get('ask', 0))
            last_price = safe_float(row.get('lastPrice', 0))
            mid_price = (bid + ask) / 2 if bid > 0 and ask > 0 else last_price
            
            volume = safe_int(row.get('volume', 0))
            open_interest = safe_int(row.get('open_interest', 0))
            
            # Get implied volatility from Yahoo or calculate
            iv = safe_float(row.get('implied_volatility', 0))
            
            # Calculate intrinsic and time value
            if option_type == OptionType.CALL:
                intrinsic = max(0, underlying_price - strike)
            else:
                intrinsic = max(0, strike - underlying_price)
            
            time_value = max(0, mid_price - intrinsic)
            
            # Calculate Greeks
            delta = gamma = theta = vega = rho = 0.0
            
            if calculate_greeks and iv > 0 and time_to_expiry > 0:
                try:
                    greeks = OptionPricer.calculate_greeks(
                        option_type=option_type,
                        S=underlying_price,
                        K=strike,
                        T=time_to_expiry,
                        sigma=iv,
                        r=self._risk_free_rate,
                    )
                    delta = greeks["delta"]
                    gamma = greeks["gamma"]
                    theta = greeks["theta"]
                    vega = greeks["vega"]
                    rho = greeks["rho"]
                except Exception:
                    pass
            
            # Generate OCC symbol
            occ = get_occ_symbol(ticker, expiration, option_type, strike)
            
            # Calculate IV analytics
            iv_daily = iv / math.sqrt(252) if iv > 0 else 0
            iv_exp = math.sqrt(days_to_exp / 252) * iv if iv > 0 and days_to_exp > 0 else 0
            iv_premium = iv - historical_vol if iv > 0 else None
            
            return OptionContract(
                ticker=ticker,
                occ_symbol=occ,
                option_type=option_type,
                strike=strike,
                expiration=expiration,
                underlying_price=underlying_price,
                bid=bid,
                ask=ask,
                last_price=last_price,
                mid_price=mid_price,
                volume=volume,
                open_interest=open_interest,
                implied_volatility=iv,
                delta=delta,
                gamma=gamma,
                theta=theta,
                vega=vega,
                rho=rho,
                days_to_expiry=days_to_exp,
                in_the_money=row.get('in_the_money', False),
                moneyness=underlying_price / strike,
                time_value=time_value,
                intrinsic_value=intrinsic,
                iv_daily=iv_daily,
                iv_to_expiry=iv_exp,
                historical_vol_1m=historical_vol,
                iv_premium=iv_premium,
                capture_date=date.today(),
                capture_time=capture_time,
            )
        except Exception as e:
            self.logger.warning(f"Error processing option row: {e}")
            return None
    
    def _calculate_chain_summary(
        self,
        ticker: str,
        underlying_price: float,
        contracts: List[OptionContract],
        historical_vol: float,
    ) -> OptionChainSummary:
        """Calculate summary statistics for the option chain."""
        if not contracts:
            return OptionChainSummary(
                ticker=ticker,
                capture_date=date.today(),
                underlying_price=underlying_price,
            )
        
        # Basic counts
        expirations = sorted(set(c.expiration for c in contracts))
        
        # Volume and OI
        call_contracts = [c for c in contracts if c.option_type == OptionType.CALL]
        put_contracts = [c for c in contracts if c.option_type == OptionType.PUT]
        
        total_call_volume = sum(c.volume for c in call_contracts)
        total_put_volume = sum(c.volume for c in put_contracts)
        total_call_oi = sum(c.open_interest for c in call_contracts)
        total_put_oi = sum(c.open_interest for c in put_contracts)
        
        pc_volume_ratio = total_put_volume / total_call_volume if total_call_volume > 0 else 0
        pc_oi_ratio = total_put_oi / total_call_oi if total_call_oi > 0 else 0
        
        # Find ATM options for nearest expiration
        nearest_exp = expirations[0] if expirations else None
        nearest_contracts = [c for c in contracts if c.expiration == nearest_exp]
        
        atm_iv_call = None
        atm_iv_put = None
        implied_move_pct = None
        implied_move_upper = None
        implied_move_lower = None
        
        if nearest_contracts:
            # Find ATM
            calls = [c for c in nearest_contracts if c.option_type == OptionType.CALL]
            puts = [c for c in nearest_contracts if c.option_type == OptionType.PUT]
            
            if calls:
                atm_call = min(calls, key=lambda c: abs(c.strike - underlying_price))
                atm_iv_call = atm_call.implied_volatility
            
            if puts:
                atm_put = min(puts, key=lambda c: abs(c.strike - underlying_price))
                atm_iv_put = atm_put.implied_volatility
            
            # Calculate implied move from straddle
            if atm_iv_call and atm_iv_put and calls and puts:
                atm_call = min(calls, key=lambda c: abs(c.strike - underlying_price))
                atm_put = min(puts, key=lambda c: abs(c.strike - underlying_price))
                
                straddle_price = atm_call.mid_price + atm_put.mid_price
                if straddle_price > 0:
                    implied_move_pct = straddle_price / underlying_price
                    implied_move_upper = underlying_price * (1 + implied_move_pct)
                    implied_move_lower = underlying_price * (1 - implied_move_pct)
        
        # Calculate skew (OTM put IV - OTM call IV)
        iv_skew = None
        if nearest_contracts:
            otm_puts = [c for c in nearest_contracts 
                       if c.option_type == OptionType.PUT and c.moneyness < 0.95]
            otm_calls = [c for c in nearest_contracts 
                        if c.option_type == OptionType.CALL and c.moneyness > 1.05]
            
            if otm_puts and otm_calls:
                avg_put_iv = np.mean([c.implied_volatility for c in otm_puts if c.implied_volatility])
                avg_call_iv = np.mean([c.implied_volatility for c in otm_calls if c.implied_volatility])
                if avg_put_iv and avg_call_iv:
                    iv_skew = avg_put_iv - avg_call_iv
        
        # IV term structure
        iv_term_structure = {}
        for exp in expirations:
            exp_contracts = [c for c in contracts if c.expiration == exp]
            atm_contracts = [c for c in exp_contracts if 0.95 < c.moneyness < 1.05]
            if atm_contracts:
                avg_iv = np.mean([c.implied_volatility for c in atm_contracts if c.implied_volatility])
                if avg_iv:
                    iv_term_structure[exp.isoformat()] = float(avg_iv)
        
        # Greeks aggregates (weighted by volume)
        total_delta_calls = sum(c.delta * c.volume for c in call_contracts)
        total_delta_puts = sum(c.delta * c.volume for c in put_contracts)
        total_gamma = sum(c.gamma * c.volume for c in contracts)
        total_vega = sum(c.vega * c.volume for c in contracts)
        
        # IV-HV spread
        atm_iv = ((atm_iv_call or 0) + (atm_iv_put or 0)) / 2 if (atm_iv_call or atm_iv_put) else None
        iv_hv_spread = atm_iv - historical_vol if atm_iv else None
        
        return OptionChainSummary(
            ticker=ticker,
            capture_date=date.today(),
            underlying_price=underlying_price,
            num_contracts=len(contracts),
            num_expirations=len(expirations),
            expirations=expirations,
            total_call_volume=total_call_volume,
            total_put_volume=total_put_volume,
            total_call_oi=total_call_oi,
            total_put_oi=total_put_oi,
            put_call_volume_ratio=pc_volume_ratio,
            put_call_oi_ratio=pc_oi_ratio,
            atm_iv_call=atm_iv_call,
            atm_iv_put=atm_iv_put,
            iv_skew=iv_skew,
            iv_term_structure=iv_term_structure,
            implied_move_pct=implied_move_pct,
            implied_move_upper=implied_move_upper,
            implied_move_lower=implied_move_lower,
            nearest_expiry_days=contracts[0].days_to_expiry if contracts else None,
            total_delta_calls=total_delta_calls,
            total_delta_puts=total_delta_puts,
            total_gamma=total_gamma,
            total_vega=total_vega,
            historical_vol_1m=historical_vol,
            iv_hv_spread=iv_hv_spread,
        )
    
    def get_option_chain_dataframe(
        self,
        ticker: str,
        scan_criteria: Optional[Any] = None,
        **kwargs
    ) -> pd.DataFrame:
        """
        Get option chain as pandas DataFrame.
        
        Convenience method for data export and analysis.
        
        Args:
            ticker: Stock ticker
            scan_criteria: Optional OptionChainScanner ScanCriteria for filtering
            **kwargs: Passed to get_option_chain
        
        Returns:
            DataFrame with option contracts
        """
        contracts, _ = self.get_option_chain(ticker, **kwargs)
        
        if not contracts:
            return pd.DataFrame()
        
        records = [c.to_dict() for c in contracts]
        df = pd.DataFrame(records)
        
        if scan_criteria is not None:
            try:
                from options_screener import OptionChainScanner
            except ImportError:
                import sys
                import os
                parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                if parent_dir not in sys.path:
                    sys.path.insert(0, parent_dir)
                from options_screener import OptionChainScanner
            
            try:
                scanner = OptionChainScanner(ticker)
                scanner.load_data(df)
                df = scanner.apply_scan(scan_criteria)
            except Exception as e:
                self.logger.warning(f"Failed to apply scan criteria: {e}")
        
        if df.empty:
            return df
        
        # Sort by expiration, right, strike
        df.sort_values(['exp', 'right', 'strike'], inplace=True)
        df.reset_index(drop=True, inplace=True)
        
        return df
    
    def get_earnings_implied_move(
        self,
        ticker: str,
        earnings_date: Optional[date] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate implied move around earnings date.
        
        Args:
            ticker: Stock ticker
            earnings_date: Earnings date (auto-detected if not provided)
        
        Returns:
            Dict with implied move analysis
        """
        contracts, summary = self.get_option_chain(ticker, num_expirations=6)
        
        if not contracts or not summary.implied_move_pct:
            return None
        
        return {
            "ticker": ticker,
            "underlying_price": summary.underlying_price,
            "implied_move_pct": summary.implied_move_pct,
            "implied_move_upper": summary.implied_move_upper,
            "implied_move_lower": summary.implied_move_lower,
            "nearest_expiry": summary.expirations[0] if summary.expirations else None,
            "nearest_expiry_days": summary.nearest_expiry_days,
            "atm_iv_call": summary.atm_iv_call,
            "atm_iv_put": summary.atm_iv_put,
            "iv_skew": summary.iv_skew,
            "put_call_ratio": summary.put_call_volume_ratio,
            "historical_vol": summary.historical_vol_1m,
            "iv_hv_spread": summary.iv_hv_spread,
        }
    
    # --- Existing methods from original yahoo_finance.py ---
    
    def get_consensus_estimates(self, ticker: str) -> Optional[ConsensusEstimate]:
        """Get consensus analyst estimates."""
        try:
            tick = self._get_ticker(ticker)
            info = tick.info
            
            earnings_estimate = info.get('forwardEps')
            num_analysts = safe_int(info.get('numberOfAnalystOpinions', 0))
            eps_mean = safe_float(earnings_estimate)
            eps_median = eps_mean
            eps_high = safe_float(info.get('targetHighPrice', eps_mean * 1.1 if eps_mean else None))
            eps_low = safe_float(info.get('targetLowPrice', eps_mean * 0.9 if eps_mean else None))
            eps_std = (eps_high - eps_low) / 4 if eps_high and eps_low else 0.0
            
            return ConsensusEstimate(
                eps_mean=eps_mean,
                eps_median=eps_median,
                eps_high=eps_high,
                eps_low=eps_low,
                eps_std=eps_std,
                revenue_mean=None,
                revenue_median=None,
                num_analysts=num_analysts,
            )
        except Exception as e:
            self.logger.error(f"Failed to get consensus estimates for {ticker}: {e}")
            return None
    
    def get_historical_earnings(self, ticker: str, num_quarters: int = 8) -> List[HistoricalEarning]:
        """Get historical earnings results."""
        try:
            tick = self._get_ticker(ticker)
            earnings = tick.earnings_dates
            
            if earnings is None or earnings.empty:
                return []
            
            historical = []
            now = datetime.now()
            
            for idx, row in earnings.iterrows():
                tz = getattr(idx, 'tzinfo', None)
                ref_now = datetime.now(tz) if tz else now
                
                if isinstance(idx, (datetime, date)) and idx > ref_now:
                    continue
                
                actual = row.get('Reported EPS')
                estimate = row.get('EPS Estimate')
                
                if actual is None or estimate is None:
                    continue
                
                actual_eps = safe_float(actual)
                estimate_eps = safe_float(estimate)
                
                surprise_pct = 0.0
                if estimate_eps != 0:
                    surprise_pct = ((actual_eps - estimate_eps) / abs(estimate_eps)) * 100
                
                historical.append(HistoricalEarning(
                    date=idx.date() if hasattr(idx, 'date') else idx,
                    actual_eps=actual_eps,
                    estimate_eps=estimate_eps,
                    surprise_pct=surprise_pct,
                    beat=actual_eps > estimate_eps,
                ))
                
                if len(historical) >= num_quarters:
                    break
            
            return historical
        except Exception as e:
            self.logger.error(f"Failed to get historical earnings for {ticker}: {e}")
            return []
    
    def get_analyst_recommendations(self, ticker: str, days_back: int = 90) -> List[AnalystRecommendation]:
        """Get analyst recommendations."""
        try:
            tick = self._get_ticker(ticker)
            recommendations = getattr(tick, 'upgrades_downgrades', None)
            
            if recommendations is None or recommendations.empty:
                recommendations = getattr(tick, 'recommendations', None)
            
            if recommendations is None or recommendations.empty:
                return []
            
            now = datetime.now()
            analyst_recs = []
            
            rating_map = {
                'strong buy': 5.0, 'buy': 4.5, 'outperform': 4.0, 'overweight': 4.0,
                'hold': 3.0, 'neutral': 3.0, 'equal-weight': 3.0,
                'underperform': 2.0, 'underweight': 2.0,
                'sell': 1.5, 'strong sell': 1.0,
            }
            
            for idx, row in recommendations.iterrows():
                rec_dt = idx
                if not isinstance(rec_dt, (datetime, date)):
                    rec_dt = row.get('Date', row.get('date'))
                
                if rec_dt is None:
                    continue
                
                if isinstance(rec_dt, datetime):
                    ref_now = datetime.now(rec_dt.tzinfo) if rec_dt.tzinfo else now
                    if rec_dt < ref_now - timedelta(days=days_back):
                        continue
                elif isinstance(rec_dt, date):
                    if rec_dt < now.date() - timedelta(days=days_back):
                        continue
                
                firm = row.get('Firm', row.get('firm', 'Unknown'))
                to_grade = str(row.get('ToGrade', row.get('To Grade', '')))
                from_grade = row.get('FromGrade', row.get('From Grade'))
                rating_score = rating_map.get(to_grade.lower(), 3.0)
                
                analyst_recs.append(AnalystRecommendation(
                    date=rec_dt.date() if isinstance(rec_dt, datetime) else rec_dt,
                    firm=str(firm),
                    analyst=None,
                    rating=to_grade,
                    rating_score=rating_score,
                    price_target=None,
                    previous_rating=str(from_grade) if from_grade else None,
                ))
            
            return analyst_recs
        except Exception as e:
            self.logger.error(f"Failed to get recommendations for {ticker}: {e}")
            return []
    
    def get_earnings_calendar(
        self,
        tickers: List[str],
        start_date: date,
        end_date: date
    ) -> List[EarningsEvent]:
        """Get earnings calendar for multiple tickers."""
        events = []
        
        for ticker in tickers:
            try:
                tick = self._get_ticker(ticker)
                calendar = tick.calendar
                
                if calendar is None or (hasattr(calendar, 'empty') and calendar.empty) or not calendar:
                    continue
                
                earnings_date = calendar.get('Earnings Date')
                if earnings_date is None:
                    continue
                
                if isinstance(earnings_date, list):
                    earnings_date = earnings_date[0]
                
                if isinstance(earnings_date, str):
                    earnings_date = datetime.fromisoformat(earnings_date)
                
                report_date = earnings_date.date() if isinstance(earnings_date, datetime) else earnings_date
                
                if start_date <= report_date <= end_date:
                    report_time = ReportTime.UNKNOWN
                    hour = earnings_date.hour if isinstance(earnings_date, datetime) else 0
                    
                    if hour < 12:
                        report_time = ReportTime.BMO
                    elif hour >= 16:
                        report_time = ReportTime.AMC
                    
                    info = tick.info
                    consensus_eps = safe_float(info.get('forwardEps'))
                    
                    events.append(EarningsEvent(
                        ticker=normalize_ticker(ticker),
                        report_date=report_date,
                        report_time=report_time,
                        consensus_eps=consensus_eps,
                    ))
            except Exception as e:
                self.logger.warning(f"Failed to get calendar for {ticker}: {e}")
                continue
        
        return events


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    """Test Yahoo Finance data source with option chain."""
    
    logging.basicConfig(level=logging.INFO)
    
    config = DataSourceConfig(rate_limit_calls=20, rate_limit_period=60)
    yahoo = YahooFinanceDataSource(config)
    yahoo.connect()
    
    # Test ticker
    ticker = "AAPL"
    print(f"\n{'='*60}")
    print(f"Testing Yahoo Finance Data Source: {ticker}")
    print(f"{'='*60}\n")
    
    # Company info
    print("1. Company Info:")
    info = yahoo.get_company_info(ticker)
    if info:
        print(f"   Name: {info.company_name}")
        print(f"   Sector: {info.sector}")
        print(f"   Industry: {info.industry}")
        print(f"   Market Cap: ${info.market_cap/1e9:.2f}B")
    
    # Price data
    print("\n2. Price Data:")
    price = yahoo.get_price_data(ticker)
    if price:
        print(f"   Current Price: ${price.current_price:.2f}")
        print(f"   5-Day Change: {price.price_change_5d:.2%}")
        print(f"   21-Day Change: {price.price_change_21d:.2%}")
        print(f"   Beta: {price.beta:.2f}" if price.beta else "   Beta: N/A")
    
    # Consensus estimates
    print("\n3. Consensus Estimates:")
    consensus = yahoo.get_consensus_estimates(ticker)
    if consensus:
        print(f"   EPS Mean: ${consensus.eps_mean:.2f}")
        print(f"   EPS Range: ${consensus.eps_low:.2f} - ${consensus.eps_high:.2f}")
        print(f"   Analysts: {consensus.num_analysts}")
    
    # Historical earnings
    print("\n4. Historical Earnings (Last 4):")
    historical = yahoo.get_historical_earnings(ticker, 4)
    for h in historical:
        beat_miss = "BEAT" if h.beat else "MISS"
        print(f"   {h.date}: {beat_miss} by {h.surprise_pct:+.1f}%")
    
    # Analyst recommendations
    print("\n5. Recent Recommendations:")
    recs = yahoo.get_analyst_recommendations(ticker, 90)
    for rec in recs[:5]:
        print(f"   {rec.date}: {rec.firm} - {rec.rating}")

    ticker = "SPY"
    print(f"\n{'='*60}")
    print(f"Testing Yahoo Finance Option Chain: {ticker}")
    print(f"{'='*60}\n")
    
    # Get option chain
    print("Fetching option chain...")
    contracts, summary = yahoo.get_option_chain(
        ticker,
        num_expirations=3,
        min_days_to_expiry=1,
        strike_range_pct=0.10,
        calculate_greeks=True,
    )
    
    print(f"\nChain Summary:")
    print(f"  Underlying: ${summary.underlying_price:.2f}")
    print(f"  Contracts: {summary.num_contracts}")
    print(f"  Expirations: {summary.num_expirations}")
    print(f"  Call Volume: {summary.total_call_volume:,}")
    print(f"  Put Volume: {summary.total_put_volume:,}")
    print(f"  P/C Volume Ratio: {summary.put_call_volume_ratio:.2f}")
    print(f"  ATM IV (Call): {summary.atm_iv_call:.2%}" if summary.atm_iv_call else "")
    print(f"  ATM IV (Put): {summary.atm_iv_put:.2%}" if summary.atm_iv_put else "")
    print(f"  IV Skew: {summary.iv_skew:.4f}" if summary.iv_skew else "")
    print(f"  Implied Move: {summary.implied_move_pct:.2%}" if summary.implied_move_pct else "")
    print(f"  HV (1M): {summary.historical_vol_1m:.2%}" if summary.historical_vol_1m else "")
    print(f"  IV-HV Spread: {summary.iv_hv_spread:.2%}" if summary.iv_hv_spread else "")
    
    # Show sample contracts
    if contracts:
        print(f"\nSample Contracts (first 5):")
        for c in contracts[:5]:
            print(f"  {c.occ_symbol}: {c.option_type.value.upper()} K={c.strike:.2f} "
                  f"IV={c.implied_volatility:.2%} Δ={c.delta:.3f} Mid=${c.mid_price:.2f}")
    
    # Get as DataFrame
    df = yahoo.get_option_chain_dataframe(ticker, num_expirations=2)
    print(f"\nDataFrame shape: {df.shape}")
    if not df.empty:
        print(df[['ticker', 'right', 'strike', 'exp', 'mid', 'implied_volatility', 'delta', 'volume']].head())
    else:
        print("  (No data available - network may be restricted)")
    
    # Earnings implied move
    print(f"\nEarnings Implied Move Analysis:")
    implied_move = yahoo.get_earnings_implied_move(ticker)
    if implied_move:
        print(f"  Implied Move: {implied_move['implied_move_pct']:.2%}")
        print(f"  Range: ${implied_move['implied_move_lower']:.2f} - ${implied_move['implied_move_upper']:.2f}")
        print(f"  P/C Ratio: {implied_move['put_call_ratio']:.2f}")
    
    yahoo.disconnect()
    
    print(f"\n{'='*60}")
    print("Test completed successfully!")
    print(f"{'='*60}\n")