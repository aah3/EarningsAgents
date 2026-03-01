import logging
from datetime import date
from pipeline import EarningsPipeline
from config.settings import load_config

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def test_cost_real():
    print("🚀 Starting Real Analysis for COST (Costco)...")
    
    # Load configuration
    config = load_config()
    
    # Initialize Pipeline
    pipeline = EarningsPipeline(config)
    print("✅ Initializing pipeline (fetching sector data, setting up agents)...")
    pipeline.initialize()
    
    try:
        # Costco reported on Dec 12, 2024, or will report soon.
        # Let's use a recent/upcoming date for the analysis context.
        report_date = date(2025, 3, 6) # Upcoming Costco report date
        
        print(f"🤖 Running Multi-Agent Debate for COST reporting on {report_date}...")
        prediction = pipeline.predict_single("COST", report_date)
        
        print("\n" + "="*50)
        print(f"🏆 FINAL PREDICTION FOR {prediction.ticker}")
        print("="*50)
        print(f"Company: {prediction.company_name}")
        print(f"Direction: {prediction.direction.value.upper()}")
        print(f"Confidence: {prediction.confidence:.1%}")
        print(f"\nSummary:\n{prediction.reasoning_summary}")
        
        print("\n📈 BULL FACTORS:")
        for factor in prediction.bull_factors:
            print(f"  + {factor}")
            
        print("\n📉 BEAR FACTORS:")
        for factor in prediction.bear_factors:
            print(f"  - {factor}")
            
        print("\n🗳️ AGENT VOTES:")
        for agent, vote in prediction.agent_votes.items():
            print(f"  {agent.title()}: {vote.upper()}")
            
        print("\n✅ Analysis Completed Successfully!")
        
    except Exception as e:
        print(f"❌ Analysis failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        pipeline.shutdown()

if __name__ == "__main__":
    test_cost_real()
