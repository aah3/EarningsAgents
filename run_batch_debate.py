import os
import sys
import time
from datetime import date, datetime
import logging

# Ensure project root is in python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from settings import load_config
from pipeline import EarningsPipeline
from database.db import Session, engine, init_db
from database.models import User, Prediction
from sqlmodel import select, text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("BatchDebateRunner")

def main():
    print("=" * 70)
    print("         AI EARNINGS DEBATE BATCH RUNNER (BAC & WFC)")
    print("         Reporting Date: July 14, 2026")
    print("=" * 70)
    
    # 1. Initialize DB
    print("\n[Step 1] Initializing Supabase database tables...")
    try:
        init_db()
        print("Database initialized successfully.")
    except Exception as e:
        print(f"Database initialization failed: {e}")
        sys.exit(1)

    # Clean up existing BAC & WFC data to guarantee a fresh fetch/sync
    print("\n[Step 1b] Cleaning up existing BAC and WFC database rows...")
    with Session(engine) as session:
        for ticker in ["BAC", "WFC"]:
            session.exec(text(f"DELETE FROM earnings_history WHERE ticker='{ticker}'"))
            session.exec(text(f"DELETE FROM earnings_calendar_event WHERE ticker='{ticker}'"))
        session.commit()
    print("Clean up completed.")
        
    # 2. Initialize pipeline
    print("\n[Step 2] Initializing the Earnings Prediction Pipeline...")
    config = load_config()
    
    config.agent.enable_rebuttals = True
    config.agent.use_react = False
    
    print(f"LLM Provider:   {config.agent.provider}")
    print(f"LLM Model:      {config.agent.model_name}")
    print(f"Rebuttals:      {config.agent.enable_rebuttals}")
    print(f"ReAct loop:     {config.agent.use_react}")
    
    pipeline = EarningsPipeline(config)
    try:
        pipeline.initialize()
        print("Pipeline initialized successfully.")
    except Exception as e:
        print(f"Pipeline initialization failed: {e}")
        sys.exit(1)
        
    # 3. Run predictions in batch mode
    print("\n[Step 3] Running the AI Debate in Batch Mode...")
    companies_data = [
        {"ticker": "BAC", "report_date": date(2026, 7, 14)},
        {"ticker": "WFC", "report_date": date(2026, 7, 14)}
    ]
    
    start_time = time.time()
    try:
        predictions = pipeline.predict_batch(companies_data)
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"\nBatch debate completed in {elapsed_time:.2f} seconds ({elapsed_time/60.0:.2f} minutes).")
    except Exception as e:
        print(f"Batch prediction failed: {e}")
        pipeline.shutdown()
        sys.exit(1)
        
    # 4. Save results and print summary for each company
    print("\n[Step 4] Saving results to Supabase and displaying summary...")
    clerk_id = "user_batch_debate_run_2026"
    
    try:
        with Session(engine) as session:
            # Get or create user
            statement = select(User).where(User.clerk_id == clerk_id)
            user = session.exec(statement).first()
            if not user:
                user = User(clerk_id=clerk_id, email="batch_debate_runner@example.com")
                session.add(user)
                session.commit()
                session.refresh(user)
                print(f"Created new batch runner user: ID {user.id}")
            else:
                print(f"Found existing batch runner user: ID {user.id}")
            
            for pred in predictions:
                print("\n" + "=" * 50)
                print(f" Ticker: {pred.ticker} | Company: {pred.company_name}")
                print(f" Consensus Direction: {pred.direction.value.upper()}")
                print(f" Confidence: {pred.confidence * 100:.1f}%")
                print(f" Expected Move: {pred.expected_price_move}")
                print(f" Move vs Implied: {pred.move_vs_implied}")
                print(f" Consensus Reasoning: {pred.reasoning_summary}")
                print("=" * 50)
                
                # Create prediction record
                db_prediction = Prediction(
                    user_id=user.id,
                    ticker=pred.ticker,
                    company_name=pred.company_name,
                    report_date=datetime.combine(pred.report_date, datetime.min.time()),
                    report_timing=getattr(pred, "report_time", "UNKNOWN"),
                    direction=pred.direction.value.upper(),
                    confidence=pred.confidence,
                    expected_price_move=pred.expected_price_move,
                    move_vs_implied=pred.move_vs_implied,
                    guidance_expectation=pred.guidance_expectation,
                    likely_guidance=getattr(pred, "likely_guidance", ""),
                    reasoning_summary=pred.reasoning_summary,
                    bull_factors=pred.bull_factors,
                    bear_factors=pred.bear_factors,
                    debate_summary=pred.debate_summary,
                    rebuttal_summary=pred.rebuttal_summary,
                    agent_votes=pred.agent_votes,
                    options_features=pred.options_features,
                )
                session.add(db_prediction)
                session.commit()
                session.refresh(db_prediction)
                
                # Sync company profile
                try:
                    from database.earnings_repo import _refresh_profile
                    _refresh_profile(session, pred.ticker)
                except Exception as pe:
                    print(f"Warning: Failed to save/refresh company profile for {pred.ticker}: {pe}")
                    
                print(f"Saved prediction for {pred.ticker} to Supabase! ID: {db_prediction.id}")
                
                # Verification
                statement_verify = select(Prediction).where(Prediction.id == db_prediction.id)
                verified = session.exec(statement_verify).first()
                if verified:
                    print(f"Verification: Successfully verified {verified.ticker} prediction in DB.")
                    
    except Exception as e:
        print(f"Error saving batch results to database: {e}")
        
    # Shutdown pipeline
    pipeline.shutdown()
    print("\nBatch run complete.")

if __name__ == "__main__":
    main()
