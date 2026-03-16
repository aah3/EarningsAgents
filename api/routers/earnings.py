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

@router.get("/health")
async def health():
    return {"status": "Earnings router is up"}
