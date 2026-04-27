from datetime import datetime
from typing import List, Optional
from sqlmodel import SQLModel, Field, Relationship, Column, JSON

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    clerk_id: str = Field(index=True, unique=True)
    email: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    predictions: List["Prediction"] = Relationship(back_populates="user")
    chats: List["PredictionChat"] = Relationship(back_populates="user")

class Prediction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    ticker: str = Field(index=True)
    company_name: str
    report_date: datetime
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
