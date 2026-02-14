"""
Options Analytics Library for Earnings Prediction System.

Provides Black-Scholes option pricing and Greeks calculations with:
- Proper type hints and validation
- Comprehensive error handling
- Clean, efficient API
- Unit tests

Usage:
    from options import Option, OptionChain, OptionType
    
    # Single option
    opt = Option(
        option_type=OptionType.CALL,
        underlying_price=100.0,
        strike=105.0,
        time_to_expiry=0.25,  # or use eval_date + exp_date
        volatility=0.20,
        risk_free_rate=0.05
    )
    
    price = opt.price
    greeks = opt.greeks
    
    # Or calculate implied volatility
    opt_iv = Option.from_market_price(
        option_type=OptionType.CALL,
        underlying_price=100.0,
        strike=105.0,
        time_to_expiry=0.25,
        market_price=3.50,
        risk_free_rate=0.05
    )
    print(f"Implied Vol: {opt_iv.implied_volatility:.2%}")
"""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple, Union

import numpy as np
from scipy.stats import norm


# ============================================================================
# ENUMS AND CONSTANTS
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
        else:
            raise ValueError(f"Invalid option type: {value}. Use 'c'/'call' or 'p'/'put'")


class OptionError(Exception):
    """Base exception for option-related errors."""
    pass


class ValidationError(OptionError):
    """Raised when option parameters are invalid."""
    pass


class CalculationError(OptionError):
    """Raised when a calculation fails."""
    pass


# Trading days per year (standard assumption)
TRADING_DAYS_PER_YEAR = 252
CALENDAR_DAYS_PER_YEAR = 365

# Numerical constants
MIN_TIME_TO_EXPIRY = 1e-10  # Avoid division by zero
MIN_VOLATILITY = 1e-10
MAX_VOLATILITY = 10.0  # 1000% annualized vol
MAX_IMPLIED_VOL_ITERATIONS = 100
IMPLIED_VOL_TOLERANCE = 1e-6


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass(frozen=True)
class Greeks:
    """
    Option Greeks - sensitivities of option price to various factors.
    
    Attributes:
        delta: Rate of change of price with respect to underlying (dP/dS)
        gamma: Rate of change of delta with respect to underlying (d²P/dS²)
        theta: Rate of change of price with respect to time (dP/dt), daily
        vega: Rate of change of price with respect to volatility (dP/dσ), per 1%
        rho: Rate of change of price with respect to interest rate (dP/dr), per 1%
        vomma: Second derivative of price with respect to volatility (d²P/dσ²)
    """
    delta: float
    gamma: float
    theta: float  # Daily theta
    vega: float   # Per 1% vol change
    rho: float    # Per 1% rate change
    vomma: float = 0.0
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            "delta": self.delta,
            "gamma": self.gamma,
            "theta": self.theta,
            "vega": self.vega,
            "rho": self.rho,
            "vomma": self.vomma,
        }


