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
from database.models import User, Prediction, EarningsHistory, EarningsCalendarEvent
from sqlmodel import select, text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("KLACDebateRunner")

def main():
    print("=" * 70)
    print("         AI EARNINGS DEBATE FOR KLA CORPORATION (KLAC) - RUNNER")
    print("         Reporting Date: July 30, 2026")
    print("=" * 70)
    
    # 1. Initialize DB
    print("\n[Step 1] Initializing database tables...")
    try:
        init_db()
        print("Database initialized successfully.")
    except Exception as e:
        print(f"Database initialization failed: {e}")
        sys.exit(1)

    # Clean up any existing KLAC history/calendar to guarantee fresh fetch/sync
    print("\n[Step 1b] Cleaning up existing KLAC data to ensure fresh sync...")
    with Session(engine) as session:
        session.exec(text("DELETE FROM earnings_history WHERE ticker='KLAC'"))
        session.exec(text("DELETE FROM earnings_calendar_event WHERE ticker='KLAC'"))
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
        
    # 3. Run prediction & measure time
    print("\n[Step 3] Running the AI Debate for KLAC (fetching data + LLM debate)...")
    start_time = time.time()
    try:
        prediction = pipeline.predict_single(
            ticker="KLAC",
            report_date=date(2026, 7, 30)
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
    try:
        with Session(engine) as session:
            system_user = session.exec(select(User).where(User.email == "system@earningsai.hero")).first()
            if not system_user:
                system_user = User(
                    clerk_id="system_user_klac",
                    email="system@earningsai.hero",
                    full_name="EarningsAI System Engine"
                )
                session.add(system_user)
                session.commit()
                session.refresh(system_user)

            db_prediction = Prediction(
                user_id=system_user.id,
                ticker="KLAC",
                company_name=prediction.company_name,
                report_date=datetime.combine(prediction.report_date, datetime.min.time()),
                report_timing=prediction.report_time,
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
            print(f"Successfully saved prediction for KLAC (ID: {db_prediction.id}) to database.")
    except Exception as e:
        print(f"Error writing to database: {e}")
        
    # 6. Shutdown pipeline
    pipeline.shutdown()
    print("\n" + "=" * 70)
    print(f"       KLAC AI EARNINGS DEBATE COMPLETE: PREDICTION = {prediction.direction.value.upper()}")
    print("=" * 70)

if __name__ == "__main__":
    main()
