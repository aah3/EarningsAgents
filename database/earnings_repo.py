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


def summarize_description(description: str, config) -> str:
    """Summarizes company description in 2-3 sentences using LLMClient with simple fallback."""
    if not description:
        return ""
    try:
        from agents.llm_client import LLMClient
        llm = LLMClient(
            api_key=config.agent.api_key,
            provider=config.agent.provider,
            model=config.agent.model_name
        )
        sys_prompt = "You are a financial analyst. Summarize the following company description in 2-3 concise sentences, focusing on the core business, products/services, and target market. Do not add any introductory or concluding text."
        summary = llm.generate(sys_prompt, description)
        if summary and summary.strip():
            return summary.strip()
    except Exception as e:
        logger.warning(f"Failed to summarize description using LLM: {e}. Falling back to original summary sentences.")
    
    # Fallback to first 3 sentences
    sentences = [s.strip() for s in description.replace("\n", " ").split(". ") if s.strip()]
    if len(sentences) > 3:
        return ". ".join(sentences[:3]) + "."
    return description


def _refresh_profile(session: Session, ticker: str) -> Optional[CompanyProfile]:
    """
    Refreshes company profile in the database, cached for 7 days.
    """
    ticker_upper = ticker.upper()
    profile = session.exec(select(CompanyProfile).where(CompanyProfile.ticker == ticker_upper)).first()
    now = datetime.utcnow()
    
    if not profile or (now - profile.updated_at).days >= 7 or not getattr(profile, "company_description", None):
        try:
            from data.earningsapi_source import EarningsAPIDataSource
            from config.settings import load_config
            config = load_config()
            
            profile_data = None
            source = EarningsAPIDataSource(config.earningsapi)
            source.connect()
            try:
                profile_data = source.get_profile(ticker_upper)
            except Exception as e:
                logger.warning(f"EarningsAPI profile fetch failed: {e}")
            finally:
                source.disconnect()
                
            # If we don't have profile_data from source, or to get longBusinessSummary, let's call yfinance:
            yf_info = {}
            try:
                import yfinance as yf
                sid = yf.Ticker(ticker_upper)
                yf_info = sid.info or {}
            except Exception as e:
                logger.error(f"Failed to fetch yfinance data for {ticker_upper}: {e}")

            if profile_data or yf_info:
                if not profile:
                    profile = CompanyProfile(ticker=ticker_upper)
                
                # Use EarningsAPI data as primary, yfinance as fallback
                profile.company_name = (profile_data or {}).get("company_name") or yf_info.get("longName") or yf_info.get("shortName") or profile.company_name or ticker_upper
                profile.sector = (profile_data or {}).get("sector") or yf_info.get("sector") or profile.sector or "Unknown"
                profile.industry = (profile_data or {}).get("industry") or yf_info.get("industry") or profile.industry or "Unknown"
                
                # Assign other fields
                if (profile_data or {}).get("market_cap"):
                    profile.market_cap = profile_data.get("market_cap")
                elif yf_info.get("marketCap"):
                    profile.market_cap = float(yf_info.get("marketCap"))
                    
                profile.exchange = (profile_data or {}).get("exchange") or yf_info.get("exchange") or profile.exchange
                profile.country = (profile_data or {}).get("country") or yf_info.get("country") or profile.country
                
                # Fields specific to profile_data
                if profile_data:
                    profile.cik = profile_data.get("cik") or profile.cik
                    profile.outstanding_shares = profile_data.get("outstanding_shares") or profile.outstanding_shares
                
                # Fetch and summarize description from yfinance info
                desc = yf_info.get("longBusinessSummary")
                if desc:
                    # Summarize description
                    summary = summarize_description(desc, config)
                    profile.company_description = summary
                
                profile.updated_at = now
                session.add(profile)
                session.commit()
                session.refresh(profile)
        except Exception as e:
            logger.error(f"Failed to refresh profile for {ticker_upper}: {e}", exc_info=True)
            from data.earningsapi_source import RateLimitError
            if isinstance(e, RateLimitError):
                raise e
            
    return profile


