"""
Backfill `Prediction.fiscal_quarter` / `fiscal_year` for rows created before the
columns existed (migration b7c41d29e5aa).

Resolution order per row is handled by database.fiscal_period.resolve_fiscal_period:
a matching EarningsHistory row when one exists, otherwise inference from
report_date.

Usage:
    python scripts/backfill_fiscal_period.py --dry-run   # preview only
    python scripts/backfill_fiscal_period.py             # write
    python scripts/backfill_fiscal_period.py --force     # also recompute rows
                                                         # that already have a value
"""

import os
import sys
import argparse

from sqlmodel import Session, select

# Ensure project root is in python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import engine
from database.models import Prediction
from database.fiscal_period import resolve_fiscal_period, format_fiscal_period


def main():
    parser = argparse.ArgumentParser(description="Backfill fiscal period on predictions")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change without writing")
    parser.add_argument("--force", action="store_true", help="Recompute rows that already have a fiscal period")
    args = parser.parse_args()

    updated = 0
    skipped = 0
    unresolved = 0

    with Session(engine) as session:
        predictions = session.exec(select(Prediction).order_by(Prediction.report_date)).all()
        print(f"Scanning {len(predictions)} prediction(s)...\n")

        for p in predictions:
            already_set = bool(p.fiscal_quarter and p.fiscal_year)
            if already_set and not args.force:
                skipped += 1
                continue

            quarter, year = resolve_fiscal_period(session, p.ticker, p.report_date)
            if not quarter or not year:
                unresolved += 1
                print(f"  [SKIP] {p.ticker} (id={p.id}) report_date={p.report_date} -> unresolved")
                continue

            before = format_fiscal_period(p.fiscal_quarter, p.fiscal_year) or "(none)"
            after = format_fiscal_period(quarter, year)
            if before == after:
                skipped += 1
                continue

            print(f"  {p.ticker:<8} (id={p.id})  report_date={str(p.report_date)[:10]}  {before} -> {after}")
            if not args.dry_run:
                p.fiscal_quarter = quarter
                p.fiscal_year = year
                session.add(p)
            updated += 1

        if not args.dry_run:
            session.commit()

    verb = "Would update" if args.dry_run else "Updated"
    print(f"\n{verb} {updated} row(s); {skipped} unchanged; {unresolved} unresolved.")


if __name__ == "__main__":
    main()
