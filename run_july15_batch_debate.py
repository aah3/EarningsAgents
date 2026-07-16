import os
import sys
import time
from datetime import date, datetime
import logging

# Ensure project root is in python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from settings import load_config
from data.base import ReportTime
from pipeline import EarningsPipeline
from database.db import Session, engine, init_db
from database.models import User, Prediction
from sqlmodel import select, text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("July15BatchDebateRunner")

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
            # Force the report timing based on user requirements
            ticker_upper = t.upper()
            if ticker_upper in ["UAL", "GSBC"]:
                company_data.report_time = ReportTime.AMC
                logger.info(f"Forced report time for {ticker_upper} to AMC (After Market Close)")
            elif ticker_upper in ["IIIN", "UNH"]:
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
    print("         AI EARNINGS DEBATE BATCH RUNNER (UAL, GSBC, IIIN, UNH)")
    print("         Run Date: July 15, 2026")
    print("=" * 70)
    
    # 1. Initialize DB
    print("\n[Step 1] Initializing database tables...")
    try:
        init_db()
        print("Database initialized successfully.")
    except Exception as e:
        print(f"Database initialization failed: {e}")
        sys.exit(1)

    # Get or create batch user
    clerk_id = "user_july15_batch_debate_run"
    user_id = None
    try:
        with Session(engine) as session:
            statement = select(User).where(User.clerk_id == clerk_id)
            user = session.exec(statement).first()
            if not user:
                user = User(clerk_id=clerk_id, email="july15_debate_runner@example.com")
                session.add(user)
                session.commit()
                session.refresh(user)
                print(f"Created new batch runner user: ID {user.id}")
            else:
                print(f"Found existing batch runner user: ID {user.id}")
            user_id = user.id
    except Exception as e:
        print(f"Error initializing batch runner user in database: {e}")
        sys.exit(1)

    # Clean up existing database rows for UAL, GSBC, IIIN, UNH to guarantee a fresh fetch/sync
    tickers_to_run = ["UAL", "GSBC", "IIIN", "UNH"]
    print(f"\n[Step 1b] Cleaning up existing DB rows for {tickers_to_run}...")
    with Session(engine) as session:
        for ticker in tickers_to_run:
            session.exec(text(f"DELETE FROM earnings_history WHERE ticker='{ticker}'"))
            session.exec(text(f"DELETE FROM earnings_calendar_event WHERE ticker='{ticker}'"))
            # Also clean up any prior predictions for these tickers from today's run
            session.exec(text(f"DELETE FROM prediction WHERE ticker='{ticker}' AND user_id={user_id}"))
        session.commit()
    print("Clean up completed.")
        
    # 2. Initialize pipeline
    print("\n[Step 2] Initializing the Earnings Prediction Pipeline...")
    config = load_config()
    
    # Ensure rebuttals are enabled and ReAct is disabled for the debate run
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
        
    # 3. Run predictions in loop and save immediately
    print("\n[Step 3] Running the AI Debate for each company...")
    companies_data = [
        {"ticker": "UAL", "report_date": date(2026, 7, 15)},
        {"ticker": "GSBC", "report_date": date(2026, 7, 15)},
        {"ticker": "IIIN", "report_date": date(2026, 7, 16)},
        {"ticker": "UNH", "report_date": date(2026, 7, 16)}
    ]
    
    start_time = time.time()
    for i, company in enumerate(companies_data):
        ticker = company["ticker"]
        report_date = company["report_date"]
        print(f"\nProcessing {i+1}/{len(companies_data)}: {ticker}")
        
        try:
            pred = pipeline.predict_single(ticker, report_date)
            
            # Print Summary
            print("\n" + "=" * 80)
            print(f" TICKER: {pred.ticker} | COMPANY: {pred.company_name}")
            print(f" Consensus Direction: {pred.direction.value.upper()}")
            print(f" Confidence: {pred.confidence * 100:.1f}%")
            print(f" Expected Move: {pred.expected_price_move}")
            print(f" Move vs Implied: {pred.move_vs_implied}")
            print(f" Timing: {pred.report_time}")
            print("-" * 80)
            print(f" Consensus Reasoning:\n{pred.reasoning_summary}")
            
            if pred.debate_summary:
                print("-" * 80)
                print(" DEBATE SUMMARY (PASS 1):")
                print(pred.debate_summary)
                
            if pred.rebuttal_summary:
                print("-" * 80)
                print(" REBUTTAL ROUND (PASS 2):")
                print(pred.rebuttal_summary)
            print("=" * 80)
            
            # Save prediction to Database immediately
            with Session(engine) as session:
                db_prediction = Prediction(
                    user_id=user_id,
                    ticker=pred.ticker,
                    company_name=pred.company_name,
                    report_date=datetime.combine(pred.report_date, datetime.min.time()),
                    report_timing=pred.report_time,
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
                
                print(f"Saved prediction for {pred.ticker} to Database! ID: {db_prediction.id}")
                
                # Double check verification
                statement_verify = select(Prediction).where(Prediction.id == db_prediction.id)
                verified = session.exec(statement_verify).first()
                if verified:
                    print(f"Verification: Successfully verified {verified.ticker} prediction in DB.")
                    
        except Exception as e:
            print(f"Error: Failed to process or save prediction for {ticker}: {e}")
            
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"\nBatch run completed in {elapsed_time:.2f} seconds ({elapsed_time/60.0:.2f} minutes).")
    
    # Shutdown pipeline
    pipeline.shutdown()

if __name__ == "__main__":
    main()
