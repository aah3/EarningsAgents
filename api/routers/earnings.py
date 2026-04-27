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
    force_refresh: bool = Query(False, description="Force new analysis and bypass cache"),
    clerk_id: str = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    try:
        # Ensure user exists in DB
        user = get_or_create_user(session, clerk_id)
        
        # 1. Check for cached prediction if not forcing refresh and no custom analysis
        if not force_refresh and not request.user_analysis:
            statement = select(Prediction).where(
                Prediction.user_id == user.id,
                Prediction.ticker == ticker.upper()
            ).order_by(Prediction.prediction_date.desc())
            existing_predictions = session.exec(statement).all()
            
            for p in existing_predictions:
                # Check if we already ran it today for this report
                if p.report_date.date() == request.report_date and p.prediction_date.date() == date.today():
                    return {
                        "task_id": f"cached-{p.id}",
                        "status": "PENDING",
                        "message": f"Cached analysis found for {ticker}"
                    }
        
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
async def get_task_status(
    task_id: str,
    session: Session = Depends(get_session)
):
    """
    Check the status and result of a background analysis task.
    """
    # 1. Fast path for cached predictions
    if task_id.startswith("cached-"):
        prediction_id = int(task_id.replace("cached-", ""))
        prediction = session.get(Prediction, prediction_id)
        if prediction:
            result_data = prediction.dict() if hasattr(prediction, "dict") else prediction.__dict__
            # Fix datetimes
            if isinstance(result_data.get('report_date'), datetime):
                result_data['report_date'] = result_data['report_date'].isoformat()
            if isinstance(result_data.get('prediction_date'), datetime):
                result_data['prediction_date'] = result_data['prediction_date'].isoformat()
            
            return {
                "task_id": task_id,
                "status": "SUCCESS",
                "ready": True,
                "result": result_data
            }
        
        return {
            "task_id": task_id,
            "status": "FAILURE",
            "ready": True,
            "error": "Cached prediction not found"
        }

    # 2. Regular celery task status
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

@router.get("/metrics")
async def get_performance_metrics(
    clerk_id: str = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Return aggregate evaluation metrics for the authenticated user's predictions.

    Only predictions that have been scored (actual_direction is not None) are
    included in win-rate / Brier calculations.  Unscored predictions are
    still counted in totals.
    """
    try:
        user = get_or_create_user(session, clerk_id)

        all_preds = session.exec(
            select(Prediction).where(Prediction.user_id == user.id)
            .order_by(Prediction.prediction_date)
        ).all()

        total = len(all_preds)
        scored = [p for p in all_preds if p.actual_direction is not None]
        n_scored = len(scored)

        win_rate = 0.0
        avg_brier = 0.0
        beat_correct = miss_correct = beat_total = miss_total = 0
        brier_over_time = []
        confidence_raw: dict[str, list] = {}

        for p in scored:
            correct = p.direction.lower() == p.actual_direction.lower()
            if correct:
                if p.direction.upper() == "BEAT":
                    beat_correct += 1
                else:
                    miss_correct += 1
            if p.direction.upper() == "BEAT":
                beat_total += 1
            else:
                miss_total += 1

            brier = p.accuracy_score if p.accuracy_score is not None else (p.confidence - (1.0 if correct else 0.0)) ** 2
            avg_brier += brier
            brier_over_time.append({
                "date": p.prediction_date.isoformat() if hasattr(p.prediction_date, "isoformat") else str(p.prediction_date),
                "brier": round(brier, 4),
                "ticker": p.ticker,
            })

            # Confidence calibration bucket (10%-wide)
            bucket_lo = int(p.confidence * 100 // 10) * 10
            bucket_key = f"{bucket_lo}-{bucket_lo + 10}%"
            if bucket_key not in confidence_raw:
                confidence_raw[bucket_key] = {"predicted": bucket_lo + 5, "wins": 0, "total": 0}
            confidence_raw[bucket_key]["wins"] += int(correct)
            confidence_raw[bucket_key]["total"] += 1

        win_rate = sum(1 for p in scored if p.direction.lower() == p.actual_direction.lower()) / n_scored if n_scored else 0.0
        avg_brier = avg_brier / n_scored if n_scored else 0.0

        confidence_buckets = [
            {
                "bucket": k,
                "predicted": v["predicted"],
                "actual_win_rate": round(v["wins"] / v["total"], 3) if v["total"] else 0.0,
                "count": v["total"],
            }
            for k, v in sorted(confidence_raw.items())
        ]

        # Direction breakdown (all predictions)
        direction_breakdown: dict[str, int] = {}
        for p in all_preds:
            direction_breakdown[p.direction.upper()] = direction_breakdown.get(p.direction.upper(), 0) + 1

        # Agent vote breakdown (from agent_votes JSON where available)
        agent_vote_breakdown: dict[str, dict[str, int]] = {}
        for p in all_preds:
            if p.agent_votes:
                for agent, vote in p.agent_votes.items():
                    if agent not in agent_vote_breakdown:
                        agent_vote_breakdown[agent] = {}
                    agent_vote_breakdown[agent][vote.upper()] = agent_vote_breakdown[agent].get(vote.upper(), 0) + 1

        avg_confidence = sum(p.confidence for p in all_preds) / total if total else 0.0

        return {
            "total_predictions": total,
            "scored_predictions": n_scored,
            "win_rate": round(win_rate, 4),
            "avg_confidence": round(avg_confidence, 4),
            "avg_brier_score": round(avg_brier, 4),
            "beat_predictions": beat_total,
            "miss_predictions": miss_total,
            "beat_correct": beat_correct,
            "miss_correct": miss_correct,
            "direction_breakdown": direction_breakdown,
            "agent_vote_breakdown": agent_vote_breakdown,
            "brier_over_time": brier_over_time,
            "confidence_buckets": confidence_buckets,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health():
    return {"status": "Earnings router is up"}
