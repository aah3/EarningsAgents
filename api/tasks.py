import logging
from api.celery_app import celery_app
from datetime import date, datetime
from typing import Dict, Any
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from pipeline import EarningsPipeline
from config.settings import load_config
from database.db import Session, engine
from database.models import User, Prediction
from sqlmodel import select

logger = logging.getLogger(__name__)

# Singleton pipeline for the worker
_pipeline = None

def get_pipeline():
    global _pipeline
    if _pipeline is None:
        config = load_config()
        config.output_dir = "worker_output"
        _pipeline = EarningsPipeline(config)
        _pipeline.initialize()
    return _pipeline

@celery_app.task(bind=True, name="api.tasks.analyze_ticker_task")
def analyze_ticker_task(self, ticker: str, report_date_str: str, clerk_id: str, user_analysis: str = ""):
    """
    Background task to analyze a ticker and save results.
    """
    task_id = self.request.id
    logger.info(f"Starting background analysis for {ticker} (Task ID: {task_id})")
    
    report_date = date.fromisoformat(report_date_str)
    pipeline = get_pipeline()
    
    try:
        import redis
        import json
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        r = redis.from_url(redis_url, socket_timeout=5)

        try:
            r.publish(f"task_updates:{task_id}", json.dumps({"status": "RUNNING", "message": f"Started analysis for {ticker}"}))
        except Exception as e:
            logger.warning(f"Failed to publish to redis: {e}")

        # 1. Run Analysis
        raw_result = pipeline.predict_single(ticker, report_date, task_id=task_id, user_analysis=user_analysis if user_analysis else None)
        
        from dataclasses import asdict
        result = asdict(raw_result)
        
        # Serialize enums for JSON
        if hasattr(raw_result.direction, "value"):
            result["direction"] = raw_result.direction.value
            
        # Serialize dates for JSON
        for k, v in result.items():
            if isinstance(v, (date, datetime)):
                result[k] = v.isoformat()
        
        # 2. Save directly to DB from worker
        with Session(engine) as session:
            # Get user
            statement = select(User).where(User.clerk_id == clerk_id)
            user = session.exec(statement).first()
            
            if not user:
                user = User(clerk_id=clerk_id)
                session.add(user)
                session.commit()
                session.refresh(user)
            
            # Save prediction
            db_prediction = Prediction(
                user_id=user.id,
                ticker=ticker.upper(),
                company_name=result.get("company_name", "Unknown"),
                report_date=datetime.combine(report_date, datetime.min.time()),
                direction=result.get("direction", "NEUTRAL").upper(),
                confidence=result.get("confidence", 0.0),
                expected_price_move=result.get("expected_price_move", ""),
                move_vs_implied=result.get("move_vs_implied", ""),
                guidance_expectation=result.get("guidance_expectation", ""),
                reasoning_summary=result.get("reasoning_summary", ""),
                bull_factors=result.get("bull_factors", []),
                bear_factors=result.get("bear_factors", []),
                debate_summary=result.get("debate_summary"),
                rebuttal_summary=result.get("rebuttal_summary"),
            )
            
            session.add(db_prediction)
            session.commit()
            
        logger.info(f"Successfully completed analysis for {ticker}")
        return {"status": "SUCCESS", "ticker": ticker, "result": result}
        
    except Exception as e:
        logger.error(f"Task failed for {ticker}: {str(e)}")
        return {"status": "FAILURE", "error": str(e)}

from scoring_service import PredictionScorer
from data.yahoo_finance import YahooFinanceDataSource, DataSourceConfig
from datetime import timedelta as _timedelta

# How many calendar days after the report_date to wait before scoring.
# Earnings need ~1 business day to appear in Yahoo Finance earnings history.
SCORE_AFTER_DAYS = int(os.getenv("SCORE_AFTER_DAYS", "1"))


@celery_app.task(
    bind=True,
    name="api.tasks.score_predictions_task",
    max_retries=3,
    default_retry_delay=300,  # 5 min between retries on total failure
)
def score_predictions_task(self):
    """
    Periodic Celery Beat task: fetches post-earnings ground truth for every
    unscored prediction whose report_date is at least SCORE_AFTER_DAYS old,
    then writes actual_direction, actual_eps, actual_price_move_pct, and
    accuracy_score (Brier) back to the Prediction row.
    """
    logger.info(f"[score_predictions_task] Starting (grace_period={SCORE_AFTER_DAYS}d)")

    try:
        config = DataSourceConfig(rate_limit_calls=100, rate_limit_period=60)
        yahoo = YahooFinanceDataSource(config)
        yahoo.connect()
        scorer = PredictionScorer(yahoo)
    except Exception as exc:
        logger.error(f"[score_predictions_task] Failed to initialise scorer: {exc}")
        raise self.retry(exc=exc)

    scored = 0
    skipped = 0
    errors = 0

    # Only consider predictions whose report_date is old enough for earnings to
    # have been reported AND which haven't been scored yet.
    cutoff = datetime.utcnow() - _timedelta(days=SCORE_AFTER_DAYS)

    with Session(engine) as session:
        statement = (
            select(Prediction)
            .where(Prediction.report_date <= cutoff)
            .where(Prediction.actual_direction == None)  # noqa: E711
        )
        unscored = session.exec(statement).all()
        logger.info(f"[score_predictions_task] {len(unscored)} unscored predictions to process")

        for p in unscored:
            try:
                result = scorer.score_prediction(p)
                if result.get("scored") is True:
                    p.actual_direction = result["actual_direction"]
                    p.actual_eps = result.get("actual_eps")
                    p.actual_price_move_pct = result.get("actual_price_move_pct")
                    p.accuracy_score = result.get("accuracy_score")
                    p.scored_at = result.get("scored_at", datetime.utcnow())
                    session.add(p)
                    session.commit()
                    scored += 1
                    logger.info(f"[score_predictions_task] Scored {p.ticker}: "
                                f"predicted={p.direction} actual={p.actual_direction} "
                                f"brier={p.accuracy_score:.4f}")
                else:
                    logger.warning(f"[score_predictions_task] Skipped {p.ticker}: {result.get('reason')}")
                    skipped += 1
            except Exception as exc:
                # Isolate per-ticker failures — never let one bad ticker abort the batch
                logger.error(f"[score_predictions_task] Error scoring {p.ticker}: {exc}", exc_info=True)
                errors += 1

    summary = {"scored": scored, "skipped": skipped, "errors": errors}
    logger.info(f"[score_predictions_task] Done: {summary}")
    return summary


@celery_app.task(name="api.tasks.beat_heartbeat")
def beat_heartbeat():
    """Lightweight liveness probe — fired every minute by Celery Beat."""
    logger.debug("[beat_heartbeat] alive")
    return {"alive": True, "ts": datetime.utcnow().isoformat()}
