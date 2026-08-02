# EarningsAgents Project Guidelines

## Earnings Outcome & EPS Verification Invariants
- Never allow actual EPS to default to `0.0` or `null` without logging an explicit warning or verifying against external financial data providers.
- When writing back outcome evaluations to database records (`scoring_service.py`, `update_predictions.py`), validate that `actual_eps` and `actual_price_move_pct` reflect actual reported metrics before saving.

## Web Dashboard & API Caching
- Always sanitize and normalize ticker symbols before rendering UI components (e.g. upper-case, strip duplicate prefixes).
- Cache redundant ticker metadata and prediction queries client-side to prevent unnecessary refetching.
