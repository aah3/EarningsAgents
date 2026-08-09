"""
FastAPI router for fundamental ResearchThesis endpoints.
Exposes GET /research/{ticker}, GET /research/{ticker}/baseline,
GET /research/{ticker}/history, and POST /research/{ticker}.
"""

import sys
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from database.db import get_session
from database.models import User, ResearchThesis
from database.research_repo import get_latest_research_thesis
from api.dependencies.auth import get_current_user
from api.routers.earnings import get_or_create_user
from api.tasks import generate_research_thesis_task

router = APIRouter(
    prefix="/research",
    tags=["research"],
)


class TriggerResearchRequest(BaseModel):
    user_notes: Optional[str] = None
    user_analysis: Optional[str] = None


def serialize_thesis(thesis: ResearchThesis, scope: str) -> Dict[str, Any]:
    """Serialize a ResearchThesis record with an explicit 'scope' label."""
    gen_at = thesis.generated_at
    if isinstance(gen_at, datetime):
        gen_at_str = gen_at.isoformat()
    else:
        gen_at_str = str(gen_at) if gen_at else None

    return {
        "id": thesis.id,
        "ticker": thesis.ticker,
        "company_name": thesis.company_name,
        "user_id": thesis.user_id,
        "user_notes": thesis.user_notes,
        "generated_at": gen_at_str,
        "source_trigger": thesis.source_trigger,
        "headline_view": thesis.headline_view or "",
        "confidence_level": thesis.confidence_level,
        "business_viability_summary": thesis.business_viability_summary or "",
        "competitive_landscape_summary": thesis.competitive_landscape_summary or "",
        "macro_context_summary": thesis.macro_context_summary or "",
        "bull_case": thesis.bull_case or "",
        "bear_case": thesis.bear_case or "",
        "catalysts": thesis.catalysts or [],
        "risks": thesis.risks or [],
        "evidence_table": thesis.evidence_table or [],
        "what_changed_summary": thesis.what_changed_summary,
        "disclaimer_shown": thesis.disclaimer_shown,
        "scope": scope,
    }


@router.get("/{ticker}")
async def get_research_thesis(
    ticker: str,
    clerk_id: str = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Get the calling user's personalized thesis if available, otherwise the shared baseline.
    Returns 404 detail if no thesis exists for the ticker.
    """
    ticker_upper = ticker.upper()
    user = get_or_create_user(session, clerk_id)

    # 1. Check calling user's personalized thesis
    user_thesis = get_latest_research_thesis(session, ticker_upper, user_id=user.id)
    if user_thesis:
        return serialize_thesis(user_thesis, scope="personalized")

    # 2. Fall back to shared baseline thesis
    baseline_thesis = get_latest_research_thesis(session, ticker_upper, user_id=None)
    if baseline_thesis:
        return serialize_thesis(baseline_thesis, scope="baseline")

    # 3. Return clean 404 error if neither exists
    raise HTTPException(
        status_code=404,
        detail=f"No research thesis found for ticker '{ticker_upper}'",
    )


@router.get("/{ticker}/baseline")
async def get_baseline_research_thesis(
    ticker: str,
    clerk_id: str = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Explicitly get the shared baseline thesis for a ticker regardless of user personalization.
    Returns 404 detail if no baseline thesis exists.
    """
    ticker_upper = ticker.upper()
    baseline_thesis = get_latest_research_thesis(session, ticker_upper, user_id=None)
    if baseline_thesis:
        return serialize_thesis(baseline_thesis, scope="baseline")

    raise HTTPException(
        status_code=404,
        detail=f"No baseline research thesis found for ticker '{ticker_upper}'",
    )


@router.get("/{ticker}/history")
async def get_research_thesis_history(
    ticker: str,
    clerk_id: str = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Get all theses for a ticker scoped to the calling user's personalized rows plus baseline rows,
    ordered by generated_at DESC. Excludes other users' personalized rows.
    """
    ticker_upper = ticker.upper()
    user = get_or_create_user(session, clerk_id)

    stmt = (
        select(ResearchThesis)
        .where(ResearchThesis.ticker == ticker_upper)
        .where(
            (ResearchThesis.user_id == user.id) | (ResearchThesis.user_id.is_(None))
        )
        .order_by(ResearchThesis.generated_at.desc())
    )
    theses = session.exec(stmt).all()

    history_items = [
        serialize_thesis(
            t,
            scope="personalized" if t.user_id == user.id else "baseline",
        )
        for t in theses
    ]

    return {
        "ticker": ticker_upper,
        "count": len(history_items),
        "history": history_items,
    }


@router.post("/{ticker}")
async def trigger_research_thesis(
    ticker: str,
    body: Optional[TriggerResearchRequest] = None,
    clerk_id: str = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Manual trigger for research thesis generation.
    Accepts optional user_notes (or user_analysis).
    If notes are provided, enqueues personalized generation for calling user.
    If omitted, enqueues/refreshes shared baseline thesis.
    Returns task_id in the exact task-status contract shape as /predict.
    """
    ticker_upper = ticker.upper()
    user = get_or_create_user(session, clerk_id)

    notes = None
    if body:
        notes = body.user_notes or body.user_analysis

    if notes and notes.strip():
        target_user_id = user.id
        target_notes = notes.strip()
        msg_type = f"personalized research thesis for user {user.id}"
    else:
        target_user_id = None
        target_notes = None
        msg_type = "shared baseline research thesis"

    task = generate_research_thesis_task.delay(
        ticker_upper,
        user_id=target_user_id,
        user_notes=target_notes,
    )

    return {
        "task_id": task.id,
        "status": "PENDING",
        "message": f"Analysis for {ticker_upper} started in background",
    }
