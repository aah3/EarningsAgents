from datetime import datetime, date
from typing import List, Optional, Dict
from sqlmodel import SQLModel, Field, Relationship, Column, JSON, UniqueConstraint

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    clerk_id: str = Field(index=True, unique=True)
    email: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    predictions: List["Prediction"] = Relationship(back_populates="user")
    chats: List["PredictionChat"] = Relationship(back_populates="user")
    settings: Optional["UserSettings"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"uselist": False, "cascade": "all, delete-orphan"}
    )

class UserSettings(SQLModel, table=True):
    __tablename__ = "user_settings"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True, unique=True)
    
    # LLM Settings
    provider: str = Field(default="gemini")
    model_name: str = Field(default="gemini-flash-latest")
    temperature: float = Field(default=0.3)
    max_tokens: int = Field(default=8192)
    use_react: bool = Field(default=False)
    react_max_turns: int = Field(default=6)
    enable_rebuttals: bool = Field(default=False)
    
    # API Keys (stored locally in plain text/unmasked in database)
    gemini_api_key: Optional[str] = Field(default=None)
    openai_api_key: Optional[str] = Field(default=None)
    anthropic_api_key: Optional[str] = Field(default=None)
    newsapi_api_key: Optional[str] = Field(default=None)
    alphavantage_api_key: Optional[str] = Field(default=None)
    earningsapi_api_key: Optional[str] = Field(default=None)
    
    user: Optional[User] = Relationship(back_populates="settings")


class Prediction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    ticker: str = Field(index=True)
    company_name: str
    company_description: Optional[str] = Field(default=None)
    sector: Optional[str] = Field(default=None)
    report_date: datetime
    report_timing: Optional[str] = Field(default=None)
    prediction_date: datetime = Field(default_factory=datetime.utcnow)
    direction: str # BEAT / MISS
    confidence: float
    
    # Extended predictions
    expected_price_move: str = Field(default="")
    move_vs_implied: str = Field(default="")
    guidance_expectation: str = Field(default="")
    
    reasoning_summary: str
    
    # Store bull/bear factors as JSON
    bull_factors: List[str] = Field(sa_column=Column(JSON))
    bear_factors: List[str] = Field(sa_column=Column(JSON))
    
    debate_summary: Optional[str] = Field(default=None)
    rebuttal_summary: Optional[str] = Field(default=None)  # Bull/Bear cross-examination transcript

    # Store votes and options features as JSON
    agent_votes: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    options_features: Optional[dict] = Field(default=None, sa_column=Column(JSON))

    # Outcome tracking (populated by the scoring task after earnings are reported)
    actual_direction: Optional[str] = Field(default=None)          # "beat", "miss", or "meet"
    actual_eps: Optional[float] = Field(default=None)              # Reported EPS
    actual_price_move_pct: Optional[float] = Field(default=None)   # % price change day-after earnings
    accuracy_score: Optional[float] = Field(default=None)          # Brier score: (confidence - correct)^2, lower = better
    scored_at: Optional[datetime] = Field(default=None)            # When the scoring task ran
    
    user: Optional[User] = Relationship(back_populates="predictions")
    chats: List["PredictionChat"] = Relationship(back_populates="prediction")

class PredictionChat(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    prediction_id: Optional[int] = Field(default=None, foreign_key="prediction.id")
    ticker: str = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Store list of messages: [{"role": "user", "content": "..."}, {"role": "model", "content": "..."}]
    messages: List[dict] = Field(sa_column=Column(JSON))
    
    user: Optional[User] = Relationship(back_populates="chats")
    prediction: Optional[Prediction] = Relationship(back_populates="chats")


class CompanyProfile(SQLModel, table=True):
    __tablename__ = "company_profile"
    ticker: str = Field(primary_key=True)
    company_name: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[float] = None
    exchange: Optional[str] = None
    country: Optional[str] = None
    cik: Optional[str] = None
    outstanding_shares: Optional[float] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class EarningsHistory(SQLModel, table=True):
    __tablename__ = "earnings_history"
    __table_args__ = (UniqueConstraint("ticker", "report_date", name="uq_hist_ticker_date"),)
    
    id: Optional[int] = Field(default=None, primary_key=True)
    ticker: str = Field(index=True)
    report_date: date = Field(index=True)
    report_time: Optional[str] = None
    fiscal_quarter: Optional[str] = None
    fiscal_year: Optional[int] = None
    # EPS
    eps_actual: Optional[float] = None
    eps_estimate: Optional[float] = None
    eps_surprise_pct: Optional[float] = None
    eps_yoy: Optional[float] = None
    eps_beat: Optional[bool] = None
    # Revenue
    revenue_actual: Optional[float] = None
    revenue_estimate: Optional[float] = None
    revenue_surprise_pct: Optional[float] = None
    revenue_yoy: Optional[float] = None
    revenue_beat: Optional[bool] = None
    # Post-earnings reaction
    reaction_1d_pct: Optional[float] = None
    reaction_5d_pct: Optional[float] = None
    reaction_volume: Optional[float] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    provenance: Dict[str, str] = Field(default_factory=dict, sa_column=Column(JSON))


class EarningsCalendarEvent(SQLModel, table=True):
    __tablename__ = "earnings_calendar_event"
    __table_args__ = (UniqueConstraint("ticker", "report_date", name="uq_cal_ticker_date"),)
    
    id: Optional[int] = Field(default=None, primary_key=True)
    ticker: str = Field(index=True)
    company_name: Optional[str] = None
    report_date: date = Field(index=True)
    report_time: Optional[str] = None
    eps_estimate: Optional[float] = None
    revenue_estimate: Optional[float] = None
    num_estimates: Optional[int] = None
    # denormalized enrichment for fast tab reads
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[float] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)
