import os
import sys
import argparse
from datetime import date, datetime
from sqlmodel import Session, select

# Ensure project root is in python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import engine
from database.models import User, Prediction
from database.scoring_service import PredictionScorer
from data.yahoo_finance import YahooFinanceDataSource, DataSourceConfig

def score_and_save(scorer, session, prediction):
    print(f"\nScoring {prediction.ticker} (ID {prediction.id or 'NEW'})...")
    result = scorer.score_prediction(prediction)
    if result.get("scored"):
        prediction.actual_direction = result["actual_direction"]
        prediction.actual_eps = result["actual_eps"]
        prediction.actual_price_move_pct = result["actual_price_move_pct"]
        prediction.accuracy_score = result["accuracy_score"]
        prediction.scored_at = result["scored_at"]
        
        session.add(prediction)
        session.commit()
        session.refresh(prediction)
        print(f"  [SUCCESS] Scored/Updated {prediction.ticker} successfully:")
        print(f"    Actual Direction: {prediction.actual_direction}")
        print(f"    Actual EPS:       {prediction.actual_eps}")
        if prediction.actual_price_move_pct is not None:
            print(f"    Price Move %:     {prediction.actual_price_move_pct:.6f} ({prediction.actual_price_move_pct*100:.2f}%)")
        else:
            print(f"    Price Move %:     Pending (Next day close not yet available)")
        print(f"    Brier Score:      {prediction.accuracy_score:.6f}")
        print(f"    Scored At:        {prediction.scored_at}")
        return True
    else:
        print(f"  [SKIPPED/ERROR] Failed to score {prediction.ticker}: {result.get('reason')}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Update and score earnings predictions in the Supabase database.")
    parser.add_argument("-t", "--ticker", type=str, help="Specific ticker symbol to update (e.g. LNN)")
    parser.add_argument("-a", "--all", action="store_true", help="Score all unscored predictions in the database (default behavior if no ticker given)")
    parser.add_argument("-c", "--create", action="store_true", help="Create a prediction record if none exists for the ticker")
    parser.add_argument("-d", "--direction", type=str, choices=["BEAT", "MISS", "MEET"], help="Predicted direction (required if using --create)")
    parser.add_argument("-p", "--confidence", type=float, help="Predicted confidence as float (e.g. 0.75 or 75.0, required if using --create)")
    parser.add_argument("-r", "--report-date", type=str, help="Report date YYYY-MM-DD (defaults to today if creating)")
    
    args = parser.parse_args()
    
    # Default to --all if no specific ticker is supplied
    run_all = args.all or (not args.ticker)
    
    # Initialize data source and scorer
    config = DataSourceConfig(rate_limit_calls=100, rate_limit_period=60)
    yahoo = YahooFinanceDataSource(config)
    yahoo.connect()
    scorer = PredictionScorer(yahoo)
    
    with Session(engine) as session:
        # Scenario A: Score all unscored predictions
        if run_all:
            print("Scanning database for all unscored predictions...")
            statement = select(Prediction).where(Prediction.actual_direction == None)
            unscored = session.exec(statement).all()
            
            if not unscored:
                print("No unscored predictions found in the database.")
            else:
                print(f"Found {len(unscored)} unscored prediction(s). Processing...")
                scored_count = 0
                for p in unscored:
                    if score_and_save(scorer, session, p):
                        scored_count += 1
                print(f"\nCompleted scoring. Scored {scored_count}/{len(unscored)} predictions.")
                
        # Scenario B: Score a specific ticker
        else:
            ticker = args.ticker.upper().strip()
            print(f"Searching for predictions for ticker: {ticker}")
            statement = select(Prediction).where(Prediction.ticker == ticker)
            preds = session.exec(statement).all()
            
            if preds:
                print(f"Found {len(preds)} prediction(s) for {ticker}. Scoring them...")
                for p in preds:
                    score_and_save(scorer, session, p)
            else:
                # Ticker not found. Check if we should create it.
                if args.create:
                    if not args.direction or args.confidence is None:
                        print("[ERROR] Creating a new prediction requires --direction (-d) and --confidence (-p).")
                        sys.exit(1)
                        
                    print(f"No existing prediction found for {ticker}. Creating a new record...")
                    # Get or create runner user
                    stmt_user = select(User).where(User.clerk_id == "user_nike_debate_run_2026")
                    user = session.exec(stmt_user).first()
                    if not user:
                        stmt_any_user = select(User)
                        user = session.exec(stmt_any_user).first()
                    if not user:
                        user = User(clerk_id="user_nike_debate_run_2026", email="nike_debate_runner@example.com")
                        session.add(user)
                        session.commit()
                        session.refresh(user)
                    
                    rep_date = datetime.strptime(args.report_date, "%Y-%m-%d") if args.report_date else datetime.now()
                    
                    conf = args.confidence
                    if conf > 1.0:
                        conf /= 100.0  # Normalize to 0-1 scale
                        
                    p_new = Prediction(
                        user_id=user.id,
                        ticker=ticker,
                        company_name=f"{ticker} Corporation",
                        report_date=rep_date,
                        report_timing="UNKNOWN",
                        direction=args.direction.upper(),
                        confidence=conf,
                        reasoning_summary=f"Manually created prediction for {ticker}.",
                        bull_factors=[],
                        bear_factors=[]
                    )
                    session.add(p_new)
                    session.commit()
                    session.refresh(p_new)
                    print(f"Successfully inserted new prediction for {ticker} (ID {p_new.id})")
                    score_and_save(scorer, session, p_new)
                else:
                    print(f"[Warning] No predictions found for ticker '{ticker}'. Run with --create (-c) to add one manually.")
                    
    yahoo.disconnect()
    print("\nDone.")

if __name__ == "__main__":
    main()
