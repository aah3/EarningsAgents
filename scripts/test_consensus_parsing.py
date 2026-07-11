import sys
import os

# Set python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../agents")))

from agents.huggingface_agents import ConsensusAgent, PredictionDirection
from config.settings import AgentConfig, CompanyData
from datetime import date

def test_parsing():
    print("Testing ConsensusAgent response parsing with likely_guidance...")
    
    cfg = AgentConfig(provider="gemini", model_name="gemini-flash-latest", api_key="dummy")
    consensus = ConsensusAgent(cfg)
    
    raw_response = """
Here is my thinking: I believe the company is in a strong position.
```json
{
    "direction": "BEAT",
    "confidence": 85,
    "expected_price_move": "positive",
    "move_vs_implied": "exceeds implied move",
    "guidance_expectation": "positive",
    "likely_guidance": "Management is expected to raise full-year EPS guidance from $3.20-$3.40 to $3.45-$3.55 due to strong enterprise adoption.",
    "reasoning": "Strong revisions and positive customer feedback support a beat.",
    "bull_factors": ["High retention rate", "Enterprise segment acceleration"],
    "bear_factors": ["Higher R&D expenses"],
    "key_signals": {
        "deciding_factor": "enterprise acceleration",
        "bull_strength": "8",
        "bear_strength": "3"
    }
}
```
"""
    
    result = consensus._parse_response(raw_response)
    print("Parsing success!")
    print(f"Direction: {result.direction}")
    print(f"Confidence: {result.confidence}")
    print(f"Guidance Expectation: {result.guidance_expectation}")
    print(f"Likely Guidance Detail: {result.likely_guidance}")
    
    assert result.direction == PredictionDirection.BEAT
    assert result.likely_guidance == "Management is expected to raise full-year EPS guidance from $3.20-$3.40 to $3.45-$3.55 due to strong enterprise adoption."
    print("Verification completed successfully!")

if __name__ == "__main__":
    test_parsing()
