import pytest
from unittest.mock import patch, MagicMock
from datetime import date
from config.settings import AgentConfig, CompanyData, PredictionDirection, EarningsPrediction

from agents.huggingface_agents import (
    BaseAgent, BullAgent, BearAgent, QuantAgent, ConsensusAgent, ThreeAgentSystem,
    AgentResponse, AgentResponseError, ConsensusError
)
from agents.llm_client import LLMClient

@pytest.fixture
def base_config():
    return AgentConfig(provider="openai", model_name="gpt-4", api_key="sk-test")

@pytest.fixture
def mock_company():
    return CompanyData(
        ticker="TSLA",
        company_name="Tesla",
        sector="Tech",
        industry="Auto",
        market_cap=600e9,
        report_date=date(2024, 4, 1),
        consensus_eps=0.5,
        consensus_revenue=20e9,
        num_analysts=30
    )

def test_agent_response_error_malformed_json(base_config, mock_company):
    agent = BaseAgent(base_config, "Test")
    with patch.object(LLMClient, 'generate', return_value="Malformed JSON: { 'direction': 'BEAT' }"):
        with pytest.raises(AgentResponseError) as exc:
            agent.analyze(mock_company, [])
        assert "failed to formulate a response" in str(exc.value)

def test_agent_response_error_429(base_config, mock_company):
    agent = BaseAgent(base_config, "Test")
    with patch.object(LLMClient, 'generate', side_effect=Exception("429 Too Many Requests")):
        with pytest.raises(AgentResponseError) as exc:
            agent.analyze(mock_company, [])
        assert "failed to formulate a response: 429" in str(exc.value)

def test_agent_response_error_auth_failure(base_config, mock_company):
    agent = BaseAgent(base_config, "Test")
    with patch.object(LLMClient, 'generate', side_effect=Exception("401 Unauthorized")):
        with pytest.raises(AgentResponseError) as exc:
            agent.analyze(mock_company, [])
        assert "failed to formulate a response: 401" in str(exc.value)

def test_predict_partial_failures(base_config, mock_company):
    """If BearAgent throws AgentResponseError but others succeed, predict() does not crash."""
    system = ThreeAgentSystem(base_config)
    def mock_bull(*args, **kwargs):
        return AgentResponse(direction=PredictionDirection.BEAT, confidence=0.8, expected_price_move="positive", move_vs_implied="inside", guidance_expectation="neutral", reasoning="bull", bull_factors=[], bear_factors=[], key_signals={})
    def mock_bear(*args, **kwargs):
        raise AgentResponseError("BearAgent", Exception("Failed for some reason"))
    def mock_quant(*args, **kwargs):
        return AgentResponse(direction=PredictionDirection.MEET, confidence=0.7, expected_price_move="neutral", move_vs_implied="inside", guidance_expectation="neutral", reasoning="quant", bull_factors=[], bear_factors=[], key_signals={})
    
    with patch.object(BullAgent, 'analyze', side_effect=mock_bull), \
         patch.object(BearAgent, 'analyze', side_effect=mock_bear), \
         patch.object(QuantAgent, 'analyze', side_effect=mock_quant), \
         patch.object(ConsensusAgent, 'synthesize', return_value=AgentResponse(direction=PredictionDirection.BEAT, confidence=0.9, expected_price_move="positive", move_vs_implied="inside", guidance_expectation="neutral", reasoning="consensus", bull_factors=[], bear_factors=[], key_signals={})):
        
        result = system.predict(mock_company, [])
        assert result.agent_votes["bull"] == "beat"
        assert result.agent_votes["bear"] == "failed"
        assert result.agent_votes["quant"] == "meet"
        assert result.agent_votes["consensus"] == "beat"

