import os
import sys
from datetime import date, datetime
from sqlmodel import Session, select

# Ensure project root is in python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import engine, init_db
from database.models import User, Prediction
from database.scoring_service import PredictionScorer
from data.yahoo_finance import YahooFinanceDataSource, DataSourceConfig

def main():
    print("=" * 70)
    print("         SUPABASE PREDICTION DATABASE UPDATER")
    print("=" * 70)
    
    # Initialize data source and scorer
    config = DataSourceConfig(rate_limit_calls=100, rate_limit_period=60)
    yahoo = YahooFinanceDataSource(config)
    yahoo.connect()
    scorer = PredictionScorer(yahoo)
    
    with Session(engine) as session:
        # 1. Update NKE (ID 14)
        print("\n--- 1. Updating NKE Prediction ---")
        stmt_nke = select(Prediction).where(Prediction.ticker == "NKE")
        nke_preds = session.exec(stmt_nke).all()
        
        if not nke_preds:
            print("[Warning] No NKE predictions found in database!")
        else:
            for p in nke_preds:
                print(f"Found NKE prediction ID={p.id}")
                print(f"  Current values: Actual={p.actual_direction}, EPS={p.actual_eps}, Price Move={p.actual_price_move_pct}, Score={p.accuracy_score}")
                
                # Fetch ground truth and compute correct Brier score
                result = scorer.score_prediction(p)
                if result.get("scored"):
                    p.actual_direction = result["actual_direction"]
                    p.actual_eps = result["actual_eps"]
                    p.actual_price_move_pct = result["actual_price_move_pct"]
                    p.accuracy_score = result["accuracy_score"]
                    p.scored_at = result["scored_at"]
                    
                    session.add(p)
                    session.commit()
                    session.refresh(p)
                    print(f"  [SUCCESS] Updated NKE (ID {p.id}) successfully:")
                    print(f"    Actual Direction: {p.actual_direction}")
                    print(f"    Actual EPS:       {p.actual_eps}")
                    print(f"    Price Move %:     {p.actual_price_move_pct:.6f} ({p.actual_price_move_pct*100:.2f}%)")
                    print(f"    Brier Score:      {p.accuracy_score:.6f}")
                    print(f"    Scored At:        {p.scored_at}")
                else:
                    print(f"  [ERROR] Failed to score NKE: {result.get('reason')}")
                    
        # 2. Check and Update PRGS (Progress Software)
        print("\n--- 2. Updating/Inserting PRGS Prediction ---")
        stmt_prgs = select(Prediction).where(Prediction.ticker == "PRGS")
        prgs_preds = session.exec(stmt_prgs).all()
        
        p_prgs = None
        if not prgs_preds:
            print("No existing PRGS prediction found. Creating a prediction record...")
            # We need a user to associate the prediction with. Let's find the runner user.
            stmt_user = select(User).where(User.clerk_id == "user_nike_debate_run_2026")
            user = session.exec(stmt_user).first()
            if not user:
                # Fallback to any user
                stmt_any_user = select(User)
                user = session.exec(stmt_any_user).first()
            
            if not user:
                # Create a temporary runner user if none exists
                user = User(clerk_id="user_nike_debate_run_2026", email="nike_debate_runner@example.com")
                session.add(user)
                session.commit()
                session.refresh(user)
                print(f"Created new database user ID {user.id}")
                
            # Create a prediction record representing the consensus prediction:
            # We predict BEAT with 78% confidence (0.78) for PRGS reporting on 2026-06-30.
            p_prgs = Prediction(
                user_id=user.id,
                ticker="PRGS",
                company_name="Progress Software Corporation",
                report_date=datetime(2026, 6, 30),
                direction="BEAT",
                confidence=0.78,
                reasoning_summary="Consensus AI prediction for Progress Software (PRGS) earnings debate.",
                bull_factors=["Strong cloud product demand", "Stable recurring maintenance revenues"],
                bear_factors=["Increasing competition", "High sales cycles in mid-market"],
                expected_price_move="3-5%",
                move_vs_implied="in-line",
                guidance_expectation="stable"
            )
            session.add(p_prgs)
            session.commit()
            session.refresh(p_prgs)
            print(f"Successfully inserted new PRGS prediction with ID={p_prgs.id}")
        else:
            p_prgs = prgs_preds[0]
            print(f"Found existing PRGS prediction ID={p_prgs.id}")
            
        # Score the PRGS prediction
        print(f"Scoring PRGS prediction...")
        result = scorer.score_prediction(p_prgs)
        if result.get("scored"):
            p_prgs.actual_direction = result["actual_direction"]
            p_prgs.actual_eps = result["actual_eps"]
            p_prgs.actual_price_move_pct = result["actual_price_move_pct"]
            p_prgs.accuracy_score = result["accuracy_score"]
            p_prgs.scored_at = result["scored_at"]
            
            session.add(p_prgs)
            session.commit()
            session.refresh(p_prgs)
            print(f"  [SUCCESS] Scored/Updated PRGS (ID {p_prgs.id}) successfully:")
            print(f"    Actual Direction: {p_prgs.actual_direction}")
            print(f"    Actual EPS:       {p_prgs.actual_eps}")
            print(f"    Price Move %:     {p_prgs.actual_price_move_pct:.6f} ({p_prgs.actual_price_move_pct*100:.2f}%)")
            print(f"    Brier Score:      {p_prgs.accuracy_score:.6f}")
            print(f"    Scored At:        {p_prgs.scored_at}")
        else:
            print(f"  [ERROR] Failed to score PRGS: {result.get('reason')}")
            
    yahoo.disconnect()
    print("\nDatabase update completed successfully!")

if __name__ == "__main__":
    main()
