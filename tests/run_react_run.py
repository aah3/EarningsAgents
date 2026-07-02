import os
import sys
import json
from datetime import date

# Add project root to path
sys.path.append(os.getcwd())

from settings import load_config, CompanyData, NewsArticle, ReportTime
from agents.huggingface_agents import ThreeAgentSystem, BullAgent, AgentResponseError

def test_react_debug():
    print("Loading config...")
    config = load_config()
    
    # We will print out the api key to make sure it's read (first few chars)
    gemini_key = os.getenv("GEMINI_API_KEY")
    print(f"Gemini API Key loaded (first 5 chars): {gemini_key[:5] if gemini_key else 'None'}")
    
    agent_system = ThreeAgentSystem(config.agent)
    agent_system.initialize()
    
    # Mock data for AVGO
    company = CompanyData(
        ticker="AVGO",
        company_name="Broadcom Inc.",
        sector="Technology",
        industry="Semiconductors",
        market_cap=650000000000,
        report_date=date(2026, 6, 3),
        report_time=ReportTime.AMC,
        consensus_eps=1.20,
        consensus_revenue=11500000000,
        num_analysts=25,
        historical_eps=[
            {"date": "2025-09-05", "surprise_pct": 2.1, "beat": True, "actual": 1.15, "estimate": 1.12},
            {"date": "2025-12-10", "surprise_pct": 1.5, "beat": True, "actual": 1.34, "estimate": 1.32},
            {"date": "2026-03-04", "surprise_pct": -0.5, "beat": False, "actual": 1.19, "estimate": 1.20},
        ],
        estimate_revisions=[],
        options_features={
            "put_call_volume_ratio": 0.85,
            "iv_skew": 0.05,
            "net_gamma_exposure": 1500000,
            "max_pain_to_spot": 0.02,
        },
    )
    company.recent_transcripts = ["Broadcom Q1 earnings transcript snippet: AI demand is extremely robust, Custom ASIC programs are scaling well with key hyper-scaler customers. Non-AI broadband remains cyclical but is bottoming out."]
    company.company_facts = {"Revenue": 11500000000, "GrossMargin": 0.75, "NetIncome": 3500000000}
    
    news = [
        NewsArticle(headline="Broadcom custom chip business gets major boost from new hyperscaler deal", sentiment_score=0.8, source="Reuters", published_at=date(2026, 5, 20)),
        NewsArticle(headline="Semiconductor industry shows mixed recovery signals, Broadcom stands out", sentiment_score=0.4, source="Bloomberg", published_at=date(2026, 5, 25)),
    ]
    
    agent = agent_system.bull_agent
    agent_name = "Bull"
    
    from agents.agent_tools import AgentToolRegistry
    registry = AgentToolRegistry(company, news)
    tool_descriptions = registry.get_tool_descriptions()
    react_system_prompt = agent._build_react_system_prompt(tool_descriptions)
    
    initial_user_message = (
        f"Ticker: {company.ticker}\n"
        f"Company: {company.company_name}\n"
        f"Report Date: 2026-06-03\n"
        f"Consensus EPS Estimate: ${company.consensus_eps:.2f}\n\n"
        "Analyze this company's earnings outlook. Use the available tools to "
        "gather the data you need, then return your final_answer."
    )
    messages = [{"role": "user", "content": initial_user_message}]
    
    print("\nStarting ReAct Loop Debug:")
    for turn in range(6):
        print(f"\n--- TURN {turn+1} ---")
        response = agent.llm.chat(
            system_prompt=react_system_prompt,
            messages=messages,
            temperature=agent.config.temperature,
            max_tokens=agent.config.max_tokens,
        )
        print(f"Assistant Response:\n{response}")
        messages.append({"role": "assistant", "content": response})
        
        try:
            parsed = json.loads(response)
        except json.JSONDecodeError as exc:
            print(f"JSONDecodeError: {exc}")
            break
            
        if "final_answer" in parsed:
            print("FOUND FINAL ANSWER!")
            break
            
        if "tool" in parsed:
            tool_name = parsed["tool"]
            tool_args = parsed.get("args", {}) or {}
            tool_result = registry.dispatch(tool_name, tool_args)
            print(f"Tool Call: {tool_name} with args {tool_args}")
            print(f"Tool Result: {tool_result.result if tool_result.error is None else 'Error: ' + tool_result.error}")
            
            tool_result_msg = {
                "tool_result": {
                    "tool": tool_name,
                    "data": tool_result.result if tool_result.error is None else {"error": tool_result.error},
                }
            }
            messages.append({"role": "user", "content": json.dumps(tool_result_msg, default=str)})
            continue
            
        print("Unexpected response format (no final_answer and no tool)")
        break

if __name__ == "__main__":
    test_react_debug()