@dataclass
class OptionData:
    """
    Standardized option data structure for chain analysis.
    
    Used for storing and processing option chain data.
    """
    ticker: str
    option_type: OptionType
    strike: float
    expiration: date
    underlying_price: float
    
    # Market data
    bid: Optional[float] = None
    ask: Optional[float] = None
    last_price: Optional[float] = None
    volume: Optional[int] = None
    open_interest: Optional[int] = None
    
    # Calculated fields
    mid_price: Optional[float] = None
    implied_volatility: Optional[float] = None
    
    # Greeks
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    
    # Metadata
    days_to_expiry: Optional[int] = None
    in_the_money: Optional[bool] = None
    occ_symbol: Optional[str] = None
    
    # Additional analytics for earnings
    implied_move_pct: Optional[float] = None
    moneyness: Optional[float] = None  # S/K
    
    def __post_init__(self):
        """Calculate derived fields."""
        # Mid price
        if self.mid_price is None and self.bid is not None and self.ask is not None:
            self.mid_price = (self.bid + self.ask) / 2
        
        # Days to expiry
        if self.days_to_expiry is None and self.expiration:
            self.days_to_expiry = (self.expiration - date.today()).days
        
        # In the money
        if self.in_the_money is None:
            if self.option_type == OptionType.CALL:
                self.in_the_money = self.underlying_price > self.strike
            else:
                self.in_the_money = self.underlying_price < self.strike
        
        # Moneyness
        if self.moneyness is None and self.strike > 0:
            self.moneyness = self.underlying_price / self.strike
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "ticker": self.ticker,
            "right": self.option_type.value,
            "strike": self.strike,
            "exp": self.expiration.isoformat() if self.expiration else None,
            "stockPrice": self.underlying_price,
            "bid": self.bid,
            "ask": self.ask,
            "lastPrice": self.last_price,
            "mid": self.mid_price,
            "volume": self.volume,
            "openInterest": self.open_interest,
            "impliedVolatility": self.implied_volatility,
            "delta": self.delta,
            "gamma": self.gamma,
            "theta": self.theta,
            "vega": self.vega,
            "days2exp": self.days_to_expiry,
            "inTheMoney": self.in_the_money,
            "occ": self.occ_symbol,
            "impliedMovePct": self.implied_move_pct,
            "moneyness": self.moneyness,
        }


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def parse_date(date_input: Union[str, date, datetime, float, int]) -> date:
    """
    Parse various date formats into a date object.
    
    Args:
        date_input: Date in various formats (str, date, datetime, float/int as YYYYMMDD)
    
    Returns:
        date object
    
    Raises:
        ValidationError: If date cannot be parsed
    """
    if isinstance(date_input, date) and not isinstance(date_input, datetime):
        return date_input
    
    if isinstance(date_input, datetime):
        return date_input.date()
    
    if isinstance(date_input, (float, int)):
        # Assume YYYYMMDD format
        date_str = str(int(date_input))
        if len(date_str) == 8:
            return date(int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8]))
        raise ValidationError(f"Cannot parse numeric date: {date_input}")
    
    if isinstance(date_input, str):
        date_input = date_input.strip()
        
        # Try common formats
        formats = [
            "%Y-%m-%d",      # 2024-01-15
            "%Y/%m/%d",      # 2024/01/15
            "%m/%d/%Y",      # 01/15/2024
            "%Y%m%d",        # 20240115
            "%d-%m-%Y",      # 15-01-2024
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_input, fmt).date()
            except ValueError:
                continue
        
        raise ValidationError(f"Cannot parse date string: {date_input}")
    
    raise ValidationError(f"Unsupported date type: {type(date_input)}")


def calculate_time_to_expiry(
    eval_date: Union[str, date, datetime],
    exp_date: Union[str, date, datetime],
    use_calendar_days: bool = True
) -> float:
    """
    Calculate time to expiry in years.
    
    Args:
        eval_date: Evaluation date
        exp_date: Expiration date
        use_calendar_days: If True, use 365 days/year; if False, use 252 trading days
    
    Returns:
        Time to expiry in years (annualized)
    
    Raises:
        ValidationError: If dates are invalid
    """
    eval_d = parse_date(eval_date)
    exp_d = parse_date(exp_date)
    
    days = (exp_d - eval_d).days
    
    if days < 0:
        raise ValidationError(f"Expiration date {exp_d} is before evaluation date {eval_d}")
    
    days_per_year = CALENDAR_DAYS_PER_YEAR if use_calendar_days else TRADING_DAYS_PER_YEAR
    
    return max(days / days_per_year, MIN_TIME_TO_EXPIRY)


def get_occ_symbol(
    ticker: str,
    expiration: Union[str, date],
    option_type: Union[str, OptionType],
    strike: float
) -> str:
    """
    Generate OCC (Options Clearing Corporation) standardized option symbol.
    
    Format: SYMBOL + YYMMDD + C/P + STRIKE*1000 (8 digits, zero-padded)
    Example: AAPL240119C00150000 (AAPL Jan 19 2024 $150 Call)
    
    Args:
        ticker: Underlying ticker symbol
        expiration: Expiration date
        option_type: 'c'/'call' or 'p'/'put'
        strike: Strike price
    
    Returns:
        OCC symbol string
    """
    exp_date = parse_date(expiration)
    
    if isinstance(option_type, str):
        option_type = OptionType.from_string(option_type)
    
    # Format: YYMMDD
    date_str = exp_date.strftime("%y%m%d")
    
    # Option type
    type_char = "C" if option_type == OptionType.CALL else "P"
    
    # Strike: multiply by 1000 and zero-pad to 8 characters
    strike_int = int(strike * 1000)
    strike_str = f"{strike_int:08d}"
    
    return f"{ticker.upper()}{date_str}{type_char}{strike_str}"


# ============================================================================
# OPTION CLASS
# ============================================================================

