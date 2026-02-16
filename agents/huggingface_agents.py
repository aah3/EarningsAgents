"""
Hugging Face Agents for Earnings Prediction POC.

Contains:
- BullAgent: Advocates for earnings BEAT
- BearAgent: Advocates for earnings MISS
- QuantAgent: Objective quantitative analysis
- ConsensusAgent: Synthesizes debate and makes final call
"""

import json
import re
import os
import logging
from datetime import date
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from config.settings import (
    AgentConfig,
    CompanyData,
    NewsArticle,
    EarningsPrediction,
    PredictionDirection,
)


# ============================================================================
# AGENT RESPONSE STRUCTURE
# ============================================================================

@dataclass
class AgentResponse:
    """Response from an agent analysis."""
    direction: PredictionDirection
    confidence: float
    reasoning: str
    bull_factors: List[str]
    bear_factors: List[str]
    key_signals: Dict[str, Any]
    raw_response: str = ""


# ============================================================================
# SYSTEM PROMPTS FOR EACH AGENT
# ============================================================================

BULL_PROMPT = """You are a BULL analyst specializing in identifying reasons why companies will BEAT earnings expectations.

YOUR MISSION: Find every positive signal that suggests an earnings beat.

ANALYSIS FOCUS:
1. Revenue strength signals (demand, market share, pricing power)
2. Margin improvement indicators (cost savings, operating leverage)
3. Positive estimate revision momentum
4. Management's track record of beating estimates
5. Positive sentiment and insider buying

OUTPUT FORMAT (JSON only, no other text):
{
    "direction": "BEAT",
    "confidence": <60-95>,
    "reasoning": "<2-3 sentence bull case>",
    "bull_factors": ["<factor 1>", "<factor 2>", "<factor 3>"],
    "bear_factors": ["<acknowledge 1 risk>"],
    "key_signals": {"estimate_momentum": "<detail>", "beat_rate": "<detail>"}
}"""


BEAR_PROMPT = """You are a BEAR analyst specializing in identifying risks that could cause companies to MISS earnings expectations.

YOUR MISSION: Find every warning sign that suggests an earnings miss.

ANALYSIS FOCUS:
1. Revenue risks (demand weakness, competition, macro headwinds)
2. Margin pressures (rising costs, pricing pressure)
3. Negative estimate revision trends
4. Execution risks and management concerns
5. High expectations that may be hard to meet

OUTPUT FORMAT (JSON only, no other text):
{
    "direction": "MISS",
    "confidence": <60-95>,
    "reasoning": "<2-3 sentence bear case>",
    "bull_factors": ["<acknowledge 1 positive>"],
    "bear_factors": ["<risk 1>", "<risk 2>", "<risk 3>"],
    "key_signals": {"estimate_risk": "<detail>", "headwinds": "<detail>"}
}"""


QUANT_PROMPT = """You are a QUANTITATIVE analyst focused on statistical patterns and numerical signals.

YOUR MISSION: Provide objective, data-driven prediction based on quantitative factors only.

ANALYSIS FOCUS:
1. Historical beat/miss rate (last 4-8 quarters)
2. Average surprise magnitude and consistency
3. Estimate revision trends (7d, 30d, 90d)
4. Pre-earnings price drift
5. Statistical probability assessment

OUTPUT FORMAT (JSON only, no other text):
{
    "direction": "BEAT" or "MISS" or "MEET",
    "confidence": <50-85>,
    "reasoning": "<statistical summary with specific numbers>",
    "bull_factors": ["<quantitative positives>"],
    "bear_factors": ["<quantitative negatives>"],
    "key_signals": {"beat_probability": "<X%>", "historical_beat_rate": "<X/Y>", "revision_trend": "<direction>"}
}"""


CONSENSUS_PROMPT = """You are the CONSENSUS analyst responsible for the final earnings prediction.

YOUR MISSION: Synthesize Bull, Bear, and Quant analyses to make the optimal prediction.

DECISION FRAMEWORK:
- Recent estimate revisions: 30% weight (most predictive)
- Historical beat/miss pattern: 25% weight
- Quantitative signals: 25% weight
- Qualitative factors: 20% weight

RULES:
- If Quant aligns with Bull or Bear: Weight Quant heavily
- If estimate revisions are strongly directional: Follow them
- If historical pattern is very consistent: Respect it

OUTPUT FORMAT (JSON only, no other text):
{
    "direction": "BEAT" or "MISS" or "MEET",
    "confidence": <50-95>,
    "reasoning": "<2-3 sentence final decision rationale>",
    "bull_factors": ["<accepted bull points>"],
    "bear_factors": ["<accepted bear points>"],
    "key_signals": {"deciding_factor": "<what tipped decision>", "bull_strength": "<1-10>", "bear_strength": "<1-10>"}
}"""


