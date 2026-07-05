from fastapi import APIRouter, HTTPException, Query, Depends, Response
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
from database.models import User, Prediction, PredictionChat, EarningsCalendarEvent, EarningsHistory
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
        statement = select(Prediction).order_by(Prediction.prediction_date.desc())
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
    start: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    sector: Optional[str] = Query(None, description="Filter by sector"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    tickers: Optional[str] = None,
    use_finviz: bool = False,
    timeframe: str = "This Week",
    index_name: str = "S&P 500",
    session: Session = Depends(get_session),
    pipeline: EarningsPipeline = Depends(get_pipeline)
):
    """
    Get the earnings calendar.
    Reads from EarningsCalendarEvent in the database, falling back to the aggregator
    if no database rows match.
    """
    try:
        eff_start = start or start_date
        eff_end = end or end_date
        
        if use_finviz:
            events = pipeline.aggregator.get_finviz_earnings(index_name, timeframe)
            return events

        if not eff_start or not eff_end:
            raise HTTPException(status_code=400, detail="start_date and end_date required if not using finviz")

        stmt = select(EarningsCalendarEvent).where(
            EarningsCalendarEvent.report_date >= eff_start,
            EarningsCalendarEvent.report_date <= eff_end
        )
        if sector:
            stmt = stmt.where(EarningsCalendarEvent.sector == sector)
        
        if tickers:
            ticker_list = [t.strip().upper() for t in tickers.split(",")]
            stmt = stmt.where(EarningsCalendarEvent.ticker.in_(ticker_list))
            
        stmt = stmt.order_by(EarningsCalendarEvent.report_date)
        db_events = session.exec(stmt).all()
        
        # If no events found, enqueue calendar sync in background
        if not db_events:
            try:
                from api.tasks import sync_earnings_calendar_task
                days_forward = max(14, (eff_end - date.today()).days)
                sync_earnings_calendar_task.delay(days_forward)
            except Exception as se:
                import logging
                logging.getLogger(__name__).warning(f"Failed to enqueue calendar sync: {se}")

        if db_events:
            results = []
            for e in db_events:
                mapped_time = "unknown"
                if e.report_time == "BMO":
                    mapped_time = "before_market_open"
                elif e.report_time == "AMC":
                    mapped_time = "after_market_close"
                
                results.append({
                    "ticker": e.ticker,
                    "company_name": e.company_name,
                    "report_date": e.report_date.isoformat() if hasattr(e.report_date, 'isoformat') else str(e.report_date),
                    "report_time": mapped_time,
                    "eps_estimate": e.eps_estimate,
                    "consensus_eps": e.eps_estimate,
                    "revenue_estimate": e.revenue_estimate,
                    "consensus_revenue": e.revenue_estimate,
                    "num_estimates": e.num_estimates,
                    "sector": e.sector,
                    "industry": e.industry,
                    "market_cap": e.market_cap,
                    "updated_at": e.updated_at.isoformat() if hasattr(e.updated_at, 'isoformat') else str(e.updated_at),
                })
            return results

        if tickers:
            ticker_list = [t.strip().upper() for t in tickers.split(",")]
        else:
            ticker_list = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA"]
            
        events = pipeline.aggregator.get_earnings_calendar(ticker_list, eff_start, eff_end)
        return events
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{ticker}")
async def get_ticker_earnings_history(
    ticker: str,
    session: Session = Depends(get_session)
):
    """
    Get historical earnings and price reactions for a ticker.
    Reads from the EarningsHistory database table, enqueuing a background
    sync task on a cache miss rather than blocking.
    """
    ticker_upper = ticker.upper()
    try:
        stmt = select(EarningsHistory).where(
            EarningsHistory.ticker == ticker_upper
        ).order_by(EarningsHistory.report_date.desc())
        
        rows = session.exec(stmt).all()
        
        if not rows:
            from api.tasks import sync_ticker_history_task
            sync_ticker_history_task.delay(ticker_upper)
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=202, content={"status": "queued", "data": []})
            
        return {"status": "ready", "data": [r.model_dump() for r in rows]}
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
            select(Prediction).order_by(Prediction.prediction_date)
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