class Option:
    """
    Black-Scholes Option pricing and Greeks calculator.
    
    Supports both European calls and puts with continuous dividend yield.
    
    Attributes:
        option_type: CALL or PUT
        S: Underlying price
        K: Strike price
        T: Time to expiry (years)
        sigma: Volatility (annualized, decimal form)
        r: Risk-free rate (annualized, decimal form)
        q: Dividend yield (annualized, decimal form)
    
    Example:
        >>> opt = Option(
        ...     option_type=OptionType.CALL,
        ...     underlying_price=100.0,
        ...     strike=105.0,
        ...     time_to_expiry=0.25,
        ...     volatility=0.20,
        ...     risk_free_rate=0.05
        ... )
        >>> print(f"Price: ${opt.price:.2f}")
        >>> print(f"Delta: {opt.greeks.delta:.4f}")
    """
    
    def __init__(
        self,
        option_type: Union[str, OptionType],
        underlying_price: float,
        strike: float,
        time_to_expiry: Optional[float] = None,
        volatility: float = 0.20,
        risk_free_rate: float = 0.05,
        dividend_yield: float = 0.0,
        eval_date: Optional[Union[str, date]] = None,
        exp_date: Optional[Union[str, date]] = None,
        market_price: Optional[float] = None,
    ):
        """
        Initialize Option.
        
        Args:
            option_type: 'c'/'call' for Call, 'p'/'put' for Put
            underlying_price: Current price of underlying asset
            strike: Option strike price
            time_to_expiry: Time to expiry in years (alternative to dates)
            volatility: Annualized volatility (e.g., 0.20 for 20%)
            risk_free_rate: Annualized risk-free rate
            dividend_yield: Continuous dividend yield
            eval_date: Evaluation date (if using dates instead of time_to_expiry)
            exp_date: Expiration date (if using dates instead of time_to_expiry)
            market_price: Market price (optional, for implied vol calculation)
        
        Raises:
            ValidationError: If parameters are invalid
        """
        # Parse option type
        if isinstance(option_type, str):
            self.option_type = OptionType.from_string(option_type)
        else:
            self.option_type = option_type
        
        # Validate and store parameters
        self.S = self._validate_positive(underlying_price, "underlying_price")
        self.K = self._validate_positive(strike, "strike")
        self.r = float(risk_free_rate)
        self.q = float(dividend_yield)
        self.market_price = market_price
        
        # Calculate time to expiry
        if time_to_expiry is not None:
            self.T = max(float(time_to_expiry), MIN_TIME_TO_EXPIRY)
        elif eval_date is not None and exp_date is not None:
            self.T = calculate_time_to_expiry(eval_date, exp_date)
        else:
            raise ValidationError(
                "Must provide either time_to_expiry or both eval_date and exp_date"
            )
        
        # Validate and store volatility
        self.sigma = self._validate_volatility(volatility)
        
        # Store dates if provided
        self.eval_date = parse_date(eval_date) if eval_date else None
        self.exp_date = parse_date(exp_date) if exp_date else None
        
        # Cache for calculated values
        self._d1: Optional[float] = None
        self._d2: Optional[float] = None
        self._price: Optional[float] = None
        self._greeks: Optional[Greeks] = None
        self._implied_vol: Optional[float] = None
    
    @staticmethod
    def _validate_positive(value: float, name: str) -> float:
        """Validate that a value is positive."""
        val = float(value)
        if val <= 0:
            raise ValidationError(f"{name} must be positive, got {val}")
        return val
    
    @staticmethod
    def _validate_volatility(vol: float) -> float:
        """Validate volatility is in reasonable range."""
        vol = float(vol)
        if vol < MIN_VOLATILITY:
            raise ValidationError(f"Volatility must be >= {MIN_VOLATILITY}, got {vol}")
        if vol > MAX_VOLATILITY:
            raise ValidationError(f"Volatility must be <= {MAX_VOLATILITY}, got {vol}")
        return vol
    
    def _clear_cache(self):
        """Clear cached calculations."""
        self._d1 = None
        self._d2 = None
        self._price = None
        self._greeks = None
    
    @property
    def d1(self) -> float:
        """Calculate d1 in Black-Scholes formula."""
        if self._d1 is None:
            sqrt_t = math.sqrt(self.T)
            self._d1 = (
                math.log(self.S / self.K) + 
                (self.r - self.q + 0.5 * self.sigma ** 2) * self.T
            ) / (self.sigma * sqrt_t)
        return self._d1
    
    @property
    def d2(self) -> float:
        """Calculate d2 in Black-Scholes formula."""
        if self._d2 is None:
            self._d2 = self.d1 - self.sigma * math.sqrt(self.T)
        return self._d2
    
    @property
    def price(self) -> float:
        """Calculate theoretical option price using Black-Scholes."""
        if self._price is None:
            self._price = self._calculate_price()
        return self._price
    
    def _calculate_price(self) -> float:
        """Internal price calculation."""
        discount_factor = math.exp(-self.r * self.T)
        dividend_discount = math.exp(-self.q * self.T)
        
        if self.option_type == OptionType.CALL:
            return (
                self.S * dividend_discount * norm.cdf(self.d1) -
                self.K * discount_factor * norm.cdf(self.d2)
            )
        else:  # PUT
            return (
                self.K * discount_factor * norm.cdf(-self.d2) -
                self.S * dividend_discount * norm.cdf(-self.d1)
            )
    
    @property
    def greeks(self) -> Greeks:
        """Calculate all Greeks."""
        if self._greeks is None:
            self._greeks = self._calculate_greeks()
        return self._greeks
    
    def _calculate_greeks(self) -> Greeks:
        """Internal Greeks calculation."""
        sqrt_t = math.sqrt(self.T)
        discount_factor = math.exp(-self.r * self.T)
        dividend_discount = math.exp(-self.q * self.T)
        pdf_d1 = norm.pdf(self.d1)
        
        # Delta
        if self.option_type == OptionType.CALL:
            delta = dividend_discount * norm.cdf(self.d1)
        else:
            delta = -dividend_discount * norm.cdf(-self.d1)
        
        # Gamma (same for calls and puts)
        gamma = dividend_discount * pdf_d1 / (self.S * self.sigma * sqrt_t)
        
        # Vega (per 1% change in volatility)
        vega = self.S * dividend_discount * sqrt_t * pdf_d1 / 100
        
        # Theta (daily decay)
        theta_common = (
            -self.S * dividend_discount * pdf_d1 * self.sigma / (2 * sqrt_t)
        )
        
        if self.option_type == OptionType.CALL:
            theta = (
                theta_common +
                self.q * self.S * dividend_discount * norm.cdf(self.d1) -
                self.r * self.K * discount_factor * norm.cdf(self.d2)
            ) / CALENDAR_DAYS_PER_YEAR
        else:
            theta = (
                theta_common -
                self.q * self.S * dividend_discount * norm.cdf(-self.d1) +
                self.r * self.K * discount_factor * norm.cdf(-self.d2)
            ) / CALENDAR_DAYS_PER_YEAR
        
        # Rho (per 1% change in interest rate)
        if self.option_type == OptionType.CALL:
            rho = self.K * self.T * discount_factor * norm.cdf(self.d2) / 100
        else:
            rho = -self.K * self.T * discount_factor * norm.cdf(-self.d2) / 100
        
        # Vomma (volga) - second derivative w.r.t. volatility
        vomma = vega * self.d1 * self.d2 / self.sigma
        
        return Greeks(
            delta=delta,
            gamma=gamma,
            theta=theta,
            vega=vega,
            rho=rho,
            vomma=vomma,
        )
    
    @property
    def delta(self) -> float:
        """Option delta."""
        return self.greeks.delta
    
    @property
    def gamma(self) -> float:
        """Option gamma."""
        return self.greeks.gamma
    
    @property
    def theta(self) -> float:
        """Option theta (daily)."""
        return self.greeks.theta
    
    @property
    def vega(self) -> float:
        """Option vega (per 1% vol change)."""
        return self.greeks.vega
    
    def get_implied_volatility(
        self,
        market_price: Optional[float] = None,
        initial_guess: float = 0.20,
        tolerance: float = IMPLIED_VOL_TOLERANCE,
        max_iterations: int = MAX_IMPLIED_VOL_ITERATIONS
    ) -> float:
        """
        Calculate implied volatility using Newton-Raphson method.
        
        Args:
            market_price: Market price of option (uses stored if not provided)
            initial_guess: Starting volatility guess
            tolerance: Convergence tolerance
            max_iterations: Maximum iterations
        
        Returns:
            Implied volatility
        
        Raises:
            CalculationError: If convergence fails
        """
        price = market_price or self.market_price
        if price is None:
            raise ValidationError("Market price required for implied vol calculation")
        
        if price <= 0:
            raise ValidationError(f"Market price must be positive, got {price}")
        
        # Store original volatility
        original_sigma = self.sigma
        
        # Newton-Raphson iteration
        sigma = initial_guess
        
        for i in range(max_iterations):
            self.sigma = sigma
            self._clear_cache()
            
            theo_price = self.price
            vega = self.greeks.vega * 100  # Convert back from per 1%
            
            if vega < 1e-10:
                # Vega too small, use bisection fallback
                break
            
            price_diff = theo_price - price
            
            if abs(price_diff) < tolerance:
                self._implied_vol = sigma
                # Restore original sigma if needed
                self.sigma = original_sigma
                self._clear_cache()
                return sigma
            
            # Newton-Raphson update
            sigma = sigma - price_diff / vega
            
            # Ensure sigma stays in valid range
            sigma = max(MIN_VOLATILITY, min(sigma, MAX_VOLATILITY))
        
        # Fallback to bisection if Newton-Raphson fails
        return self._implied_vol_bisection(price, tolerance, max_iterations)
    
    def _implied_vol_bisection(
        self,
        market_price: float,
        tolerance: float,
        max_iterations: int
    ) -> float:
        """Bisection fallback for implied volatility."""
        low_vol = MIN_VOLATILITY
        high_vol = MAX_VOLATILITY
        
        for _ in range(max_iterations):
            mid_vol = (low_vol + high_vol) / 2
            self.sigma = mid_vol
            self._clear_cache()
            
            theo_price = self.price
            price_diff = theo_price - market_price
            
            if abs(price_diff) < tolerance:
                return mid_vol
            
            if price_diff > 0:
                high_vol = mid_vol
            else:
                low_vol = mid_vol
        
        warnings.warn(
            f"Implied vol did not converge after {max_iterations} iterations. "
            f"Using {mid_vol:.4f}"
        )
        return mid_vol
    
    @property
    def implied_volatility(self) -> Optional[float]:
        """Get stored implied volatility."""
        if self._implied_vol is None and self.market_price is not None:
            self._implied_vol = self.get_implied_volatility()
        return self._implied_vol
    
    @classmethod
    def from_market_price(
        cls,
        option_type: Union[str, OptionType],
        underlying_price: float,
        strike: float,
        market_price: float,
        time_to_expiry: Optional[float] = None,
        risk_free_rate: float = 0.05,
        dividend_yield: float = 0.0,
        eval_date: Optional[Union[str, date]] = None,
        exp_date: Optional[Union[str, date]] = None,
    ) -> "Option":
        """
        Create Option and calculate implied volatility from market price.
        
        Returns:
            Option with implied_volatility calculated
        """
        opt = cls(
            option_type=option_type,
            underlying_price=underlying_price,
            strike=strike,
            time_to_expiry=time_to_expiry,
            volatility=0.20,  # Initial guess
            risk_free_rate=risk_free_rate,
            dividend_yield=dividend_yield,
            eval_date=eval_date,
            exp_date=exp_date,
            market_price=market_price,
        )
        
        # Calculate and store implied vol
        iv = opt.get_implied_volatility()
        opt.sigma = iv
        opt._implied_vol = iv
        opt._clear_cache()
        
        return opt
    
    def get_all(self) -> Tuple[float, float, float, float, float, float, float]:
        """
        Get price and all Greeks.
        
        Returns:
            Tuple of (price, delta, theta, gamma, vega, vomma_pos, vomma_neg)
            
        Note: vomma_pos and vomma_neg are the same (included for backward compatibility)
        """
        g = self.greeks
        return (self.price, g.delta, g.theta, g.gamma, g.vega, g.vomma, g.vomma)
    
    def __repr__(self) -> str:
        type_str = "CALL" if self.option_type == OptionType.CALL else "PUT"
        return (
            f"Option({type_str}, S={self.S:.2f}, K={self.K:.2f}, "
            f"T={self.T:.4f}, σ={self.sigma:.2%})"
        )


