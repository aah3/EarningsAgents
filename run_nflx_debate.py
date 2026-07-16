import os
import sys
import time
from datetime import date, datetime
import logging

# Ensure project root is in python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from settings import load_config, ReportTime
from pipeline import EarningsPipeline
from database.db import Session, engine, init_db
from database.models import User, Prediction
from sqlmodel import select, text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("NFLXDebateRunner")

class CustomEarningsPipeline(EarningsPipeline):
    """
    Subclass of EarningsPipeline to force report times for specific tickers.
    This ensures that even if Yahoo Finance calendar fetches fail or return UNKNOWN,
    our agents receive the correct BMO / AMC context.
    """
    def predict_single(self, ticker, report_date, *args, **kwargs):
        original_get_company_data = self.aggregator.get_company_data
        
        def custom_get_company_data(t, rd, *a, **kw):
            company_data = original_get_company_data(t, rd, *a, **kw)
            # Force the report timing to BMO for NFLX
            ticker_upper = t.upper()
            if ticker_upper == "NFLX":
                company_data.report_time = ReportTime.BMO
                logger.info(f"Forced report time for {ticker_upper} to BMO (Before Market Open)")
            return company_data
            
        self.aggregator.get_company_data = custom_get_company_data
        try:
            return super().predict_single(ticker, report_date, *args, **kwargs)
        finally:
            self.aggregator.get_company_data = original_get_company_data

def main():
    print("=" * 70)
    print("         AI EARNINGS DEBATE FOR NETFLIX, INC. (NFLX) - RUNNER")
    print("         Reporting Date: July 17, 2026 (Before Market Open)")
    print("=" * 70)
    
    # 1. Initialize DB
    print("\n[Step 1] Initializing database tables...")
    try:
        init_db()
        print("Database initialized successfully.")
    except Exception as e:
        print(f"Database initialization failed: {e}")
        sys.exit(1)

    # Get or create runner user
    clerk_id = "user_nflx_debate_run"
    user_id = None
    try:
        with Session(engine) as session:
            statement = select(User).where(User.clerk_id == clerk_id)
            user = session.exec(statement).first()
            if not user:
                user = User(clerk_id=clerk_id, email="nflx_debate_runner@example.com")
                session.add(user)
                session.commit()
                session.refresh(user)
                print(f"Created new runner user: ID {user.id}")
            else:
                print(f"Found existing runner user: ID {user.id}")
            user_id = user.id
    except Exception as e:
        print(f"Error initializing user in database: {e}")
        sys.exit(1)

    # Clean up any existing NFLX history/calendar to guarantee a fresh fetch/sync
    print("\n[Step 1b] Cleaning up existing NFLX data to ensure fresh sync...")
    try:
        with Session(engine) as session:
            session.exec(text("DELETE FROM earnings_history WHERE ticker='NFLX'"))
            session.exec(text("DELETE FROM earnings_calendar_event WHERE ticker='NFLX'"))
            session.exec(text(f"DELETE FROM prediction WHERE ticker='NFLX'"))
            session.commit()
        print("Clean up completed.")
    except Exception as e:
        print(f"Warning during DB clean up: {e}")
        
    # 2. Initialize pipeline
    print("\n[Step 2] Initializing the Earnings Prediction Pipeline...")
    config = load_config()
    
    # Ensure rebuttals are enabled and ReAct is disabled for a clean debate run
    config.agent.model_name = "gemini-2.5-flash"
    config.agent.enable_rebuttals = True
    config.agent.use_react = False
    
    print(f"LLM Provider:   {config.agent.provider}")
    print(f"LLM Model:      {config.agent.model_name}")
    print(f"Rebuttals:      {config.agent.enable_rebuttals}")
    print(f"ReAct loop:     {config.agent.use_react}")
    
    pipeline = CustomEarningsPipeline(config)
    try:
        pipeline.initialize()
        print("Pipeline initialized successfully.")
    except Exception as e:
        print(f"Pipeline initialization failed: {e}")
        sys.exit(1)
        
    # 3. Run prediction & measure time
    print("\n[Step 3] Running the AI Debate for NFLX (fetching data + LLM debate)...")
    start_time = time.time()
    try:
        prediction = pipeline.predict_single(
            ticker="NFLX",
            report_date=date(2026, 7, 17)
        )
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"\nDebate completed successfully in {elapsed_time:.2f} seconds ({elapsed_time/60.0:.2f} minutes).")
    except Exception as e:
        print(f"Debate failed: {e}")
        pipeline.shutdown()
        sys.exit(1)
        
    # 4. Show output from each agent and consensus reasoning
    print("\n" + "=" * 80)
    print(f" TICKER: {prediction.ticker} | COMPANY: {prediction.company_name}")
    print(f" Consensus Direction: {prediction.direction.value.upper()}")
    print(f" Confidence: {prediction.confidence * 100:.1f}%")
    print(f" Expected Move: {prediction.expected_price_move}")
    print(f" Move vs Implied: {prediction.move_vs_implied}")
    print(f" Timing: {prediction.report_time}")
    print("-" * 80)
    print(f" Consensus Reasoning:\n{prediction.reasoning_summary}")
    
    if prediction.debate_summary:
        print("-" * 80)
        print(" DEBATE SUMMARY (PASS 1):")
        print(prediction.debate_summary)
        
    if prediction.rebuttal_summary:
        print("-" * 80)
        print(" REBUTTAL ROUND (PASS 2):")
        print(prediction.rebuttal_summary)
    print("=" * 80)
        
    # 5. Insert data into DB
    print("\n[Step 5] Writing prediction result to database...")
    try:
        with Session(engine) as session:
            # Create prediction record
            db_prediction = Prediction(
                user_id=user_id,
                ticker="NFLX",
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
            
            # Sync company profile
            try:
                from database.earnings_repo import _refresh_profile
                _refresh_profile(session, "NFLX")
            except Exception as pe:
                print(f"Warning: Failed to save/refresh company profile for NFLX: {pe}")
                
            print(f"Successfully saved prediction to Database! ID: {db_prediction.id}")
            
            # Double check retrieval
            statement_verify = select(Prediction).where(Prediction.id == db_prediction.id)
            verified = session.exec(statement_verify).first()
            if verified:
                print(f"Verification check: Successfully retrieved row for NFLX with ID {verified.id} and Direction {verified.direction}")
            
    except Exception as e:
        print(f"Error saving to database: {e}")
        
    # Shutdown pipeline
    pipeline.shutdown()
    print("\nRun complete.")

if __name__ == "__main__":
    main()
