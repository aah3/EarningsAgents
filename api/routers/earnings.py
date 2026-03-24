from fastapi import APIRouter, HTTPException, Query, Depends
from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel
from sqlmodel import Session, select
import sys
import os

# Add the project root to sys.path to import existing modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from pipeline import EarningsPipeline
from config.settings import PipelineConfig, load_config
from database.db import get_session
from database.models import User, Prediction, PredictionChat
from api.dependencies.auth import get_current_user

router = APIRouter(
    prefix="/earnings",
    tags=["earnings"],
)

def get_or_create_user(session: Session, clerk_id: str):
    statement = select(User).where(User.clerk_id == clerk_id)
    user = session.exec(statement).first()
    if not user:
        user = User(clerk_id=clerk_id)
        session.add(user)
        session.commit()
        session.refresh(user)
    return user

# Initialize pipeline as a singleton-like object for the router
_pipeline_instance = None

def get_pipeline():
    global _pipeline_instance
    if _pipeline_instance is None:
        config = load_config()
        # Ensure output dir is manageable
        config.output_dir = "api_output"
        _pipeline_instance = EarningsPipeline(config)
        _pipeline_instance.initialize()
    return _pipeline_instance

from api.tasks import analyze_ticker_task
from celery.result import AsyncResult

class PredictRequest(BaseModel):
    report_date: date
    user_analysis: Optional[str] = None

class BatchPredictItem(BaseModel):
    ticker: str
    report_date: date
    user_analysis: Optional[str] = None

class BatchPredictRequest(BaseModel):
    companies: List[BatchPredictItem]
    prediction_date: Optional[date] = None

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    ticker: str
    prediction_id: Optional[int] = None
    messages: List[ChatMessage]

@router.post("/predict/{ticker}")
async def predict_ticker(
    ticker: str, 
    request: PredictRequest,
    clerk_id: str = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    try:
        # Ensure user exists in DB
        get_or_create_user(session, clerk_id)
        
        # Dispatch background task
        task = analyze_ticker_task.delay(
            ticker.upper(), 
            request.report_date.isoformat(), 
            clerk_id,
            request.user_analysis or ""
        )
        
        return {
            "task_id": task.id,
            "status": "PENDING",
            "message": f"Analysis for {ticker} started in background"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """
    Check the status and result of a background analysis task.
    """
    res = AsyncResult(task_id)
    
    if res.ready():
        result_data = res.result
        if isinstance(result_data, dict) and result_data.get("status") == "FAILURE":
            return {
                "task_id": task_id,
                "status": "SUCCESS", # The task completed (even if with internal error)
                "ready": True,
                "error": result_data.get("error")
            }
        
        return {
            "task_id": task_id,
            "status": "SUCCESS",
            "ready": True,
            "result": result_data
        }
    
    return {
        "task_id": task_id,
        "status": res.status,
        "ready": False
    }

@router.get("/history")
async def get_prediction_history(
    clerk_id: str = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    try:
        user = get_or_create_user(session, clerk_id)
        statement = select(Prediction).where(Prediction.user_id == user.id).order_by(Prediction.prediction_date.desc())
        predictions = session.exec(statement).all()
        return predictions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat")
async def chat_with_consensus(
    request: ChatRequest,
    clerk_id: str = Depends(get_current_user),
    session: Session = Depends(get_session),
    pipeline: EarningsPipeline = Depends(get_pipeline)
):
    try:
        user = get_or_create_user(session, clerk_id)
        
        # format messages for LLM
        messages_dict = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        
        # query ConsensusAgent
        response_text = pipeline.agent_system.consensus_agent.chat(messages_dict)
        
        # append agent response
        messages_dict.append({"role": "model", "content": response_text})
        
        # persist chat locally
        chat_session = PredictionChat(
            user_id=user.id,
            prediction_id=request.prediction_id,
            ticker=request.ticker,
            messages=messages_dict
        )
        session.add(chat_session)
        session.commit()
        session.refresh(chat_session)
        
        return {
            "chat_id": chat_session.id,
            "response": response_text,
            "messages": messages_dict
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/chat/history")
async def get_all_chats(
    clerk_id: str = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    try:
        user = get_or_create_user(session, clerk_id)
        statement = select(PredictionChat).where(PredictionChat.user_id == user.id).order_by(PredictionChat.created_at.desc())
        chats = session.exec(statement).all()
        return chats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/weekly")
async def get_weekly_predictions(
    week_start: date,
    pipeline: EarningsPipeline = Depends(get_pipeline)
):
    try:
        predictions = pipeline.run_weekly(week_start)
        return predictions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/daily")
async def get_daily_predictions(
    target_date: date,
    pipeline: EarningsPipeline = Depends(get_pipeline)
):
    """
    Get earnings predictions for all companies reporting on a specific day.
    """
    try:
        predictions = pipeline.run_daily(target_date)
        return predictions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/calendar")
def get_earnings_calendar(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    tickers: Optional[str] = None,
    use_finviz: bool = False,
    timeframe: str = "This Week",
    index_name: str = "S&P 500",
    pipeline: EarningsPipeline = Depends(get_pipeline)
):
    """
    Get the earnings calendar.
    If 'use_finviz' is true, it uses 'timeframe' and 'index_name'.
    Otherwise, uses Yahoo Finance via 'start_date', 'end_date', and 'tickers'.
    """
    try:
        if use_finviz:
            events = pipeline.aggregator.get_finviz_earnings(index_name, timeframe)
            return events

        if not start_date or not end_date:
            raise HTTPException(status_code=400, detail="start_date and end_date required if not using finviz")

        if tickers:
            ticker_list = [t.strip().upper() for t in tickers.split(",")]
        else:
            ticker_list = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA"]
            
        events = pipeline.aggregator.get_earnings_calendar(ticker_list, start_date, end_date)
        return events
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sentiment/{ticker}")
async def get_sentiment(
    ticker: str,
    days_back: int = 30,
    pipeline: EarningsPipeline = Depends(get_pipeline)
):
    """
    Get recent news sentiment and options features for a company without running a full prediction.
    """
    try:
        report_date = date.today()
        # We invoke get_company_data safely to extract the company name, options features, etc.
        company_data = pipeline.aggregator.get_company_data(ticker.upper(), report_date, include_news=False)
        
        # Then we specifically pull down the news and sentiment 
        news = pipeline.aggregator.get_news_with_sentiment(
            ticker.upper(), 
            company_data.company_name, 
            days_back=days_back,
            max_articles=20
        )
        
        return {
            "ticker": ticker.upper(),
            "company_name": company_data.company_name,
            "options_features": company_data.options_features,
            "news_sentiment": news
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/batch")
async def predict_batch(
    request: BatchPredictRequest,
    pipeline: EarningsPipeline = Depends(get_pipeline)
):
    """
    Run predictions for a bespoke list of tickers and reporting dates.
    """
    try:
        companies_dicts = [
            {
                "ticker": item.ticker.upper(),
                "report_date": item.report_date,
                "user_analysis": item.user_analysis
            }
            for item in request.companies
        ]
        
        predictions = pipeline.predict_batch(
            companies_dicts,
            prediction_date=request.prediction_date
        )
        return predictions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health():
    return {"status": "Earnings router is up"}
