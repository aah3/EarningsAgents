import statistics
import logging
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from sqlmodel import Session, select
from database.models import CompanyProfile, EarningsHistory

logger = logging.getLogger(__name__)


def compute_reaction_summary(rows: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Summary of post-earnings 1-day reactions. `rows` are EarningsHistory dicts."""
    moves = [r["reaction_1d_pct"] for r in rows if r.get("reaction_1d_pct") is not None]
    if not moves:
        return None
    
    beats = [
        r["reaction_1d_pct"]
        for r in rows
        if r.get("reaction_1d_pct") is not None and r.get("eps_beat") is True
    ]
    misses = [
        r["reaction_1d_pct"]
        for r in rows
        if r.get("reaction_1d_pct") is not None and r.get("eps_beat") is False
    ]
    
    n = len(moves)
    depth = "high" if n >= 8 else "moderate" if n >= 4 else "low"
    
    return {
        "n": n,
        "sample_depth": depth,
        "avg_1d_pct": round(statistics.fmean(moves), 2),
        "median_1d_pct": round(statistics.median(moves), 2),
        "min_1d_pct": round(min(moves), 2),
        "max_1d_pct": round(max(moves), 2),
        "std_1d_pct": round(statistics.pstdev(moves), 2) if len(moves) > 1 else 0.0,
        "avg_abs_1d_pct": round(statistics.fmean([abs(m) for m in moves]), 2),
        "beat_move_avg": round(statistics.fmean(beats), 2) if beats else None,
        "miss_move_avg": round(statistics.fmean(misses), 2) if misses else None,
    }


def get_reaction_summary_and_history(session: Session, ticker: str, quarters: int = 8):
    """Return (summary_dict|None, [row_dict, ...]) most-recent-first."""
    stmt = (
        select(EarningsHistory)
        .where(EarningsHistory.ticker == ticker.upper())
        .order_by(EarningsHistory.report_date.desc())
        .limit(quarters)
    )
    records = session.exec(stmt).all()
    rows = [r.model_dump() for r in records]
    return compute_reaction_summary(rows), rows


def _refresh_profile(session: Session, ticker: str) -> Optional[CompanyProfile]:
    """
    Refreshes company profile in the database, cached for 7 days.
    """
    ticker_upper = ticker.upper()
    profile = session.exec(select(CompanyProfile).where(CompanyProfile.ticker == ticker_upper)).first()
    now = datetime.utcnow()
    
    if not profile or (now - profile.updated_at).days >= 7:
        try:
            from data.earningsapi_source import EarningsAPIDataSource
            from config.settings import load_config
            config = load_config()
            
            source = EarningsAPIDataSource(config.earningsapi)
            source.connect()
            try:
                profile_data = source.get_profile(ticker_upper)
                if profile_data:
                    if not profile:
                        profile = CompanyProfile(ticker=ticker_upper)
                    profile.company_name = profile_data.get("company_name")
                    profile.sector = profile_data.get("sector")
                    profile.industry = profile_data.get("industry")
                    profile.market_cap = profile_data.get("market_cap")
                    profile.exchange = profile_data.get("exchange")
                    profile.country = profile_data.get("country")
                    profile.cik = profile_data.get("cik")
                    profile.outstanding_shares = profile_data.get("outstanding_shares")
                    profile.updated_at = now
                    
                    session.add(profile)
                    session.commit()
                    session.refresh(profile)
            finally:
                source.disconnect()
        except Exception as e:
            logger.error(f"Failed to refresh profile for {ticker_upper}: {e}", exc_info=True)
            from data.earningsapi_source import RateLimitError
            if isinstance(e, RateLimitError):
                raise e
            
    return profile


def sync_ticker_history(session: Session, ticker: str, source) -> int:
    """
    Pure sync: pull /v1/earnings + /v1/earnings-reactions from `source`, merge by
    report_date, upsert into EarningsHistory on (ticker, report_date). Returns rows upserted.
    Idempotent: SELECT by (ticker, report_date) then UPDATE, else INSERT.
    """
    ticker_upper = ticker.upper()
    logger.info(f"Syncing history for {ticker_upper}")
    
    # 1. Try to refresh profile first
    try:
        _refresh_profile(session, ticker_upper)
    except Exception as e:
        logger.warning(f"Failed to refresh profile during history sync for {ticker_upper}: {e}")
        
    # 2. Fetch history and reactions from the API
    earnings = source.get_company_earnings(ticker_upper)
    reactions = source.get_earnings_reactions(ticker_upper)
    
    reactions_by_date = {r["date"]: r for r in reactions}
    
    from data.earningsapi_source import summarize_reaction
    
    upserted_count = 0
    for row in earnings:
        date_str = row["date"]
        actual_eps = row.get("eps")
        actual_rev = row.get("revenue")
        
        # Skip upcoming rows (null actuals)
        if actual_eps is None and actual_rev is None:
            continue
        
        report_date = date.fromisoformat(date_str)
        
        react_data = reactions_by_date.get(date_str, {})
        eps_data = react_data.get("eps") or {}
        rev_data = react_data.get("revenue") or {}
        reactions_list = react_data.get("reactions") or []
        summary = summarize_reaction(reactions_list)
        
        time_raw = row.get("time")
        report_time = "UNKNOWN"
        if time_raw == "time-after-hours":
            report_time = "AMC"
        elif time_raw == "time-before-market":
            report_time = "BMO"
            
        stmt = select(EarningsHistory).where(
            EarningsHistory.ticker == ticker_upper,
            EarningsHistory.report_date == report_date
        )
        db_hist = session.exec(stmt).first()
        if not db_hist:
            db_hist = EarningsHistory(
                ticker=ticker_upper,
                report_date=report_date
            )
            
        db_hist.report_time = report_time
        db_hist.eps_actual = actual_eps
        db_hist.eps_estimate = row.get("epsEstimate")
        db_hist.eps_surprise_pct = eps_data.get("surprisePercent")
        db_hist.eps_yoy = eps_data.get("yoy")
        db_hist.eps_beat = eps_data.get("beat")
        
        db_hist.revenue_actual = actual_rev
        db_hist.revenue_estimate = row.get("revenueEstimate")
        db_hist.revenue_surprise_pct = rev_data.get("surprisePercent")
        db_hist.revenue_yoy = rev_data.get("yoy")
        db_hist.revenue_beat = rev_data.get("beat")
        
        db_hist.reaction_1d_pct = summary.get("reaction_1d_pct")
        db_hist.reaction_5d_pct = summary.get("reaction_5d_pct")
        db_hist.reaction_volume = summary.get("reaction_volume")
        db_hist.updated_at = datetime.utcnow()
        
        session.add(db_hist)
        upserted_count += 1
        
    session.commit()
    logger.info(f"Synced {upserted_count} history rows for {ticker_upper}")
    return upserted_count
