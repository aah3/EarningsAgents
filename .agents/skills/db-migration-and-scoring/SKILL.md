---
name: db-migration-and-scoring
description: Workflow for updating database schemas, generating Alembic migrations, managing encrypted fields, and enforcing EPS outcome evaluation invariants.
---

# Database Migration & Outcome Scoring Workflow

Follow this procedure when modifying database models, applying migrations, or updating outcome scoring logic.

## 1. Schema Modifications (`database/models.py`)
1. Update or add SQLModel models in [`database/models.py`](file:///c:/Users/alfredo/Project/EarningsAgents/database/models.py).
2. **Security Invariant**: Any user-configured LLM provider API keys MUST be Fernet-encrypted via [`database/crypto.py`](file:///c:/Users/alfredo/Project/EarningsAgents/database/crypto.py) before `session.add(...)`, and decrypted only upon read. Never store or return plaintext API keys.

## 2. Alembic Migrations
1. Generate migration script:
   ```bash
   python -m alembic revision --autogenerate -m "describe_changes_here"
   ```
2. Inspect the generated migration script in `alembic/versions/` for accuracy.
3. Apply migration to local DB:
   ```bash
   python -m alembic upgrade head
   ```

## 3. Scoring & Outcome Verification Invariants
When modifying [`database/scoring_service.py`](file:///c:/Users/alfredo/Project/EarningsAgents/database/scoring_service.py) or `update_predictions.py`:
- **EPS Verification Invariant**: Never allow `actual_eps` to default to `0.0` or `null` without logging an explicit warning or verifying against external financial data providers.
- Validate that `actual_eps` and `actual_price_move_pct` reflect real reported earnings metrics before saving records.
- Compute Brier score: `(confidence/100 - correct)^2`.

## 4. Verification
1. Run database & scoring unit tests:
   ```bash
   python -m pytest tests/ -v
   ```
2. Manually verify scoring runner:
   ```bash
   make score-now
   ```
