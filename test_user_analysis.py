import os
from datetime import date
from config.settings import load_config, CompanyData
from agents.huggingface_agents import ThreeAgentSystem

def test_user_analysis():
    print("Testing Analyst (User Analysis) in agent debate...")
    config = load_config()
    agent_system = ThreeAgentSystem(config.agent)
    agent_system.initialize()
    
    # Mock data
    company = CompanyData(
        ticker="TEST",
        company_name="Test Corp",
        sector="Technology",
        industry="Software",
        market_cap=1e10,
        report_date=date.today(),
    )
    # news = ["TEST Corp likely to beat earnings due to widespread adoption of their new software."]
    news = []
    
    # User analysis string
    user_analysis = "I strongly believe TEST Corp will CRUSH earnings because I bought their new software and it's amazing. They have strong pricing power."
    
    print("Running predict with user_analysis...")
    prediction = agent_system.predict(company, news, prediction_date=date.today(), task_id=None, user_analysis=user_analysis)
    
    print("\n" + "="*50)
    print(f"Prediction: {prediction.direction.value}")
    print(f"Confidence: {prediction.confidence}")
    print("Agent votes:")
    for k, v in prediction.agent_votes.items():
        print(f"  {k}: {v}")
    
    assert "analyst" in prediction.agent_votes, "Analyst vote missing"
    assert prediction.agent_votes["analyst"] == "user_provided", "Analyst vote incorrect"
    
    print("\nSUCCESS: User analysis integrated.")

if __name__ == "__main__":
    test_user_analysis()
