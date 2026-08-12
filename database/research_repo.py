"""
Repository for ResearchThesis persistence and retrieval.
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlmodel import Session, select

from database.models import ResearchThesis

logger = logging.getLogger(__name__)


def save_research_thesis(
    session: Session,
    ticker: str,
    company_name: str,
    response_data: Any,  # ResearchThesisResponse dataclass or dict
    user_id: Optional[int] = None,
    user_notes: Optional[str] = None,
    source_trigger: str = "manual",
) -> ResearchThesis:
    """
    Save a ResearchThesis record into the database (append-only).
    
    Args:
        session: SQLModel DB Session
        ticker: Stock ticker symbol (e.g. "NVDA")
        company_name: Name of the company
        response_data: ResearchThesisResponse dataclass or dict
        user_id: Foreign key to user table (None for shared baseline thesis)
        user_notes: Analyst notes provided for personalized thesis
        source_trigger: Trigger source ("auto_on_predict", "manual", "user_personalized")
        
    Returns:
        Persisted ResearchThesis instance
    """
    ticker_upper = ticker.upper()

    # Normalize response fields if response_data is dataclass or dict
    if hasattr(response_data, "__dataclass_fields__") or hasattr(response_data, "headline_view"):
        headline_view = getattr(response_data, "headline_view", "")
        confidence_level = float(getattr(response_data, "confidence_level", 50.0))
        business_viability_summary = getattr(response_data, "business_viability_summary", "")
        competitive_landscape_summary = getattr(response_data, "competitive_landscape_summary", "")
        macro_context_summary = getattr(response_data, "macro_context_summary", "")
        bull_case = getattr(response_data, "bull_case", "")
        bear_case = getattr(response_data, "bear_case", "")
        catalysts = getattr(response_data, "catalysts", []) or []
        risks = getattr(response_data, "risks", []) or []
        evidence_table = getattr(response_data, "evidence_table", []) or []
        what_changed_summary = getattr(response_data, "what_changed_summary", None)
        disclaimer_shown = bool(getattr(response_data, "disclaimer_shown", True))
    elif isinstance(response_data, dict):
        headline_view = response_data.get("headline_view", "")
        confidence_level = float(response_data.get("confidence_level", 50.0))
        business_viability_summary = response_data.get("business_viability_summary", "")
        competitive_landscape_summary = response_data.get("competitive_landscape_summary", "")
        macro_context_summary = response_data.get("macro_context_summary", "")
        bull_case = response_data.get("bull_case", "")
        bear_case = response_data.get("bear_case", "")
        catalysts = response_data.get("catalysts", []) or []
        risks = response_data.get("risks", []) or []
        evidence_table = response_data.get("evidence_table", []) or []
        what_changed_summary = response_data.get("what_changed_summary")
        disclaimer_shown = bool(response_data.get("disclaimer_shown", True))
    else:
        raise ValueError(f"Unsupported response_data type: {type(response_data)}")

    trigger = source_trigger
    if user_id is not None or user_notes:
        trigger = "user_personalized"

    thesis = ResearchThesis(
        ticker=ticker_upper,
        company_name=company_name,
        user_id=user_id,
        user_notes=user_notes,
        generated_at=datetime.utcnow(),
        source_trigger=trigger,
        headline_view=headline_view,
        confidence_level=confidence_level,
        business_viability_summary=business_viability_summary,
        competitive_landscape_summary=competitive_landscape_summary,
        macro_context_summary=macro_context_summary,
        bull_case=bull_case,
        bear_case=bear_case,
        catalysts=catalysts,
        risks=risks,
        evidence_table=evidence_table,
        what_changed_summary=what_changed_summary,
        disclaimer_shown=disclaimer_shown,
    )

    session.add(thesis)
    session.commit()
    session.refresh(thesis)
    logger.info(f"Saved ResearchThesis for {ticker_upper} (id={thesis.id}, user_id={user_id})")
    return thesis


def get_latest_research_thesis(
    session: Session,
    ticker: str,
    user_id: Optional[int] = None,
) -> Optional[ResearchThesis]:
    """
    Retrieve the most recent ResearchThesis for a ticker.
    
    If user_id is None, retrieves the latest baseline thesis (user_id IS NULL).
    If user_id is provided, retrieves the latest personalized thesis for that user.
    """
    ticker_upper = ticker.upper()
    if user_id is None:
        stmt = (
            select(ResearchThesis)
            .where(ResearchThesis.ticker == ticker_upper)
            .where(ResearchThesis.user_id.is_(None))
            .order_by(ResearchThesis.generated_at.desc())
        )
    else:
        stmt = (
            select(ResearchThesis)
            .where(ResearchThesis.ticker == ticker_upper)
            .where(ResearchThesis.user_id == user_id)
            .order_by(ResearchThesis.generated_at.desc())
        )
    return session.exec(stmt).first()


def format_research_summary(thesis: Optional[ResearchThesis]) -> str:
    """Format headline_view and business_viability_summary into a concise research context block."""
    if not thesis:
        return ""
    headline = thesis.headline_view or ""
    viability = thesis.business_viability_summary or ""
    return f"Headline View: {headline}\nBusiness Viability: {viability}"


def resolve_thesis_for_prediction(
    session: Session,
    ticker: str,
    user_id: Optional[int] = None,
    user_notes: Optional[str] = None,
    staleness_days: int = 21,
) -> tuple[Optional[str], bool]:
    """
    Resolve which ResearchThesis summary to feed into ConsensusAgent,
    and determine whether a baseline thesis generation background task needs to be enqueued.
    
    Returns:
        (research_context_summary_string_or_None, needs_baseline_enqueue_boolean)
    """
    ticker_upper = ticker.upper()
    needs_baseline_enqueue = False
    selected_thesis: Optional[ResearchThesis] = None

    # 1. Check user personalized thesis if user_id is provided
    if user_id is not None:
        user_thesis = get_latest_research_thesis(session, ticker_upper, user_id=user_id)
        if user_notes:
            if user_thesis and user_thesis.user_notes == user_notes:
                selected_thesis = user_thesis
        else:
            if user_thesis:
                selected_thesis = user_thesis

    # 2. Fall back to shared baseline thesis if no personalized thesis selected
    if selected_thesis is None:
        baseline_thesis = get_latest_research_thesis(session, ticker_upper, user_id=None)
        if baseline_thesis is None:
            needs_baseline_enqueue = True
            selected_thesis = None
        else:
            age_days = (datetime.utcnow() - baseline_thesis.generated_at).days
            if age_days >= staleness_days:
                needs_baseline_enqueue = True
                selected_thesis = baseline_thesis
            else:
                needs_baseline_enqueue = False
                selected_thesis = baseline_thesis

    research_context = format_research_summary(selected_thesis) if selected_thesis else None
    return research_context, needs_baseline_enqueue


def resolve_or_generate_research_context(
    session: Session,
    ticker: str,
    agent_config: Any,
    user_id: Optional[int] = None,
    user_notes: Optional[str] = None,
    staleness_days: int = 21,
) -> Optional[str]:
    """
    Like resolve_thesis_for_prediction, but when the baseline thesis is missing or
    stale, generates and saves a fresh one synchronously (in-process) instead of
    just flagging it for async enqueue. Used by callers that want every prediction
    to have research context available immediately (batch runs, synchronous API
    triggers) rather than only from the next run onward.

    Returns the research_context summary string, or None if a thesis could not be
    resolved or generated.
    """
    research_context, needs_baseline_enqueue = resolve_thesis_for_prediction(
        session, ticker, user_id=user_id, user_notes=user_notes, staleness_days=staleness_days
    )
    if not needs_baseline_enqueue:
        return research_context

    ticker_upper = ticker.upper()
    try:
        from agents.huggingface_agents import generate_thesis
        previous = get_latest_research_thesis(session, ticker_upper, user_id=None)
        response = generate_thesis(ticker_upper, previous_thesis=previous, config=agent_config)
        thesis = save_research_thesis(
            session, ticker_upper, ticker_upper, response,
            user_id=None, user_notes=None, source_trigger="auto_on_predict",
        )
        logger.info(f"Synchronously generated baseline ResearchThesis for {ticker_upper} (id={thesis.id})")
        return format_research_summary(thesis)
    except Exception as e:
        logger.warning(f"Failed to synchronously generate baseline research thesis for {ticker_upper}: {e}")
        return research_context