@router.get("/{prediction_id}/report")
def download_prediction_report(
    prediction_id: int,
    format: str = Query("md", pattern="^(md|pdf)$"),
    session: Session = Depends(get_session),
    pipeline: EarningsPipeline = Depends(get_pipeline)
):
    """
    Generate and download the earnings debate report for a prediction in either MD or PDF format.
    """
    prediction = session.get(Prediction, prediction_id)
    if not prediction:
        raise HTTPException(status_code=404, detail="Prediction not found")
        
    llm_info = {
        "provider": pipeline.config.agent.provider,
        "model_name": pipeline.config.agent.model_name,
        "enable_rebuttals": pipeline.config.agent.enable_rebuttals
    }
    
    db_sync_status = f"SUCCESSFUL (Record Saved with ID: {prediction.id})"
    
    if format == "md":
        from output.report_generator import generate_markdown_report
        md_content = generate_markdown_report(prediction, db_sync_status=db_sync_status, llm_info=llm_info)
        
        headers = {
            "Content-Disposition": f"attachment; filename={prediction.ticker}_{prediction.report_date.strftime('%Y-%m-%d')}_report.md"
        }
        return Response(content=md_content, media_type="text/markdown", headers=headers)
        
    elif format == "pdf":
        from output.report_generator import FPDF_AVAILABLE
        if not FPDF_AVAILABLE:
            raise HTTPException(status_code=500, detail="PDF generation is currently unavailable on the server.")
            
        from output.report_generator import generate_pdf_report
        import tempfile
        from pathlib import Path
        
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir) / f"report.pdf"
            try:
                generate_pdf_report(prediction, temp_path, db_sync_status=db_sync_status, llm_info=llm_info)
                pdf_bytes = temp_path.read_bytes()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")
                
        headers = {
            "Content-Disposition": f"attachment; filename={prediction.ticker}_{prediction.report_date.strftime('%Y-%m-%d')}_report.pdf"
        }
        return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)


@router.post("/{prediction_id}/verify")
async def verify_prediction(
    prediction_id: int,
    clerk_id: str = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Trigger outcome verification/scoring for a specific prediction.
    """
    try:
        # Get prediction
        prediction = session.get(Prediction, prediction_id)
        if not prediction:
            raise HTTPException(status_code=404, detail=f"Prediction with ID {prediction_id} not found")

        from database.scoring_service import PredictionScorer
        from data.yahoo_finance import YahooFinanceDataSource, DataSourceConfig

        yahoo = None
        try:
            config = DataSourceConfig(rate_limit_calls=100, rate_limit_period=60)
            yahoo = YahooFinanceDataSource(config)
            yahoo.connect()
            scorer = PredictionScorer(yahoo)
            
            result = scorer.score_prediction(prediction)
            
            if result.get("scored") is True:
                prediction.actual_direction = result["actual_direction"]
                prediction.actual_eps = result.get("actual_eps")
                prediction.actual_price_move_pct = result.get("actual_price_move_pct")
                prediction.accuracy_score = result.get("accuracy_score")
                prediction.scored_at = result.get("scored_at", datetime.utcnow())
                
                session.add(prediction)
                session.commit()
                session.refresh(prediction)
                
                return {
                    "success": True,
                    "message": f"Successfully verified/scored prediction for {prediction.ticker}",
                    "result": {
                        "actual_direction": prediction.actual_direction,
                        "actual_eps": prediction.actual_eps,
                        "actual_price_move_pct": prediction.actual_price_move_pct,
                        "accuracy_score": prediction.accuracy_score,
                        "scored_at": prediction.scored_at.isoformat() if prediction.scored_at else None
                    }
                }
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Could not score prediction: {result.get('reason', 'Unknown reason')}"
                )
        finally:
            if yahoo:
                try:
                    yahoo.disconnect()
                except Exception:
                    pass
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")


@router.get("/health")

async def health():
    return {"status": "Earnings router is up"}
