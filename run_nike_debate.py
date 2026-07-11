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
from sqlmodel import select

# Configure logging to show what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("NikeDebateRunner")

def main():
    print("=" * 70)
    print("         AI EARNINGS DEBATE FOR NIKE (NKE) - RUNNER")
    print("         Reporting Date: June 30, 2026 (After close)")
    print("=" * 70)
    
    # 1. Initialize DB
    print("\n[Step 1] Initializing Supabase database tables...")
    try:
        init_db()
        print("Database initialized successfully.")
    except Exception as e:
        print(f"Database initialization failed: {e}")
        sys.exit(1)
        
    # 2. Initialize pipeline
    print("\n[Step 2] Initializing the Earnings Prediction Pipeline...")
    config = load_config()
    
    # Enable rebuttals for a thorough debate round, keep react false for speed/cost safety
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
        
    # 3. Run prediction & measure time
    print("\n[Step 3] Running the AI Debate for NKE (fetching data + LLM debate)...")
    start_time = time.time()
    try:
        prediction = pipeline.predict_single(
            ticker="NKE",
            report_date=date(2026, 6, 30)
        )
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"\nDebate completed successfully in {elapsed_time:.2f} seconds ({elapsed_time/60.0:.2f} minutes).")
    except Exception as e:
        print(f"Debate failed: {e}")
        pipeline.shutdown()
        sys.exit(1)
        
    # 4. Show output from each agent and consensus reasoning
    print("\n" + "=" * 70)
    print("                   AGENT DEBATE SUMMARY & OUTPUTS")
    print("=" * 70)
    if prediction.debate_summary:
        print(prediction.debate_summary)
    else:
        print(f"Consensus Direction: {prediction.direction.value.upper()}")
        print(f"Confidence: {prediction.confidence * 100:.1f}%")
        print(f"Consensus Reasoning: {prediction.reasoning_summary}")
        
    if prediction.rebuttal_summary:
        print("\n" + "=" * 70)
        print("                     REBUTTAL SUMMARY (PASS 2)")
        print("=" * 70)
        print(prediction.rebuttal_summary)
        
    # 5. Insert data into Supabase DB
    print("\n[Step 5] Writing prediction result to Supabase...")
    clerk_id = "user_nike_debate_run_2026"
    try:
        with Session(engine) as session:
            # Get or create user
            statement = select(User).where(User.clerk_id == clerk_id)
            user = session.exec(statement).first()
            if not user:
                user = User(clerk_id=clerk_id, email="nike_debate_runner@example.com")
                session.add(user)
                session.commit()
                session.refresh(user)
                print(f"Created new runner user: ID {user.id}")
            else:
                print(f"Found existing runner user: ID {user.id}")
                
            # Create prediction record
            db_prediction = Prediction(
                user_id=user.id,
                ticker="NKE",
                company_name=prediction.company_name,
                company_description=getattr(prediction, "company_description", None),
                sector=getattr(prediction, "sector", None),
                report_date=datetime.combine(prediction.report_date, datetime.min.time()),
                report_timing=getattr(prediction, "report_time", "UNKNOWN"),
                direction=prediction.direction.value.upper(),
                confidence=prediction.confidence,
                expected_price_move=prediction.expected_price_move,
                move_vs_implied=prediction.move_vs_implied,
                guidance_expectation=prediction.guidance_expectation,
                likely_guidance=getattr(prediction, "likely_guidance", ""),
                reasoning_summary=prediction.reasoning_summary,
                bull_factors=prediction.bull_factors,
                bear_factors=prediction.bear_factors,
                debate_summary=prediction.debate_summary,
                rebuttal_summary=prediction.rebuttal_summary,
                agent_votes=prediction.agent_votes,
                options_features=prediction.options_features,
            )
            session.add(db_prediction)
            session.commit()
            session.refresh(db_prediction)
            print(f"Successfully saved prediction to Supabase! ID: {db_prediction.id}")
            
            # Double check retrieval
            statement_verify = select(Prediction).where(Prediction.id == db_prediction.id)
            verified = session.exec(statement_verify).first()
            if verified:
                print(f"Verification check: Successfully retrieved row for NKE with ID {verified.id} and Direction {verified.direction}")
            
    except Exception as e:
        print(f"Error saving to database: {e}")
        
    # Shutdown pipeline
    pipeline.shutdown()
    print("\nRun complete.")

if __name__ == "__main__":
    main()
