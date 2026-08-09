"""
Integration tests for Sprint 3 fundamental ResearchThesis API router (api/routers/research.py).
"""

import sys
import os
import json
import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlmodel import Session, select, delete

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set ENV=dev for test_ clerk bearer authentication bypass
os.environ["ENV"] = "dev"

from main_api import app
from database.db import engine, init_db
from database.models import User, ResearchThesis
from database.research_repo import save_research_thesis, get_latest_research_thesis
from api.routers.earnings import get_or_create_user

init_db()  # TestClient() alone doesn't trigger the FastAPI lifespan, so tables
           # wouldn't otherwise exist on a fresh DB (e.g. a clean CI checkout).
client = TestClient(app)

HEADERS_USER1 = {"Authorization": "Bearer test_clerk_user_1"}
HEADERS_USER2 = {"Authorization": "Bearer test_clerk_user_2"}


def cleanup_test_ticker(ticker: str):
    with Session(engine) as session:
        theses = session.exec(select(ResearchThesis).where(ResearchThesis.ticker == ticker)).all()
        for t in theses:
            session.delete(t)
        session.commit()


def test_get_thesis_empty_404():
    cleanup_test_ticker("NONEXISTENT_TICKER")
    response = client.get("/research/NONEXISTENT_TICKER", headers=HEADERS_USER1)
    assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
    json_data = response.json()
    assert json_data["detail"] == "No research thesis found for ticker 'NONEXISTENT_TICKER'"
    print(f"\n[PASS] Clean 404 empty case verified: {json_data}")


def test_get_thesis_baseline_and_personalized_scoping():
    ticker = "TEST_NVDA"
    cleanup_test_ticker(ticker)

    dummy_response = {
        "headline_view": "Baseline headline view for NVDA.",
        "confidence_level": 80.0,
        "business_viability_summary": "Strong GPU moat.",
        "competitive_landscape_summary": "Dominant position.",
        "macro_context_summary": "AI buildout.",
        "bull_case": "Blackwell demand.",
        "bear_case": "Supply constraints.",
        "catalysts": ["Earnings"],
        "risks": ["Competition"],
        "evidence_table": [],
        "what_changed_summary": "Initial baseline",
        "disclaimer_shown": True,
    }

    # 1. Save shared baseline thesis (user_id = None)
    with Session(engine) as session:
        user1 = get_or_create_user(session, "test_clerk_user_1")
        user2 = get_or_create_user(session, "test_clerk_user_2")
        user1_id = user1.id
        user2_id = user2.id
        baseline_thesis = save_research_thesis(
            session, ticker, "NVIDIA Corp", dummy_response, user_id=None, source_trigger="manual"
        )
        baseline_id = baseline_thesis.id

    # 2. Test GET /research/{ticker} returns baseline scope for User 1 initially
    resp_b = client.get(f"/research/{ticker}", headers=HEADERS_USER1)
    assert resp_b.status_code == 200
    data_b = resp_b.json()
    assert data_b["scope"] == "baseline"
    assert data_b["id"] == baseline_id

    # 3. Create personalized thesis for User 1
    dummy_personalized = dict(dummy_response)
    dummy_personalized["headline_view"] = "User 1 personalized view for NVDA."
    with Session(engine) as session:
        pers_thesis = save_research_thesis(
            session, ticker, "NVIDIA Corp", dummy_personalized, user_id=user1_id, user_notes="Custom notes", source_trigger="user_personalized"
        )
        pers_id = pers_thesis.id

    # 4. GET /research/{ticker} for User 1 returns personalized thesis
    resp_p = client.get(f"/research/{ticker}", headers=HEADERS_USER1)
    assert resp_p.status_code == 200
    data_p = resp_p.json()
    assert data_p["scope"] == "personalized"
    assert data_p["id"] == pers_id
    assert data_p["user_id"] == user1_id
    assert data_p["headline_view"] == "User 1 personalized view for NVDA."

    # 5. GET /research/{ticker} for User 2 (who has no personalized thesis) still returns baseline thesis
    resp_u2 = client.get(f"/research/{ticker}", headers=HEADERS_USER2)
    assert resp_u2.status_code == 200
    data_u2 = resp_u2.json()
    assert data_u2["scope"] == "baseline"
    assert data_u2["id"] == baseline_id

    # 6. GET /research/{ticker}/baseline explicitly returns baseline even for User 1
    resp_base_explicit = client.get(f"/research/{ticker}/baseline", headers=HEADERS_USER1)
    assert resp_base_explicit.status_code == 200
    data_be = resp_base_explicit.json()
    assert data_be["scope"] == "baseline"
    assert data_be["id"] == baseline_id

    print(f"\n[PASS] Thesis baseline, personalized, and explicit baseline scoping verified successfully!")


def test_history_endpoint_and_privacy():
    ticker = "TEST_HIST"
    cleanup_test_ticker(ticker)

    dummy = {"headline_view": "History test", "confidence_level": 70.0}

    with Session(engine) as session:
        user1 = get_or_create_user(session, "test_clerk_user_1")
        user2 = get_or_create_user(session, "test_clerk_user_2")
        t_base = save_research_thesis(session, ticker, "Test Corp", dummy, user_id=None)
        t_u1 = save_research_thesis(session, ticker, "Test Corp", dummy, user_id=user1.id)
        t_u2 = save_research_thesis(session, ticker, "Test Corp", dummy, user_id=user2.id)
        u2_thesis_id = t_u2.id

    # User 1 history should contain 2 items: user1's thesis + baseline (excludes user2's thesis)
    resp = client.get(f"/research/{ticker}/history", headers=HEADERS_USER1)
    assert resp.status_code == 200
    hist_data = resp.json()
    assert hist_data["count"] == 2
    scopes = [item["scope"] for item in hist_data["history"]]
    assert "personalized" in scopes
    assert "baseline" in scopes
    ids = [item["id"] for item in hist_data["history"]]
    assert u2_thesis_id not in ids, "User 2 private thesis MUST NOT be returned in User 1 history"

    print(f"\n[PASS] History scoping and privacy isolation verified successfully!")


def test_post_trigger_contract(monkeypatch):
    ticker = "TEST_POST"
    cleanup_test_ticker(ticker)

    class DummyTask:
        id = "mock-task-id-12345"

    monkeypatch.setattr("api.routers.research.generate_research_thesis_task.delay", lambda *args, **kwargs: DummyTask())

    # Test POST /research/{ticker}
    resp = client.post(f"/research/{ticker}", json={"user_notes": "Deep research notes"}, headers=HEADERS_USER1)
    assert resp.status_code == 200
    post_json = resp.json()

    assert "task_id" in post_json
    assert post_json["status"] == "PENDING"
    assert "Analysis for TEST_POST started in background" in post_json["message"]

    print(f"\n[PASS] POST /research/{ticker} contract shape verified: {post_json}")


if __name__ == "__main__":
    pytest.main(["-v", __file__])