# ============================================================================
# BASE AGENT CLASS
# ============================================================================

class HuggingFaceAgent:
    """
    Base Hugging Face agent for earnings analysis.
    
    Supports both Inference API and local model loading.
    """
    
    def __init__(self, config: AgentConfig, system_prompt: str):
        self.config = config
        self.system_prompt = system_prompt
        self.logger = logging.getLogger(self.__class__.__name__)
        
        self.model = None
        self.tokenizer = None
        self.api_client = None
        self._initialized = False
    
    def initialize(self) -> bool:
        """Initialize the agent (load model or setup API)."""
        if self.config.use_local:
            return self._init_local()
        else:
            return self._init_api()
    
    def _init_local(self) -> bool:
        """Initialize local model."""
        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM
            import torch
            
            self.logger.info(f"Loading local model: {self.config.model_name}")
            
            self.tokenizer = AutoTokenizer.from_pretrained(self.config.model_name)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.config.model_name,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None,
            )
            
            self._initialized = True
            self.logger.info("Local model loaded successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load local model: {e}")
            return False
    
    def _init_api(self) -> bool:
        """Initialize Hugging Face Inference API."""
        try:
            from huggingface_hub import InferenceClient
            
            api_key = self.config.api_key or os.environ.get("HUGGINGFACE_API_KEY")
            
            self.api_client = InferenceClient(
                model=self.config.model_name,
                token=api_key,
            )
            
            self._initialized = True
            self.logger.info(f"HF API client initialized for {self.config.model_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize HF API: {e}")
            return False
    
    def shutdown(self) -> None:
        """Cleanup resources."""
        self.model = None
        self.tokenizer = None
        self.api_client = None
        self._initialized = False
    
    def _format_prompt(self, company: CompanyData, news: List[NewsArticle]) -> str:
        """Format company data into analysis prompt."""
        # Format historical earnings
        hist_str = ""
        if company.historical_eps:
            for h in company.historical_eps[:4]:
                beat = "BEAT" if h.get("surprise_pct", 0) > 0 else "MISS"
                hist_str += f"  - {h.get('date')}: {beat} by {h.get('surprise_pct', 0):.1f}%\n"
        
        # Format estimate revisions
        rev_str = ""
        if company.estimate_revisions:
            for r in company.estimate_revisions[:5]:
                rev_str += f"  - {r.get('date')}: {r.get('direction').upper()} (${r.get('old_estimate'):.2f} → ${r.get('new_estimate'):.2f})\n"
        
        # Format news
        news_str = ""
        if news:
            for n in news[:10]:
                sent = f"[{n.sentiment_score:+.1f}]" if n.sentiment_score else ""
                news_str += f"  - {n.headline} {sent}\n"
        
        prompt = f"""
## Company Analysis Request

**Company:** {company.company_name} ({company.ticker})
**Sector:** {company.sector} | **Industry:** {company.industry}
**Market Cap:** ${company.market_cap/1e9:.1f}B
**Report Date:** {company.report_date}

### Consensus Estimates
- EPS Estimate: ${company.consensus_eps:.2f}
- Revenue Estimate: ${company.consensus_revenue/1e9:.1f}B
- Number of Analysts: {company.num_analysts}

### Historical Earnings (Last 4 Quarters)
{hist_str if hist_str else "  No historical data available"}
- Beat Rate: {company.beat_rate_4q:.0%} if company.beat_rate_4q else 'N/A'
- Avg Surprise: {company.avg_surprise_4q:.1f}% if company.avg_surprise_4q else 'N/A'

### Recent Estimate Revisions
{rev_str if rev_str else "  No recent revisions"}

### Price Momentum
- Current Price: ${company.current_price:.2f} if company.current_price else 'N/A'
- 5-Day Change: {company.price_change_5d:.1%} if company.price_change_5d else 'N/A'
- 21-Day Change: {company.price_change_21d:.1%} if company.price_change_21d else 'N/A'
- Short Interest: {company.short_interest:.1%} if company.short_interest else 'N/A'

### Recent News Headlines
{news_str if news_str else "  No recent news"}

---
Analyze this company and provide your prediction in the specified JSON format.
"""
        return prompt
    
    def _generate_response(self, prompt: str) -> str:
        """Generate response from model."""
        full_prompt = f"{self.system_prompt}\n\n{prompt}"
        
        if self.config.use_local and self.model:
            return self._generate_local(full_prompt)
        elif self.api_client:
            return self._generate_api(full_prompt)
        else:
            raise RuntimeError("Agent not initialized")
    
    def _generate_local(self, prompt: str) -> str:
        """Generate using local model."""
        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=4096)
        
        if hasattr(self.model, 'device'):
            inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
        
        outputs = self.model.generate(
            **inputs,
            max_new_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            do_sample=True,
            pad_token_id=self.tokenizer.eos_token_id,
        )
        
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extract only the new generated part
        if prompt in response:
            response = response[len(prompt):]
        
        return response.strip()
    
    def _generate_api(self, prompt: str) -> str:
        """Generate using Hugging Face Inference API."""
        response = self.api_client.text_generation(
            prompt,
            max_new_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            return_full_text=False,
        )
        
        return response.strip()
    
    def _parse_response(self, response: str) -> AgentResponse:
        """Parse JSON response from model."""
        # Try to extract JSON from response
        json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
        
        if json_match:
            try:
                data = json.loads(json_match.group())
                
                # Parse direction
                dir_str = data.get("direction", "meet").lower()
                if "beat" in dir_str:
                    direction = PredictionDirection.BEAT
                elif "miss" in dir_str:
                    direction = PredictionDirection.MISS
                else:
                    direction = PredictionDirection.MEET
                
                return AgentResponse(
                    direction=direction,
                    confidence=float(data.get("confidence", 50)) / 100,
                    reasoning=data.get("reasoning", ""),
                    bull_factors=data.get("bull_factors", []),
                    bear_factors=data.get("bear_factors", []),
                    key_signals=data.get("key_signals", {}),
                    raw_response=response,
                )
                
            except json.JSONDecodeError:
                pass
        
        # Fallback: return default response
        self.logger.warning("Failed to parse agent response, using defaults")
        return AgentResponse(
            direction=PredictionDirection.MEET,
            confidence=0.5,
            reasoning="Unable to parse response",
            bull_factors=[],
            bear_factors=[],
            key_signals={},
            raw_response=response,
        )
    
    def analyze(
        self,
        company: CompanyData,
        news: List[NewsArticle]
    ) -> AgentResponse:
        """
        Analyze company and return prediction.
        
        Args:
            company: CompanyData to analyze
            news: Recent news articles
            
        Returns:
            AgentResponse with prediction
        """
        if not self._initialized:
            raise RuntimeError("Agent not initialized. Call initialize() first.")
        
        prompt = self._format_prompt(company, news)
        response = self._generate_response(prompt)
        
        return self._parse_response(response)


