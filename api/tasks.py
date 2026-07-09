import logging
from api.celery_app import celery_app
from datetime import date, datetime
from typing import Dict, Any, Optional
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from pipeline import EarningsPipeline
from settings import load_config
from database.earnings_repo import _refresh_profile, sync_ticker_history
from data.earningsapi_source import RateLimitError
from database.db import Session, engine
from database.models import User, Prediction, CompanyProfile, EarningsHistory, EarningsCalendarEvent, UserSettings
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
    
    # Check for user-specific settings overrides
    pipeline = None
    with Session(engine) as session:
        statement = select(User).where(User.clerk_id == clerk_id)
        user = session.exec(statement).first()
        if user:
            statement_settings = select(UserSettings).where(UserSettings.user_id == user.id)
            user_settings = session.exec(statement_settings).first()
            if user_settings:
                # check if there are overrides
                has_overrides = any([
                    user_settings.provider != "gemini",
                    user_settings.model_name != "gemini-flash-latest",
                    user_settings.temperature != 0.3,
                    user_settings.max_tokens != 8192,
                    user_settings.use_react is True,
                    user_settings.enable_rebuttals is True,
                    user_settings.gemini_api_key is not None,
                    user_settings.openai_api_key is not None,
                    user_settings.anthropic_api_key is not None,
                    user_settings.newsapi_api_key is not None,
                    user_settings.alphavantage_api_key is not None,
                    user_settings.earningsapi_api_key is not None
                ])
                if has_overrides:
                    logger.info(f"Custom user overrides found for user {clerk_id}. Initializing bespoke pipeline.")
                    config = load_config()
                    config.output_dir = "worker_output"
                    
                    if user_settings.provider:
                        config.agent.provider = user_settings.provider.lower()
                    if user_settings.model_name:
                        config.agent.model_name = user_settings.model_name
                    if user_settings.temperature is not None:
                        config.agent.temperature = user_settings.temperature
                    if user_settings.max_tokens is not None:
                        config.agent.max_tokens = user_settings.max_tokens
                    if user_settings.use_react is not None:
                        config.agent.use_react = user_settings.use_react
                    if user_settings.react_max_turns is not None:
                        config.agent.react_max_turns = user_settings.react_max_turns
                    if user_settings.enable_rebuttals is not None:
                        config.agent.enable_rebuttals = user_settings.enable_rebuttals
                        
                    # Apply keys
                    if config.agent.provider == "gemini" and user_settings.gemini_api_key:
                        config.agent.api_key = user_settings.gemini_api_key
                    elif config.agent.provider == "openai" and user_settings.openai_api_key:
                        config.agent.api_key = user_settings.openai_api_key
                    elif config.agent.provider == "anthropic" and user_settings.anthropic_api_key:
                        config.agent.api_key = user_settings.anthropic_api_key
                        
                    if user_settings.newsapi_api_key:
                        config.newsapi.api_key = user_settings.newsapi_api_key
                        config.newsapi.enabled = True
                    if user_settings.alphavantage_api_key:
                        config.alphavantage.api_key = user_settings.alphavantage_api_key
                        config.alphavantage.enabled = True
                    if user_settings.earningsapi_api_key:
                        config.earningsapi.api_key = user_settings.earningsapi_api_key
                        config.earningsapi.enabled = True
                        
                    pipeline = EarningsPipeline(config)
                    pipeline.initialize()
                    
    if pipeline is None:
        logger.info(f"Using default pipeline configuration for user {clerk_id}.")
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
                company_description=result.get("company_description"),
                sector=result.get("sector"),
                report_date=datetime.combine(report_date, datetime.min.time()),
                report_timing=result.get("report_time", "UNKNOWN"),
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
                agent_votes=result.get("agent_votes"),
                options_features=result.get("options_features"),
            )
            
            session.add(db_prediction)
            session.commit()
            session.refresh(db_prediction)
            
            # Enqueue ticker history sync on active user analysis
            sync_ticker_history_task.delay(ticker.upper())
            
            # Re-export report to update DB sync details (successful save with record ID)
            if getattr(pipeline.config, "save_report", True):
                try:
                    from output.report_generator import export_report
                    llm_info = {
                        "provider": pipeline.config.agent.provider,
                        "model_name": pipeline.config.agent.model_name,
                        "enable_rebuttals": pipeline.config.agent.enable_rebuttals
                    }
                    export_report(
                        prediction=db_prediction,
                        reports_dir=getattr(pipeline.config, "reports_dir", "reports"),
                        elapsed_time=None,
                        db_sync_status=f"SUCCESSFUL (Record Saved with ID: {db_prediction.id})",
                        llm_info=llm_info
                    )
                except Exception as re:
                    logger.warning(f"Failed to update report with DB sync details: {re}")
            
        logger.info(f"Successfully completed analysis for {ticker}")
        return {"status": "SUCCESS", "ticker": ticker, "result": result}

        
    except Exception as e:
        logger.error(f"Task failed for {ticker}: {str(e)}")
        return {"status": "FAILURE", "error": str(e)}