def test_predict_consensus_error(base_config, mock_company):
    """If 2 or more fail, ConsensusError is raised by synthesize (and predictable propagated)."""
    system = ThreeAgentSystem(base_config)
    def mock_fail(*args, **kwargs):
        raise AgentResponseError("Agent", Exception("Failed"))
    def mock_succ(*args, **kwargs):
        return AgentResponse(direction=PredictionDirection.BEAT, confidence=0.8, expected_price_move="positive", move_vs_implied="inside", guidance_expectation="neutral", reasoning="bull", bull_factors=[], bear_factors=[], key_signals={})
    
    # 2 fails, 1 success -> synthesize will raise ConsensusError
    with patch.object(BullAgent, 'analyze', side_effect=mock_fail), \
         patch.object(BearAgent, 'analyze', side_effect=mock_fail), \
         patch.object(QuantAgent, 'analyze', side_effect=mock_succ):
         
         with pytest.raises(ConsensusError):
             system.predict(mock_company, [])

def test_provider_kwargs_routing():
    # OpenAI
    cfg_openai = AgentConfig(provider="openai", model_name="gpt-4o", api_key="test")
    agent_openai = BaseAgent(cfg_openai, "Test")
    kw_open = agent_openai._get_llm_kwargs()
    assert "response_format" in kw_open
    assert kw_open["response_format"]["type"] == "json_schema"
    assert "tool_choice" not in kw_open
    assert "tools" not in kw_open
    
    # Anthropic
    cfg_anth = AgentConfig(provider="anthropic", model_name="claude-3", api_key="test")
    agent_anth = BaseAgent(cfg_anth, "Test")
    kw_anth = agent_anth._get_llm_kwargs()
    assert "tools" in kw_anth
    assert "tool_choice" in kw_anth
    assert "response_format" not in kw_anth
    assert kw_anth["tool_choice"]["name"] == "AgentResponse"
    
    # Gemini
    cfg_gem = AgentConfig(provider="gemini", model_name="gemini-1.5", api_key="test")
    agent_gem = BaseAgent(cfg_gem, "Test")
    kw_gem = agent_gem._get_llm_kwargs()
    assert "generation_config" in kw_gem
    assert kw_gem["generation_config"]["response_mime_type"] == "application/json"
    assert "response_format" not in kw_gem
    assert "tool_choice" not in kw_gem

def test_synthesize_with_successful_agents(base_config, mock_company):
    consensus = ConsensusAgent(base_config)
    bull = AgentResponse(direction=PredictionDirection.BEAT, confidence=0.8, expected_price_move="positive", move_vs_implied="inside", guidance_expectation="neutral", reasoning="bull", bull_factors=["A"], bear_factors=[], key_signals={'beat_rate': 'yes'})
    bear = None
    quant = AgentResponse(direction=PredictionDirection.MEET, confidence=0.7, expected_price_move="neutral", move_vs_implied="inside", guidance_expectation="neutral", reasoning="quant", bull_factors=[], bear_factors=[], key_signals={})
    
    with patch.object(LLMClient, 'generate', return_value='{"direction":"BEAT","confidence":0.75,"expected_price_move":"positive","move_vs_implied":"inside","guidance_expectation":"neutral","reasoning":"consensus logic","bull_factors":[],"bear_factors":[],"key_signals":{}}'):
        res = consensus.synthesize(mock_company, bull_response=bull, bear_response=bear, quant_response=quant)
        assert res.direction == PredictionDirection.BEAT

def test_synthesize_consensus_error(base_config, mock_company):
    consensus = ConsensusAgent(base_config)
    bull = AgentResponse(direction=PredictionDirection.BEAT, confidence=0.8, expected_price_move="pos", move_vs_implied="ins", guidance_expectation="neu", reasoning="bull", bull_factors=[], bear_factors=[], key_signals={})
    
    # Missing 2/3 agents
    with pytest.raises(ConsensusError) as exc:
        consensus.synthesize(mock_company, bull_response=bull, bear_response=None, quant_response=None)
    assert "Fewer than 2 agents succeeded" in str(exc.value)