# ============================================================================
# SPECIALIZED AGENTS
# ============================================================================

class BullAgent(HuggingFaceAgent):
    """Bull Agent - Advocates for earnings BEAT."""
    
    def __init__(self, config: AgentConfig):
        super().__init__(config, BULL_PROMPT)


class BearAgent(HuggingFaceAgent):
    """Bear Agent - Advocates for earnings MISS."""
    
    def __init__(self, config: AgentConfig):
        super().__init__(config, BEAR_PROMPT)


class QuantAgent(HuggingFaceAgent):
    """Quant Agent - Objective quantitative analysis."""
    
    def __init__(self, config: AgentConfig):
        super().__init__(config, QUANT_PROMPT)


class ConsensusAgent(HuggingFaceAgent):
    """Consensus Agent - Synthesizes debate and makes final call."""
    
    def __init__(self, config: AgentConfig):
        super().__init__(config, CONSENSUS_PROMPT)
    
    def synthesize(
        self,
        company: CompanyData,
        bull_response: AgentResponse,
        bear_response: AgentResponse,
        quant_response: AgentResponse
    ) -> AgentResponse:
        """
        Synthesize the three agent responses into final prediction.
        
        Args:
            company: Company being analyzed
            bull_response: Bull agent's analysis
            bear_response: Bear agent's analysis
            quant_response: Quant agent's analysis
            
        Returns:
            Final consensus AgentResponse
        """
        synthesis_prompt = f"""
## Synthesis Request for {company.ticker}

### BULL AGENT ANALYSIS
- Direction: {bull_response.direction.value.upper()}
- Confidence: {bull_response.confidence:.0%}
- Reasoning: {bull_response.reasoning}
- Key Factors: {', '.join(bull_response.bull_factors[:3])}

### BEAR AGENT ANALYSIS
- Direction: {bear_response.direction.value.upper()}
- Confidence: {bear_response.confidence:.0%}
- Reasoning: {bear_response.reasoning}
- Key Factors: {', '.join(bear_response.bear_factors[:3])}

### QUANT AGENT ANALYSIS
- Direction: {quant_response.direction.value.upper()}
- Confidence: {quant_response.confidence:.0%}
- Reasoning: {quant_response.reasoning}
- Key Signals: {json.dumps(quant_response.key_signals)}

---
Based on this debate, provide your FINAL consensus prediction.
Weigh the evidence and make a decisive call.
"""
        
        response = self._generate_response(synthesis_prompt)
        return self._parse_response(response)


# ============================================================================
# MULTI-AGENT ORCHESTRATOR
# ============================================================================