# ============================================================================
# OPTION CHAIN ANALYTICS
# ============================================================================

@dataclass
class ImpliedMoveData:
    """Implied move analysis from ATM straddle pricing."""
    expiration: date
    days_to_expiry: int
    atm_straddle_price: float
    implied_move_pct: float
    implied_volatility: float
    underlying_price: float
    upper_range: float  # +1 std dev
    lower_range: float  # -1 std dev


class OptionChainAnalyzer:
    """
    Analyze option chains for earnings predictions.
    
    Extracts features useful for ML/agent analysis:
    - Implied volatility term structure
    - Put/Call ratios
    - Implied moves around earnings
    - Skew analysis
    """
    
    def __init__(
        self,
        ticker: str,
        underlying_price: float,
        options: List[OptionData],
        risk_free_rate: float = 0.05,
    ):
        """
        Initialize analyzer.
        
        Args:
            ticker: Underlying ticker
            underlying_price: Current stock price
            options: List of OptionData objects
            risk_free_rate: Risk-free rate for calculations
        """
        self.ticker = ticker
        self.underlying_price = underlying_price
        self.options = options
        self.risk_free_rate = risk_free_rate
    
    def get_implied_move(
        self,
        expiration: Optional[date] = None,
        std_dev: float = 1.0
    ) -> Optional[ImpliedMoveData]:
        """
        Calculate implied move from ATM straddle.
        
        Args:
            expiration: Target expiration (uses nearest if None)
            std_dev: Number of standard deviations for range
        
        Returns:
            ImpliedMoveData or None
        """
        # Filter options by expiration
        if expiration:
            exp_options = [o for o in self.options if o.expiration == expiration]
        else:
            # Use nearest expiration with sufficient data
            expirations = sorted(set(o.expiration for o in self.options))
            exp_options = []
            for exp in expirations:
                opts = [o for o in self.options if o.expiration == exp]
                if len(opts) >= 4:  # Need at least some puts and calls
                    exp_options = opts
                    expiration = exp
                    break
        
        if not exp_options:
            return None
        
        # Find ATM options (nearest strike to underlying)
        atm_call = None
        atm_put = None
        min_call_diff = float('inf')
        min_put_diff = float('inf')
        
        for opt in exp_options:
            diff = abs(opt.strike - self.underlying_price)
            if opt.option_type == OptionType.CALL and diff < min_call_diff:
                min_call_diff = diff
                atm_call = opt
            elif opt.option_type == OptionType.PUT and diff < min_put_diff:
                min_put_diff = diff
                atm_put = opt
        
        if not atm_call or not atm_put:
            return None
        
        # Calculate straddle price
        call_price = atm_call.mid_price or atm_call.last_price or 0
        put_price = atm_put.mid_price or atm_put.last_price or 0
        straddle_price = call_price + put_price
        
        if straddle_price <= 0:
            return None
        
        # Calculate implied move
        implied_move_pct = straddle_price / self.underlying_price
        days = (expiration - date.today()).days
        
        if days <= 0:
            return None
        
        # Annualize to get implied vol
        implied_vol = implied_move_pct * math.sqrt(CALENDAR_DAYS_PER_YEAR / days)
        
        return ImpliedMoveData(
            expiration=expiration,
            days_to_expiry=days,
            atm_straddle_price=straddle_price,
            implied_move_pct=implied_move_pct,
            implied_volatility=implied_vol,
            underlying_price=self.underlying_price,
            upper_range=self.underlying_price * (1 + std_dev * implied_move_pct),
            lower_range=self.underlying_price * (1 - std_dev * implied_move_pct),
        )
    
    def get_put_call_ratios(self) -> Dict[str, Dict[str, float]]:
        """
        Calculate put/call ratios by expiration.
        
        Returns:
            Dict with volume and OI ratios per expiration
        """
        ratios = {}
        
        expirations = sorted(set(o.expiration for o in self.options))
        
        for exp in expirations:
            exp_opts = [o for o in self.options if o.expiration == exp]
            
            put_volume = sum(o.volume or 0 for o in exp_opts if o.option_type == OptionType.PUT)
            call_volume = sum(o.volume or 0 for o in exp_opts if o.option_type == OptionType.CALL)
            
            put_oi = sum(o.open_interest or 0 for o in exp_opts if o.option_type == OptionType.PUT)
            call_oi = sum(o.open_interest or 0 for o in exp_opts if o.option_type == OptionType.CALL)
            
            ratios[exp.isoformat()] = {
                "volume_ratio": put_volume / call_volume if call_volume > 0 else 0,
                "oi_ratio": put_oi / call_oi if call_oi > 0 else 0,
                "put_volume": put_volume,
                "call_volume": call_volume,
                "put_oi": put_oi,
                "call_oi": call_oi,
            }
        
        return ratios
    
    def get_skew(
        self,
        expiration: Optional[date] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate volatility skew.
        
        Returns:
            Dict with skew metrics
        """
        if expiration:
            exp_opts = [o for o in self.options if o.expiration == expiration]
        else:
            expirations = sorted(set(o.expiration for o in self.options))
            if not expirations:
                return None
            exp_opts = [o for o in self.options if o.expiration == expirations[0]]
        
        if not exp_opts:
            return None
        
        # Get IVs by moneyness
        put_ivs = [
            (o.moneyness, o.implied_volatility)
            for o in exp_opts
            if o.option_type == OptionType.PUT and o.implied_volatility
        ]
        call_ivs = [
            (o.moneyness, o.implied_volatility)
            for o in exp_opts
            if o.option_type == OptionType.CALL and o.implied_volatility
        ]
        
        if not put_ivs and not call_ivs:
            return None
        
        # Calculate skew as IV difference between OTM puts and OTM calls
        otm_put_iv = np.mean([iv for m, iv in put_ivs if m < 0.95]) if put_ivs else 0
        atm_iv = np.mean([iv for m, iv in (put_ivs + call_ivs) if 0.97 < m < 1.03])
        otm_call_iv = np.mean([iv for m, iv in call_ivs if m > 1.05]) if call_ivs else 0
        
        return {
            "expiration": expiration.isoformat() if expiration else None,
            "otm_put_iv": float(otm_put_iv) if otm_put_iv else None,
            "atm_iv": float(atm_iv) if atm_iv else None,
            "otm_call_iv": float(otm_call_iv) if otm_call_iv else None,
            "put_skew": float(otm_put_iv - atm_iv) if otm_put_iv and atm_iv else None,
            "call_skew": float(otm_call_iv - atm_iv) if otm_call_iv and atm_iv else None,
        }
    
    def get_chain_features(self) -> Dict[str, Any]:
        """
        Extract all features for agent analysis.
        
        Returns:
            Dict with comprehensive chain features
        """
        features = {
            "ticker": self.ticker,
            "underlying_price": self.underlying_price,
            "num_options": len(self.options),
            "expirations": sorted([exp.isoformat() for exp in set(o.expiration for o in self.options)]),
        }
        
        # Implied moves
        implied_move = self.get_implied_move()
        if implied_move:
            features["implied_move"] = {
                "expiration": implied_move.expiration.isoformat(),
                "days_to_expiry": implied_move.days_to_expiry,
                "straddle_price": implied_move.atm_straddle_price,
                "implied_move_pct": implied_move.implied_move_pct,
                "implied_vol": implied_move.implied_volatility,
                "upper_range": implied_move.upper_range,
                "lower_range": implied_move.lower_range,
            }
        
        # Put/Call ratios
        features["put_call_ratios"] = self.get_put_call_ratios()
        
        # Skew
        skew = self.get_skew()
        if skew:
            features["skew"] = skew
        
        # Aggregate stats
        total_volume = sum(o.volume or 0 for o in self.options)
        total_oi = sum(o.open_interest or 0 for o in self.options)
        features["total_volume"] = total_volume
        features["total_open_interest"] = total_oi
        
        return features


# ============================================================================
# TESTS
# ============================================================================

def run_tests():
    """Run unit tests for the options module."""
    import traceback
    
    tests_passed = 0
    tests_failed = 0
    
    def assert_close(actual, expected, tolerance=0.01, msg=""):
        """Assert two values are close within tolerance."""
        if abs(actual - expected) > tolerance:
            raise AssertionError(
                f"{msg}: Expected {expected}, got {actual}, diff={abs(actual-expected)}"
            )
    
    # Test 1: Basic Call Option Price
    print("Test 1: Basic Call Option Pricing...")
    try:
        opt = Option(
            option_type=OptionType.CALL,
            underlying_price=100.0,
            strike=100.0,
            time_to_expiry=1.0,
            volatility=0.20,
            risk_free_rate=0.05,
            dividend_yield=0.0
        )
        # Expected: ~10.45 for ATM 1-year call with 20% vol
        assert_close(opt.price, 10.45, tolerance=0.5, msg="Call price")
        assert_close(opt.delta, 0.64, tolerance=0.05, msg="Call delta")
        print(f"  ✓ Call price: ${opt.price:.2f}, delta: {opt.delta:.4f}")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        tests_failed += 1
    
    # Test 2: Basic Put Option Price
    print("Test 2: Basic Put Option Pricing...")
    try:
        opt = Option(
            option_type=OptionType.PUT,
            underlying_price=100.0,
            strike=100.0,
            time_to_expiry=1.0,
            volatility=0.20,
            risk_free_rate=0.05,
        )
        # Put-Call parity check
        call_opt = Option(
            option_type=OptionType.CALL,
            underlying_price=100.0,
            strike=100.0,
            time_to_expiry=1.0,
            volatility=0.20,
            risk_free_rate=0.05,
        )
        parity_diff = call_opt.price - opt.price - (100 - 100 * math.exp(-0.05))
        assert_close(parity_diff, 0, tolerance=0.01, msg="Put-call parity")
        assert opt.delta < 0, "Put delta should be negative"
        print(f"  ✓ Put price: ${opt.price:.2f}, delta: {opt.delta:.4f}")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        tests_failed += 1
    
    # Test 3: Greeks calculation
    print("Test 3: Greeks Calculation...")
    try:
        opt = Option(
            option_type=OptionType.CALL,
            underlying_price=100.0,
            strike=100.0,
            time_to_expiry=0.25,
            volatility=0.20,
            risk_free_rate=0.05,
        )
        greeks = opt.greeks
        assert greeks.gamma > 0, "Gamma should be positive"
        assert greeks.vega > 0, "Vega should be positive"
        assert greeks.theta < 0, "Theta should be negative for long options"
        print(f"  ✓ Gamma: {greeks.gamma:.4f}, Vega: {greeks.vega:.4f}, Theta: {greeks.theta:.4f}")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        tests_failed += 1
    
    # Test 4: Implied Volatility
    print("Test 4: Implied Volatility Calculation...")
    try:
        # Create option with known vol and get price
        original_opt = Option(
            option_type=OptionType.CALL,
            underlying_price=100.0,
            strike=105.0,
            time_to_expiry=0.25,
            volatility=0.25,
            risk_free_rate=0.05,
        )
        market_price = original_opt.price
        
        # Recover IV from price
        recovered_opt = Option.from_market_price(
            option_type=OptionType.CALL,
            underlying_price=100.0,
            strike=105.0,
            time_to_expiry=0.25,
            market_price=market_price,
            risk_free_rate=0.05,
        )
        assert_close(recovered_opt.implied_volatility, 0.25, tolerance=0.001, msg="IV recovery")
        print(f"  ✓ Original vol: 25%, Recovered IV: {recovered_opt.implied_volatility:.2%}")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        traceback.print_exc()
        tests_failed += 1
    
    # Test 5: Date parsing and time to expiry
    print("Test 5: Date Parsing and Time to Expiry...")
    try:
        d1 = parse_date("2024-06-15")
        d2 = parse_date("06/15/2024")
        d3 = parse_date(20240615)
        assert d1 == d2 == d3, "All date formats should parse to same date"
        
        t = calculate_time_to_expiry("2024-01-01", "2025-01-01")
        assert_close(t, 1.0, tolerance=0.01, msg="Time to expiry")
        print(f"  ✓ Date parsing and TTY calculation correct")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        tests_failed += 1
    
    # Test 6: OCC Symbol Generation
    print("Test 6: OCC Symbol Generation...")
    try:
        occ = get_occ_symbol("AAPL", "2024-01-19", "c", 150.0)
        expected = "AAPL240119C00150000"
        assert occ == expected, f"Expected {expected}, got {occ}"
        
        occ2 = get_occ_symbol("SPY", date(2024, 3, 15), OptionType.PUT, 450.50)
        expected2 = "SPY240315P00450500"
        assert occ2 == expected2, f"Expected {expected2}, got {occ2}"
        print(f"  ✓ OCC symbols: {occ}, {occ2}")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        tests_failed += 1
    
    # Test 7: Validation errors
    print("Test 7: Validation Errors...")
    try:
        # Should raise for negative price
        try:
            Option(OptionType.CALL, -100, 100, time_to_expiry=0.25, volatility=0.2)
            raise AssertionError("Should have raised ValidationError for negative price")
        except ValidationError:
            pass
        
        # Should raise for invalid vol
        try:
            Option(OptionType.CALL, 100, 100, time_to_expiry=0.25, volatility=15.0)
            raise AssertionError("Should have raised ValidationError for extreme vol")
        except ValidationError:
            pass
        
        print("  ✓ Validation errors raised correctly")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        tests_failed += 1
    
    # Test 8: get_all backward compatibility
    print("Test 8: get_all() Backward Compatibility...")
    try:
        opt = Option(
            option_type="c",
            underlying_price=100.0,
            strike=100.0,
            time_to_expiry=0.25,
            volatility=0.20,
            risk_free_rate=0.05,
        )
        price, delta, theta, gamma, vega, vommap, vomman = opt.get_all()
        assert price == opt.price
        assert delta == opt.delta
        assert theta == opt.theta
        assert gamma == opt.gamma
        assert vega == opt.vega
        print(f"  ✓ get_all() returns correct tuple")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        tests_failed += 1
    
    # Test 9: Option using date strings
    print("Test 9: Option with Date Strings...")
    try:
        opt = Option(
            option_type=OptionType.CALL,
            underlying_price=100.0,
            strike=100.0,
            volatility=0.20,
            risk_free_rate=0.05,
            eval_date="2024-01-01",
            exp_date="2024-04-01",
        )
        # Should be about 0.25 years
        assert_close(opt.T, 0.2466, tolerance=0.01, msg="Time to expiry from dates")
        print(f"  ✓ Option with dates: T={opt.T:.4f} years")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        tests_failed += 1
    
    # Summary
    print(f"\n{'='*50}")
    print(f"Tests Passed: {tests_passed}")
    print(f"Tests Failed: {tests_failed}")
    print(f"{'='*50}\n")
    
    return tests_failed == 0


if __name__ == "__main__":
    print("Options Analytics Library - Test Suite\n")
    success = run_tests()
    
    if success:
        print("All tests passed! ✓")
    else:
        print("Some tests failed! ✗")
        exit(1)