def compute_yoy(current_actual: Optional[float], year_ago_actual: Optional[float], min_base: float) -> Optional[float]:
    """Compute year-over-year growth percentage, capped at ±1000%."""
    from data.metrics import safe_surprise_pct
    return safe_surprise_pct(current_actual, year_ago_actual, cap=1000.0, min_base=min_base)


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
    from data.metrics import safe_surprise_pct
    
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
        
        provenance = {}
        
        eps_surp = eps_data.get("surprisePercent")
        if eps_surp is not None:
            db_hist.eps_surprise_pct = eps_surp
            provenance["eps_surprise_pct"] = "reported"
        else:
            local_eps_surp = safe_surprise_pct(actual_eps, row.get("epsEstimate"), min_base=0.05)
            if local_eps_surp is not None:
                db_hist.eps_surprise_pct = local_eps_surp
                provenance["eps_surprise_pct"] = "computed"
            else:
                db_hist.eps_surprise_pct = None
                
        eps_yoy_val = eps_data.get("yoy")
        if eps_yoy_val is not None:
            db_hist.eps_yoy = eps_yoy_val
            provenance["eps_yoy"] = "reported"
        else:
            db_hist.eps_yoy = None
            
        db_hist.eps_beat = eps_data.get("beat")
        
        db_hist.revenue_actual = actual_rev
        db_hist.revenue_estimate = row.get("revenueEstimate")
        
        rev_surp = rev_data.get("surprisePercent")
        if rev_surp is not None:
            db_hist.revenue_surprise_pct = rev_surp
            provenance["revenue_surprise_pct"] = "reported"
        else:
            local_rev_surp = safe_surprise_pct(actual_rev, row.get("revenueEstimate"), min_base=1e6)
            if local_rev_surp is not None:
                db_hist.revenue_surprise_pct = local_rev_surp
                provenance["revenue_surprise_pct"] = "computed"
            else:
                db_hist.revenue_surprise_pct = None
                
        rev_yoy_val = rev_data.get("yoy")
        if rev_yoy_val is not None:
            db_hist.revenue_yoy = rev_yoy_val
            provenance["revenue_yoy"] = "reported"
        else:
            db_hist.revenue_yoy = None
            
        db_hist.revenue_beat = rev_data.get("beat")
        db_hist.provenance = provenance
        
        db_hist.reaction_1d_pct = summary.get("reaction_1d_pct")
        db_hist.reaction_5d_pct = summary.get("reaction_5d_pct")
        db_hist.reaction_volume = summary.get("reaction_volume")
        db_hist.updated_at = datetime.utcnow()
        
        session.add(db_hist)
        upserted_count += 1
        
    if upserted_count > 0:
        session.flush()
        all_rows = session.exec(
            select(EarningsHistory)
            .where(EarningsHistory.ticker == ticker_upper)
            .order_by(EarningsHistory.report_date.asc())
        ).all()
        
        for r in all_rows:
            prov = dict(r.provenance or {})
            if r.eps_yoy is None or r.revenue_yoy is None:
                prev_row = None
                min_diff = 9999
                for p in all_rows:
                    diff_days = (r.report_date - p.report_date).days
                    if 330 <= diff_days <= 400:
                        if abs(diff_days - 365) < min_diff:
                            min_diff = abs(diff_days - 365)
                            prev_row = p
                
                if prev_row:
                    if r.eps_yoy is None and r.eps_actual is not None and prev_row.eps_actual is not None:
                        local_yoy = compute_yoy(r.eps_actual, prev_row.eps_actual, min_base=0.05)
                        if local_yoy is not None:
                            r.eps_yoy = local_yoy
                            prov["eps_yoy"] = "computed"
                    if r.revenue_yoy is None and r.revenue_actual is not None and prev_row.revenue_actual is not None:
                        local_yoy = compute_yoy(r.revenue_actual, prev_row.revenue_actual, min_base=1e6)
                        if local_yoy is not None:
                            r.revenue_yoy = local_yoy
                            prov["revenue_yoy"] = "computed"
            r.provenance = prov
            session.add(r)
                    
    session.commit()
    logger.info(f"Synced {upserted_count} history rows for {ticker_upper}")
    return upserted_count