class ThreeAgentSystem:
    """
    Orchestrates the three-agent prediction workflow.
    
    Workflow:
    1. Bull, Bear, and Quant agents analyze independently
    2. Consensus agent synthesizes all viewpoints
    3. Final prediction with full reasoning trace
    
    Usage:
        config = AgentConfig(model_name="mistralai/Mistral-7B-Instruct-v0.2")
        system = ThreeAgentSystem(config)
        system.initialize()
        
        prediction = system.predict(company_data, news)
        print(f"Prediction: {prediction.direction} ({prediction.confidence:.0%})")
        
        system.shutdown()
    """
    
    def __init__(self, config: AgentConfig, enable_rebuttals: bool = False):
        self.config = config
        self.enable_rebuttals = enable_rebuttals
        self.logger = logging.getLogger(self.__class__.__name__)
        
        self.bull_agent: Optional[BullAgent] = None
        self.bear_agent: Optional[BearAgent] = None
        self.quant_agent: Optional[QuantAgent] = None
        self.consensus_agent: Optional[ConsensusAgent] = None
    
    def initialize(self) -> None:
        """Initialize all four agents."""
        self.logger.info("Initializing three-agent system...")
        
        self.bull_agent = BullAgent(self.config)
        self.bear_agent = BearAgent(self.config)
        self.quant_agent = QuantAgent(self.config)
        self.consensus_agent = ConsensusAgent(self.config)
        
        self.bull_agent.initialize()
        self.bear_agent.initialize()
        self.quant_agent.initialize()
        self.consensus_agent.initialize()
        
        self.logger.info("All agents initialized")
    
    def shutdown(self) -> None:
        """Shutdown all agents."""
        if self.bull_agent:
            self.bull_agent.shutdown()
        if self.bear_agent:
            self.bear_agent.shutdown()
        if self.quant_agent:
            self.quant_agent.shutdown()
        if self.consensus_agent:
            self.consensus_agent.shutdown()
        
        self.logger.info("All agents shut down")
    
    def predict(
        self,
        company: CompanyData,
        news: List[NewsArticle],
        prediction_date: Optional[date] = None
    ) -> EarningsPrediction:
        """
        Run full three-agent prediction.
        
        Args:
            company: Company data to analyze
            news: Recent news articles
            prediction_date: Date of prediction (default: today)
            
        Returns:
            EarningsPrediction with full debate record
        """
        prediction_date = prediction_date or date.today()
        
        self.logger.info(f"Starting analysis for {company.ticker}")
        
        # Phase 1: Independent Analysis
        self.logger.info("Phase 1: Independent agent analysis")
        
        bull_response = self.bull_agent.analyze(company, news)
        self.logger.info(f"  Bull: {bull_response.direction.value} ({bull_response.confidence:.0%})")
        
        bear_response = self.bear_agent.analyze(company, news)
        self.logger.info(f"  Bear: {bear_response.direction.value} ({bear_response.confidence:.0%})")
        
        quant_response = self.quant_agent.analyze(company, news)
        self.logger.info(f"  Quant: {quant_response.direction.value} ({quant_response.confidence:.0%})")
        
        # Phase 2: Consensus Synthesis
        self.logger.info("Phase 2: Consensus synthesis")
        
        consensus_response = self.consensus_agent.synthesize(
            company, bull_response, bear_response, quant_response
        )
        
        self.logger.info(
            f"Final: {consensus_response.direction.value.upper()} "
            f"({consensus_response.confidence:.0%})"
        )
        
        # Build debate summary
        debate_summary = f"""
=== THREE-AGENT EARNINGS DEBATE ===

BULL ({bull_response.direction.value.upper()}, {bull_response.confidence:.0%}):
{bull_response.reasoning}

BEAR ({bear_response.direction.value.upper()}, {bear_response.confidence:.0%}):
{bear_response.reasoning}

QUANT ({quant_response.direction.value.upper()}, {quant_response.confidence:.0%}):
{quant_response.reasoning}

CONSENSUS ({consensus_response.direction.value.upper()}, {consensus_response.confidence:.0%}):
{consensus_response.reasoning}
"""
        
        return EarningsPrediction(
            ticker=company.ticker,
            company_name=company.company_name,
            report_date=company.report_date,
            prediction_date=prediction_date,
            direction=consensus_response.direction,
            confidence=consensus_response.confidence,
            reasoning_summary=consensus_response.reasoning,
            bull_factors=bull_response.bull_factors,
            bear_factors=bear_response.bear_factors,
            agent_votes={
                "bull": bull_response.direction.value,
                "bear": bear_response.direction.value,
                "quant": quant_response.direction.value,
                "consensus": consensus_response.direction.value,
            },
            debate_summary=debate_summary,
        )