from database.scoring_service import PredictionScorer
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


# Removed local _refresh_profile (imported from database.earnings_repo)


@celery_app.task(bind=True, name="api.tasks.sync_earnings_calendar_task",
                 autoretry_for=(RateLimitError,), retry_backoff=True,
                 retry_backoff_max=600, max_retries=5)
def sync_earnings_calendar_task(self, days_forward: int = 14):
    """
    Sync upcoming earnings calendar events.
    """
    logger.info(f"Starting earnings calendar sync for the next {days_forward} days")
    config = load_config()
    from data.earningsapi_source import EarningsAPIDataSource
    source = EarningsAPIDataSource(config.earningsapi)
    if not source.connect():
        logger.error("Failed to connect to EarningsAPIDataSource")
        return {"status": "FAILURE", "error": "Connection failed"}
        
    try:
        today = date.today()
        all_events = []
        for i in range(days_forward + 1):
            target_date = today + _timedelta(days=i)
            day_events = source.get_calendar_by_date(target_date)
            all_events.extend(day_events)
            
        with Session(engine) as session:
            distinct_tickers = set()
            for ev in all_events:
                ticker = ev["ticker"].upper()
                report_date = ev["report_date"]
                distinct_tickers.add(ticker)
                
                # Check for existing event
                stmt = select(EarningsCalendarEvent).where(
                    EarningsCalendarEvent.ticker == ticker,
                    EarningsCalendarEvent.report_date == report_date
                )
                db_event = session.exec(stmt).first()
                if not db_event:
                    db_event = EarningsCalendarEvent(
                        ticker=ticker,
                        report_date=report_date
                    )
                
                db_event.company_name = ev.get("company_name")
                db_event.report_time = ev.get("report_time")
                db_event.eps_estimate = ev.get("eps_estimate")
                db_event.revenue_estimate = ev.get("revenue_estimate")
                db_event.num_estimates = ev.get("num_estimates")
                db_event.updated_at = datetime.utcnow()
                
                session.add(db_event)
            session.commit()
            
            # Refresh profiles and denormalize
            rate_limited = False
            for ticker in distinct_tickers:
                profile = None
                if not rate_limited:
                    try:
                        profile = _refresh_profile(session, ticker)
                    except Exception as e:
                        import requests
                        if isinstance(e, requests.exceptions.HTTPError) and e.response is not None and e.response.status_code == 429:
                            logger.warning(f"Rate limit (429) hit, skipping further API profile fetches: {e}")
                            rate_limited = True
                
                # Fallback to local profile if API was skipped or failed
                if not profile:
                    profile = session.exec(select(CompanyProfile).where(CompanyProfile.ticker == ticker)).first()
                    
                if profile:
                    stmt = select(EarningsCalendarEvent).where(
                        EarningsCalendarEvent.ticker == ticker
                    )
                    ticker_events = session.exec(stmt).all()
                    for te in ticker_events:
                        te.sector = profile.sector
                        te.industry = profile.industry
                        te.market_cap = profile.market_cap
                        session.add(te)
            session.commit()
            
        logger.info(f"Successfully synced earnings calendar: {len(all_events)} events")
        return {"status": "SUCCESS", "events_synced": len(all_events)}
    except Exception as e:
        logger.error(f"Failed to sync earnings calendar: {e}", exc_info=True)
        return {"status": "FAILURE", "error": str(e)}
    finally:
        source.disconnect()


@celery_app.task(bind=True, name="api.tasks.sync_ticker_history_task",
                 autoretry_for=(RateLimitError,), retry_backoff=True,
                 retry_backoff_max=600, max_retries=5)
def sync_ticker_history_task(self, ticker: str):
    """
    Celery task wrapper around repository sync.
    """
    from database.earnings_repo import sync_ticker_history
    from data.earningsapi_source import EarningsAPIDataSource
    from config.settings import load_config
    src = EarningsAPIDataSource(load_config().earningsapi)
    src.connect()
    try:
        with Session(engine) as session:
            return sync_ticker_history(session, ticker.upper(), src)
    finally:
        src.disconnect()

sync_earnings_calendar_task.override_options = {
    'autoretry_for': (RateLimitError,),
    'retry_backoff': True,
    'retry_backoff_max': 600,
    'max_retries': 5
}

sync_ticker_history_task.override_options = {
    'autoretry_for': (RateLimitError,),
    'retry_backoff': True,
    'retry_backoff_max': 600,
    'max_retries': 5
}
