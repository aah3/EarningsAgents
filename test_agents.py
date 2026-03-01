import os
import logging
from datetime import date
from agents.huggingface_agents import ThreeAgentSystem
from config.settings import AgentConfig, CompanyData, ReportTime, PredictionDirection, NewsArticle

# Setup logging
logging.basicConfig(level=logging.INFO)

def test_agent_flow():
    print("🚀 Starting Agent System Test...")
    
    # Load Gemini Key from environment
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        print("❌ Error: GEMINI_API_KEY not found in environment.")
        return

    # Configure the system to use Gemini 2.0 Flash
    config = AgentConfig(
        provider="gemini",
        model_name="gemini-2.0-flash",
        api_key=gemini_key
    )
    
    system = ThreeAgentSystem(config)
    print("✅ Initializing agents...")
    system.initialize()
    
    # Mock Company Data
    company = CompanyData(
        ticker="TSLA",
        company_name="Tesla, Inc.",
        sector="Consumer Cyclical",
        industry="Auto Manufacturers",
        market_cap=600e9,
        report_date=date(2024, 4, 23),
        consensus_eps=0.51,
        consensus_revenue=22.3e9,
        num_analysts=35,
        beat_rate_4q=0.5,
        avg_surprise_4q=-2.1
    )
    
    # Mock News
    news = [
        NewsArticle(headline="Tesla sales drop in China amid rising competition", sentiment_score=-0.4),
        NewsArticle(headline="Elon Musk announces new low-cost model roadmap", sentiment_score=0.6),
        NewsArticle(headline="Analysts cut price targets on Tesla ahead of earnings", sentiment_score=-0.3)
    ]
    
    print(f"🤖 Running analysis for {company.ticker}...")
    try:
        prediction = system.predict(company, news)
        
        print("\n=== ANALYSIS RESULT ===")
        print(f"Ticker: {prediction.ticker}")
        print(f"Final Call: {prediction.direction.value.upper()}")
        print(f"Confidence: {prediction.confidence:.0%}")
        print(f"Reasoning: {prediction.reasoning_summary}")
        print("\n=== AGENT VOTES ===")
        for agent, vote in prediction.agent_votes.items():
            print(f"- {agent.title()}: {vote.upper()}")
            
        print("\n✅ Test Completed Successfully!")
        
    except Exception as e:
        print(f"❌ Test Failed with Error: {e}")
    finally:
        system.shutdown()

if __name__ == "__main__":
    test_agent_flow()
