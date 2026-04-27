"""
Multi-Agent System for Earnings Prediction.

Contains:
- BaseAgent: Core logic for interacting with LLMClient
- BullAgent: Advocates for earnings BEAT
- BearAgent: Advocates for earnings MISS
- QuantAgent: Objective quantitative analysis
- ConsensusAgent: Synthesizes debate and makes final call
"""

import json
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
from .llm_client import LLMClient


# ============================================================================
# AGENT RESPONSE STRUCTURE
# ============================================================================

@dataclass
class AgentResponse:
    """Response from an agent analysis."""
    direction: PredictionDirection
    confidence: float
    expected_price_move: str
    move_vs_implied: str
    guidance_expectation: str
    reasoning: str
    bull_factors: List[str]
    bear_factors: List[str]
    key_signals: Dict[str, Any]
    raw_response: str = ""


AGENT_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "direction": {"type": "string"},
        "confidence": {"type": "number"},
        "expected_price_move": {"type": "string"},
        "move_vs_implied": {"type": "string"},
        "guidance_expectation": {"type": "string"},
        "reasoning": {"type": "string"},
        "bull_factors": {"type": "array", "items": {"type": "string"}},
        "bear_factors": {"type": "array", "items": {"type": "string"}},
        "key_signals": {
            "type": "object",
            "properties": {
                "estimate_momentum": {"type": "string"},
                "beat_rate": {"type": "string"},
                "estimate_risk": {"type": "string"},
                "headwinds": {"type": "string"},
                "beat_probability": {"type": "string"},
                "historical_beat_rate": {"type": "string"},
                "revision_trend": {"type": "string"},
                "deciding_factor": {"type": "string"},
                "bull_strength": {"type": "string"},
                "bear_strength": {"type": "string"}
            },
            "required": [
                "estimate_momentum", "beat_rate", "estimate_risk", "headwinds",
                "beat_probability", "historical_beat_rate", "revision_trend",
                "deciding_factor", "bull_strength", "bear_strength"
            ],
            "additionalProperties": False
        }
    },
    "required": [
        "direction", "confidence", "expected_price_move", "move_vs_implied",
        "guidance_expectation", "reasoning", "bull_factors", "bear_factors",
        "key_signals"
    ],
    "additionalProperties": False
}


class AgentResponseError(Exception):
    """Exception raised when an agent fails to generate a valid response."""
    def __init__(self, agent: str, cause: Exception):
        self.agent = agent
        self.cause = cause
        super().__init__(f"{agent} failed to formulate a response: {cause}")


class ConsensusError(Exception):
    """Exception raised when consensus cannot be formed (e.g. not enough agent responses)."""
    pass

# ============================================================================
# SYSTEM PROMPTS FOR EACH AGENT
# ============================================================================

BULL_PROMPT = """You are a BULL analyst specializing in identifying reasons why companies will BEAT earnings expectations.

YOUR MISSION: Find every positive signal that suggests an earnings beat.

ANALYSIS FOCUS:
1. Revenue strength signals (demand, market share, pricing power)
2. Margin improvement indicators (cost savings, operating leverage)
3. Positive estimate revision momentum
4. Management's tone and forward guidance in the Latest Earnings Transcript Snippet
5. Positive sentiment and insider buying

INSTRUCTIONS:
First, provide a brief paragraph explaining your thoughts and reasoning (your "thinking process").
Then, output your final decision in the following exact JSON format, enclosed in a ```json``` code block:
{
    "direction": "BEAT",
    "confidence": <60-95>,
    "expected_price_move": "positive" | "negative" | "neutral",
    "move_vs_implied": "inside implied move" | "exceeds implied move",
    "guidance_expectation": "positive" | "negative" | "neutral",
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
4. Hesitant management tone or defensive posturing in the Latest Earnings Transcript Snippet
5. High expectations that may be hard to meet

INSTRUCTIONS:
First, provide a brief paragraph explaining your thoughts and reasoning (your "thinking process").
Then, output your final decision in the following exact JSON format, enclosed in a ```json``` code block:
{
    "direction": "MISS",
    "confidence": <60-95>,
    "expected_price_move": "positive" | "negative" | "neutral",
    "move_vs_implied": "inside implied move" | "exceeds implied move",
    "guidance_expectation": "positive" | "negative" | "neutral",
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
5. Options market signals (Put/Call ratios, IV Skew, Max Pain, Net Gamma)
6. SEC Company Facts (XBRL) analysis (balance sheet health, margins from revenues vs net income)
7. Statistical probability assessment

INSTRUCTIONS:
First, provide a brief paragraph explaining your thoughts and reasoning (your "thinking process").
Then, output your final decision in the following exact JSON format, enclosed in a ```json``` code block:
{
    "direction": "BEAT" or "MISS" or "MEET",
    "confidence": <50-85>,
    "expected_price_move": "positive" | "negative" | "neutral",
    "move_vs_implied": "inside implied move" | "exceeds implied move",
    "guidance_expectation": "positive" | "negative" | "neutral",
    "reasoning": "<statistical summary with specific numbers>",
    "bull_factors": ["<quantitative positives>"],
    "bear_factors": ["<quantitative negatives>"],
    "key_signals": {"beat_probability": "<X%>", "historical_beat_rate": "<X/Y>", "revision_trend": "<direction>"}
}"""


CONSENSUS_PROMPT = """You are the CONSENSUS analyst responsible for the final earnings prediction.

YOUR MISSION: Synthesize Bull, Bear, Quant, and User (Analyst) analyses to make the optimal prediction.

DECISION FRAMEWORK:
- Recent estimate revisions: 30% weight (most predictive)
- Historical beat/miss pattern: 25% weight
- Quantitative signals: 25% weight
- Qualitative factors (including User Analysis): 20% weight

RULES:
- If Quant aligns with Bull or Bear: Weight Quant heavily
- If estimate revisions are strongly directional: Follow them
- If historical pattern is very consistent: Respect it
- If User (Analyst) analysis provides verified unique insight, incorporate it into final reasoning
- When rebuttals are provided, give extra weight to whichever side successfully refuted the other's weakest argument

INSTRUCTIONS:
First, provide a brief paragraph explaining your thoughts and reasoning (your "thinking process").
Then, output your final decision in the following exact JSON format, enclosed in a ```json``` code block:
{
    "direction": "BEAT" or "MISS" or "MEET",
    "confidence": <50-95>,
    "expected_price_move": "positive" | "negative" | "neutral",
    "move_vs_implied": "inside implied move" | "exceeds implied move",
    "guidance_expectation": "positive" | "negative" | "neutral",
    "reasoning": "<2-3 sentence final decision rationale>",
    "bull_factors": ["<accepted bull points>"],
    "bear_factors": ["<accepted bear points>"],
    "key_signals": {"deciding_factor": "<what tipped decision>", "bull_strength": "<1-10>", "bear_strength": "<1-10>"}
}"""


# Rebuttal prompts — each agent receives the opposing thesis and must respond
BULL_REBUTTAL_PROMPT = """You are a BULL analyst who has just read the Bear analyst's full case against this company.

YOUR MISSION: Critically examine the Bear case and, where it is factually weak or overstated,
provide a specific, evidence-backed counter-argument. Do NOT simply re-state your original thesis.

INSTRUCTIONS:
- Acknowledge any Bear points you genuinely cannot refute.
- Challenge Bear points that rely on speculation, outdated data, or ignore positive signals.
- Output your rebuttal in the following exact JSON format, enclosed in a ```json``` code block:
{
    "direction": "BEAT",
    "confidence": <60-95>,
    "expected_price_move": "positive" | "negative" | "neutral",
    "move_vs_implied": "inside implied move" | "exceeds implied move",
    "guidance_expectation": "positive" | "negative" | "neutral",
    "reasoning": "<2-3 sentence rebuttal focused on weaknesses in the Bear case>",
    "bull_factors": ["<strongest surviving bull points after Bear cross-examination>"],
    "bear_factors": ["<Bear risks you concede are valid>"],
    "key_signals": {"estimate_momentum": "<detail>", "beat_rate": "<detail>"}
}"""


BEAR_REBUTTAL_PROMPT = """You are a BEAR analyst who has just read the Bull analyst's full case for this company.

YOUR MISSION: Critically examine the Bull case and, where it is optimistic, unsubstantiated, or
overlooks key risks, provide a specific, evidence-backed counter-argument. Do NOT simply re-state
your original thesis.

INSTRUCTIONS:
- Acknowledge any Bull points that are genuinely strong and hard to refute.
- Challenge Bull points that rely on momentum alone, ignore macro risks, or project unrealistically.
- Output your rebuttal in the following exact JSON format, enclosed in a ```json``` code block:
{
    "direction": "MISS",
    "confidence": <60-95>,
    "expected_price_move": "positive" | "negative" | "neutral",
    "move_vs_implied": "inside implied move" | "exceeds implied move",
    "guidance_expectation": "positive" | "negative" | "neutral",
    "reasoning": "<2-3 sentence rebuttal focused on weaknesses in the Bull case>",
    "bull_factors": ["<Bull strengths you concede are valid>"],
    "bear_factors": ["<strongest surviving bear risks after Bull cross-examination>"],
    "key_signals": {"estimate_risk": "<detail>", "headwinds": "<detail>"}
}"""


# ============================================================================
# BASE AGENT CLASS
# ============================================================================

class BaseAgent:
    """Base agent using LLMClient for analysis."""
    
    def __init__(self, config: AgentConfig, system_prompt: str):
        self.config = config
        self.system_prompt = system_prompt
        self.logger = logging.getLogger(self.__class__.__name__)
        self.llm = LLMClient(
            api_key=config.api_key,
            provider=config.provider,
            model=config.model_name
        )
    
    def initialize(self) -> bool:
        """Initialize the agent."""
        # LLMClient handles initialization internally
        return True
    
    def shutdown(self) -> None:
        """Cleanup resources."""
        pass
    
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
                rev_str += f"  - {r.get('date')}: {r.get('direction').upper()} (${r.get('old_estimate', 0):.2f} → ${r.get('new_estimate', 0):.2f})\n"
        
        # Format news
        news_str = ""
        if news:
            for n in news[:10]:
                sent = f"[{n.sentiment_score:+.1f}]" if n.sentiment_score else ""
                news_str += f"  - {n.headline} {sent}\n"
        
        # Market Cap formatting
        mc_val = company.market_cap / 1e9 if company.market_cap else 0
        
        # Options formatting
        options_str = ""
        if company.options_features:
            features = company.options_features
            pc_ratio = features.get('put_call_volume_ratio')
            if pc_ratio is not None and str(pc_ratio).lower() != 'nan':
                options_str += f"  - Put/Call Vol Ratio: {pc_ratio:.2f}x\n"
            iv_skew = features.get('iv_skew')
            if iv_skew is not None and str(iv_skew).lower() != 'nan':
                options_str += f"  - IV Skew (OTM Put - Call): {iv_skew:.4f}\n"
            net_gamma = features.get('net_gamma_exposure')
            if net_gamma is not None and str(net_gamma).lower() != 'nan':
                options_str += f"  - Net Gamma Exposure: {net_gamma:.2f}\n"
            max_pain = features.get('max_pain_to_spot')
            if max_pain is not None and str(max_pain).lower() != 'nan':
                options_str += f"  - Max Pain to Spot Ratio: {max_pain:.4f}\n"
            if not options_str:
                options_str = "  No significant options data\n"
        
        # Transcript formatting
        transcript_str = ""
        if hasattr(company, 'recent_transcripts') and company.recent_transcripts:
            latest_t = company.recent_transcripts[0]
            transcript_str = f"  - Year/Quarter: {latest_t.get('year')}/{latest_t.get('quarter')}\n"
            transcript_str += f"  - Transcript Snippet: {latest_t.get('transcript', '')[:5000]}\n"
            
        # Facts formatting
        facts_str = ""
        if hasattr(company, 'company_facts') and company.company_facts:
            facts_str = "  (Latest SEC XBRL filings)\n"
            for fact_name, fact_data in company.company_facts.items():
                val = fact_data.get('value', 0)
                # format millions/billions
                if val >= 1e9:
                    val_fmt = f"${val/1e9:.2f}B"
                elif val >= 1e6:
                    val_fmt = f"${val/1e6:.2f}M"
                else:
                    val_fmt = f"${val:,.0f}"
                facts_str += f"  - {fact_name}: {val_fmt} (as of {fact_data.get('period_end')} via {fact_data.get('form')})\n"
        
        prompt = f"""
## Company Analysis Request

**Company:** {company.company_name} ({company.ticker})
**Sector:** {company.sector} | **Industry:** {company.industry}
**Market Cap:** ${mc_val:.1f}B
**Report Date:** {company.report_date}

### Consensus Estimates
- EPS Estimate: ${company.consensus_eps:.2f}
- Revenue Estimate: ${company.consensus_revenue/1e9 if company.consensus_revenue else 0:.1f}B
- Number of Analysts: {company.num_analysts}

### Historical Earnings (Last 4 Quarters)
{hist_str if hist_str else "  No historical data available"}
- Beat Rate: {f"{company.beat_rate_4q:.0%}" if company.beat_rate_4q is not None else "N/A"}
- Avg Surprise: {f"{company.avg_surprise_4q:.1f}%" if company.avg_surprise_4q is not None else "N/A"}

### Recent Estimate Revisions
{rev_str if rev_str else "  No recent revisions"}

### Price Momentum
- Current Price: {f"${company.current_price:.2f}" if company.current_price is not None else "N/A"}
- 5-Day Change: {f"{company.price_change_5d:.1%}" if company.price_change_5d is not None else "N/A"}
- 21-Day Change: {f"{company.price_change_21d:.1%}" if company.price_change_21d is not None else "N/A"}
- Short Interest: {f"{company.short_interest:.1%}" if company.short_interest is not None else "N/A"}

### Options Market Signals
{options_str if options_str else "  No options data available"}

### Recent News Headlines
{news_str if news_str else "  No recent news"}

### Recent SEC Company Facts (XBRL)
{facts_str if facts_str else "  No recent facts available"}

### Latest Earnings Transcript Snippet
{transcript_str if transcript_str else "  No transcript available"}

---
Analyze this company and provide your prediction in the specified JSON format.
"""
        return prompt
    
    def _get_llm_kwargs(self) -> dict:
        """Get provider-specific formatting instructions to enforce JSON Schema outputs."""
        kwargs = {}
        if self.config.provider == "openai":
            kwargs["response_format"] = {
                "type": "json_schema", 
                "json_schema": {"name": "AgentResponse", "strict": True, "schema": AGENT_RESPONSE_SCHEMA}
            }
        elif self.config.provider == "anthropic":
            kwargs["tools"] = [{
                "name": "AgentResponse",
                "description": "Output the final prediction",
                "input_schema": AGENT_RESPONSE_SCHEMA
            }]
            kwargs["tool_choice"] = {"type": "tool", "name": "AgentResponse"}
        elif self.config.provider == "gemini":
            kwargs["generation_config"] = {
                "response_mime_type": "application/json",
                "response_schema": AGENT_RESPONSE_SCHEMA
            }
        return kwargs
    
    def _build_react_system_prompt(self, tool_descriptions: List[dict]) -> str:
        """Build a ReAct-style system prompt by appending a protocol block to self.system_prompt.

        Args:
            tool_descriptions: List of tool descriptor dicts, each with at minimum
                               a 'name' key and optionally 'description' and 'args'.

        Returns:
            The combined system prompt with the ReAct protocol appended.
        """
        # Serialise the tool list for injection into the prompt
        tools_json = json.dumps(tool_descriptions, indent=2)

        # Build the final_answer schema summary for the prompt
        required_fields = AGENT_RESPONSE_SCHEMA.get("required", [])
        schema_summary = json.dumps(
            {field: AGENT_RESPONSE_SCHEMA["properties"][field] for field in required_fields},
            indent=2,
        )

        react_block = f"""

================================================================================
REACT PROTOCOL — STRICT JSON OUTPUT REQUIRED
================================================================================

On EVERY turn you must output ONLY valid JSON — no markdown, no prose, no
explanations outside the JSON value fields.  Choose exactly one of the two
formats below:

1. TOOL CALL — when you need to invoke a tool:
{{
  "thought": "<your internal reasoning, 1-3 sentences>",
  "tool": "<tool_name>",
  "args": {{<optional key-value arguments>}}
}}

2. FINAL ANSWER — when you have gathered enough information to conclude:
{{
  "thought": "<your final reasoning, 1-3 sentences>",
  "final_answer": {{
    <AgentResponse fields — see schema below>
  }}
}}

RULES:
- Never mix plain text with JSON.  The entire response must be parseable JSON.
- Do NOT include any text before or after the JSON object.
- Always call `get_company_summary` FIRST to orient yourself before any other tool.
- After `get_company_summary`, call 2–4 additional tools as appropriate, then
  return a `final_answer`.
- The `final_answer` object must conform EXACTLY to the following schema:
{schema_summary}

AVAILABLE TOOLS:
{tools_json}

When selecting tools, prefer tools that provide data you have not yet seen.
Stop calling tools once you have enough information to form a confident prediction.
================================================================================
"""
        return self.system_prompt + react_block

    def _react_analyze(
        self,
        company: CompanyData,
        news: List[NewsArticle],
        max_turns: int = 6,
    ) -> AgentResponse:
        """Run a ReAct tool-use loop and return a parsed AgentResponse.

        The loop:
        1. Builds a tool registry over the already-fetched company/news data.
        2. Constructs a ReAct system prompt via _build_react_system_prompt.
        3. Seeds the conversation with a minimal framing message.
        4. On each turn:
           - Calls self.llm.chat to get the next model turn.
           - Parses the JSON response.
           - If it contains "final_answer", parses and returns it.
           - If it contains "tool", dispatches the tool and injects the result
             back as a user message.
           - Otherwise raises AgentResponseError.
        5. Raises AgentResponseError if max_turns is exhausted without a
           final_answer.

        Parameters
        ----------
        company : CompanyData
            Pre-fetched company snapshot.
        news : List[NewsArticle]
            Pre-fetched news articles.
        max_turns : int
            Maximum number of LLM turns before giving up (default 6).

        Returns
        -------
        AgentResponse
            Parsed and validated agent prediction.
        """
        from .agent_tools import AgentToolRegistry

        # 1. Build registry and tool descriptions
        registry = AgentToolRegistry(company, news)
        tool_descriptions = registry.get_tool_descriptions()

        # 2. Build ReAct system prompt
        react_system_prompt = self._build_react_system_prompt(tool_descriptions)

        # 3. Initial user message — minimal context only
        report_date_str = (
            company.report_date.isoformat() if company.report_date else "unknown"
        )
        initial_user_message = (
            f"Ticker: {company.ticker}\n"
            f"Company: {company.company_name}\n"
            f"Report Date: {report_date_str}\n"
            f"Consensus EPS Estimate: ${company.consensus_eps:.2f}\n\n"
            "Analyze this company's earnings outlook. Use the available tools to "
            "gather the data you need, then return your final_answer."
        )

        messages = [{"role": "user", "content": initial_user_message}]

        # 4. ReAct loop
        for turn in range(max_turns):
            response = self.llm.chat(
                system_prompt=react_system_prompt,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )

            # Append assistant turn to history
            messages.append({"role": "assistant", "content": response})

            # Parse the response — must be valid JSON
            try:
                parsed = json.loads(response)
            except json.JSONDecodeError as exc:
                raise AgentResponseError(
                    agent=self.__class__.__name__,
                    cause=exc,
                )

            # --- Branch: final answer ---
            if "final_answer" in parsed:
                return self._parse_response(json.dumps(parsed["final_answer"]))

            # --- Branch: tool call ---
            if "tool" in parsed:
                tool_name = parsed["tool"]
                tool_args = parsed.get("args", {}) or {}

                tool_result: "ToolResult" = registry.dispatch(tool_name, tool_args)

                # Build tool result message and inject as next user turn
                tool_result_msg = {
                    "tool_result": {
                        "tool": tool_name,
                        "data": tool_result.result if tool_result.error is None
                        else {"error": tool_result.error},
                    }
                }
                messages.append(
                    {"role": "user", "content": json.dumps(tool_result_msg, default=str)}
                )
                continue

            # --- Branch: unexpected format ---
            raise AgentResponseError(
                agent=self.__class__.__name__,
                cause=Exception("Unexpected response format"),
            )

        # Exhausted all turns without a final_answer
        raise AgentResponseError(
            agent=self.__class__.__name__,
            cause=Exception(
                "ReAct loop exceeded max_turns without producing final_answer"
            ),
        )

    def analyze(
        self,
        company: CompanyData,
        news: List[NewsArticle],
        stream_callback=None,
        status_callback=None,
        use_react: Optional[bool] = None,
    ) -> AgentResponse:
        """Analyze company and return prediction.

        Parameters
        ----------
        company : CompanyData
            Pre-fetched company snapshot.
        news : List[NewsArticle]
            Pre-fetched news articles.
        stream_callback : callable, optional
            Token-level streaming callback (single-shot path only).
        status_callback : callable, optional
            Status/retry callback (single-shot path only).
        use_react : bool or None
            When True, delegate to _react_analyze() which runs the full
            ReAct tool-use loop. stream_callback and status_callback are
            ignored in this mode.
            When None (default), the value is read from ``self.config.use_react``,
            allowing the flag to be set once at configuration time rather than
            at every call site.
        """
        # Resolve: explicit override > config default
        _use_react = self.config.use_react if use_react is None else use_react
        max_turns = getattr(self.config, "react_max_turns", 6)

        # --- ReAct path ---
        if _use_react:
            return self._react_analyze(company, news, max_turns=max_turns)

        # --- Existing single-shot path (unchanged) ---
        prompt = self._format_prompt(company, news)
        kwargs = self._get_llm_kwargs()
        try:
            if stream_callback:
                full_response = ""
                for chunk in self.llm.generate_stream(
                    system_prompt=self.system_prompt,
                    user_prompt=prompt,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    on_retry=status_callback,
                    **kwargs
                ):
                    full_response += chunk
                    stream_callback(chunk)
                return self._parse_response(full_response)
            
            response = self.llm.generate(
                system_prompt=self.system_prompt,
                user_prompt=prompt,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                on_retry=status_callback,
                **kwargs
            )
            return self._parse_response(response)
        except Exception as e:
            raise AgentResponseError(agent=self.__class__.__name__, cause=e)
    
    def _parse_response(self, response: str) -> AgentResponse:
        """Parse JSON response from model directly into typed AgentResponse."""
        try:
            data = json.loads(response)

            # --- 1. Validate required top-level keys ---
            required_keys = AGENT_RESPONSE_SCHEMA["required"]
            missing = [k for k in required_keys if k not in data]
            if missing:
                raise AgentResponseError(
                    agent=self.__class__.__name__,
                    cause=Exception(
                        f"Response missing required keys: {missing}"
                    ),
                )

            # --- 2. Validate and clamp confidence ---
            raw_confidence = data["confidence"]
            try:
                confidence = float(raw_confidence)
            except (TypeError, ValueError):
                self.logger.warning(
                    "confidence value %r is not numeric; clamping to 0.", raw_confidence
                )
                confidence = 0.0
            if not (0 <= confidence <= 100):
                clamped = max(0.0, min(100.0, confidence))
                self.logger.warning(
                    "confidence %s is out of [0, 100]; clamping to %s.", confidence, clamped
                )
                confidence = clamped

            # --- 3. Validate direction ---
            dir_str = str(data["direction"]).lower().strip()
            _VALID_DIRECTIONS = {"beat", "miss", "meet"}
            if dir_str not in _VALID_DIRECTIONS:
                raise AgentResponseError(
                    agent=self.__class__.__name__,
                    cause=Exception(
                        f"Invalid direction {data['direction']!r}; must be one of {sorted(_VALID_DIRECTIONS)}."
                    ),
                )
            direction_map = {
                "beat": PredictionDirection.BEAT,
                "miss": PredictionDirection.MISS,
                "meet": PredictionDirection.MEET,
            }
            direction = direction_map[dir_str]

            return AgentResponse(
                direction=direction,
                confidence=confidence,
                expected_price_move=data.get("expected_price_move", "neutral"),
                move_vs_implied=data.get("move_vs_implied", "inside implied move"),
                guidance_expectation=data.get("guidance_expectation", "neutral"),
                reasoning=data.get("reasoning", ""),
                bull_factors=data.get("bull_factors", []),
                bear_factors=data.get("bear_factors", []),
                key_signals=data.get("key_signals", {}),
                raw_response=response,
            )
        except AgentResponseError:
            raise
        except Exception as e:
            raise AgentResponseError(agent=self.__class__.__name__, cause=e)

    def rebuttal_analyze(
        self,
        company: CompanyData,
        news: List[NewsArticle],
        opposing_response: "AgentResponse",
        rebuttal_system_prompt: str,
        stream_callback=None,
        status_callback=None,
    ) -> "AgentResponse":
        """Run a rebuttal pass given the full text of the opposing agent's thesis.

        Builds a prompt that presents the original company context *and* the
        opposing thesis, then asks the agent to specifically counter it.

        Parameters
        ----------
        company : CompanyData
        news : List[NewsArticle]
        opposing_response : AgentResponse
            The fully-parsed response from the opposing agent.
        rebuttal_system_prompt : str
            Role-specific rebuttal system prompt (BULL_REBUTTAL_PROMPT or
            BEAR_REBUTTAL_PROMPT).
        stream_callback, status_callback : callable, optional
        """
        base_context = self._format_prompt(company, news)

        opposing_desc = (
            f"Direction: {opposing_response.direction.value.upper()}\n"
            f"Confidence: {opposing_response.confidence:.0f}%\n"
            f"Reasoning: {opposing_response.reasoning}\n"
            f"Key bull factors: {', '.join(opposing_response.bull_factors[:5])}\n"
            f"Key bear factors: {', '.join(opposing_response.bear_factors[:5])}"
        )

        rebuttal_prompt = (
            base_context
            + "\n\n---\n## OPPOSING ANALYST THESIS — CROSS-EXAMINE THIS CAREFULLY\n\n"
            + opposing_desc
            + "\n\n---\nNow provide your rebuttal in the required JSON format."
        )

        kwargs = self._get_llm_kwargs()
        try:
            if stream_callback:
                full_response = ""
                for chunk in self.llm.generate_stream(
                    system_prompt=rebuttal_system_prompt,
                    user_prompt=rebuttal_prompt,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    on_retry=status_callback,
                    **kwargs,
                ):
                    full_response += chunk
                    stream_callback(chunk)
                return self._parse_response(full_response)

            response = self.llm.generate(
                system_prompt=rebuttal_system_prompt,
                user_prompt=rebuttal_prompt,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                on_retry=status_callback,
                **kwargs,
            )
            return self._parse_response(response)
        except Exception as e:
            raise AgentResponseError(agent=self.__class__.__name__, cause=e)


class BullAgent(BaseAgent):
    """Bull Agent - Advocates for earnings BEAT."""
    def __init__(self, config: AgentConfig):
        super().__init__(config, BULL_PROMPT)


class BearAgent(BaseAgent):
    """Bear Agent - Advocates for earnings MISS."""
    def __init__(self, config: AgentConfig):
        super().__init__(config, BEAR_PROMPT)


class QuantAgent(BaseAgent):
    """Quant Agent - Objective quantitative analysis."""
    def __init__(self, config: AgentConfig):
        super().__init__(config, QUANT_PROMPT)


class ConsensusAgent(BaseAgent):
    """Consensus Agent - Synthesizes debate and makes final call."""

    def __init__(self, config: AgentConfig):
        super().__init__(config, CONSENSUS_PROMPT)

    def synthesize(
        self,
        company: CompanyData,
        bull_response: Optional[AgentResponse] = None,
        bear_response: Optional[AgentResponse] = None,
        quant_response: Optional[AgentResponse] = None,
        user_analysis: Optional[str] = None,
        stream_callback=None,
        status_callback=None,
        bull_rebuttal: Optional[AgentResponse] = None,
        bear_rebuttal: Optional[AgentResponse] = None,
    ) -> AgentResponse:
        """Synthesize agent responses (and optional rebuttals) into a final prediction."""
        successful_agents = []
        if bull_response:
            successful_agents.append("BULL")
        if bear_response:
            successful_agents.append("BEAR")
        if quant_response:
            successful_agents.append("QUANT")

        absent_agents = [a for a in ["BULL", "BEAR", "QUANT"] if a not in successful_agents]
        if absent_agents:
            self.logger.warning(f"Consensus proceeding without {', '.join(absent_agents)}.")

        if len(successful_agents) < 2:
            raise ConsensusError(
                f"Cannot form consensus. Fewer than 2 agents succeeded. Absent: {', '.join(absent_agents)}"
            )

        def _fmt(label: str, resp: Optional[AgentResponse], factors_key: str) -> str:
            if resp is None:
                return f"\n### {label}\n- Status: FAILED TO RESPOND - EXCLUDE FROM CONSIDERATION\n"
            factors = getattr(resp, factors_key, [])[:3]
            return (
                f"\n### {label}\n"
                f"- Direction: {resp.direction.value.upper()}\n"
                f"- Confidence: {resp.confidence:.0f}%\n"
                f"- Reasoning: {resp.reasoning}\n"
                f"- Key Factors: {', '.join(factors)}\n"
            )

        bull_section  = _fmt("BULL AGENT — INITIAL THESIS", bull_response, "bull_factors")
        bear_section  = _fmt("BEAR AGENT — INITIAL THESIS", bear_response, "bear_factors")
        quant_section = _fmt("QUANT AGENT ANALYSIS",        quant_response, "bull_factors")

        rebuttal_section = ""
        if bull_rebuttal or bear_rebuttal:
            rebuttal_section = "\n---\n## REBUTTAL ROUND\n"
            if bull_rebuttal:
                rebuttal_section += _fmt(
                    "BULL REBUTTAL (response to Bear thesis)", bull_rebuttal, "bull_factors"
                )
            if bear_rebuttal:
                rebuttal_section += _fmt(
                    "BEAR REBUTTAL (response to Bull thesis)", bear_rebuttal, "bear_factors"
                )

        user_analysis_section = ""
        if user_analysis:
            user_analysis_section = (
                f"\n### ANALYST (USER PROVIDED) ANALYSIS\n- Analysis: {user_analysis}\n"
            )

        synthesis_prompt = (
            f"## Synthesis Request for {company.ticker}\n"
            f"{bull_section}{bear_section}{quant_section}"
            f"{rebuttal_section}{user_analysis_section}"
            f"\n---\nBased on this {'multi-round debate' if rebuttal_section else 'debate'}, "
            "provide your FINAL consensus prediction. Weigh the evidence and make a decisive call."
        )

        kwargs = self._get_llm_kwargs()
        try:
            if stream_callback:
                full_response = ""
                for chunk in self.llm.generate_stream(
                    system_prompt=self.system_prompt,
                    user_prompt=synthesis_prompt,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    on_retry=status_callback,
                    **kwargs,
                ):
                    full_response += chunk
                    stream_callback(chunk)
                return self._parse_response(full_response)

            response = self.llm.generate(
                system_prompt=self.system_prompt,
                user_prompt=synthesis_prompt,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                on_retry=status_callback,
                **kwargs,
            )
            return self._parse_response(response)
        except Exception as e:
            raise AgentResponseError(agent=self.__class__.__name__, cause=e)


    def chat(self, messages: List[Dict[str, str]]) -> str:
        """Interact with the Consensus Agent regarding its analysis."""
        chat_prompt = """You are the CONSENSUS analyst. The user is asking you questions about your recent earnings prediction.
Please respond directly to the user as an informed analyst. Be concise, objective, and reference the bull, bear, and quant analyses where relevant."""
        
        response = self.llm.chat(
            system_prompt=chat_prompt,
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens
        )
        return response


# ============================================================================
# MULTI-AGENT ORCHESTRATOR
# ============================================================================

class ThreeAgentSystem:
    """Orchestrates the three-agent prediction workflow."""
    
    def __init__(self, config: AgentConfig, enable_rebuttals: bool = False):
        self.config = config
        self.enable_rebuttals = enable_rebuttals
        self.logger = logging.getLogger(self.__class__.__name__)
        
        self.bull_agent = BullAgent(config)
        self.bear_agent = BearAgent(config)
        self.quant_agent = QuantAgent(config)
        self.consensus_agent = ConsensusAgent(config)
    
    def initialize(self) -> None:
        """Initialize all agents."""
        self.bull_agent.initialize()
        self.bear_agent.initialize()
        self.quant_agent.initialize()
        self.consensus_agent.initialize()
    
    def shutdown(self) -> None:
        """Shutdown all agents."""
        pass
    
    def predict(
        self,
        company: CompanyData,
        news: List[NewsArticle],
        prediction_date: Optional[date] = None,
        task_id: Optional[str] = None,
        user_analysis: Optional[str] = None
    ) -> EarningsPrediction:
        """Run full three-agent prediction with optional rebuttal pass.

        Execution flow
        --------------
        Pass 1 (always):
            Bull, Bear, and Quant run in parallel to produce initial theses.

        Pass 2 (when ``self.config.enable_rebuttals`` is True):
            - Bull re-runs against Bear's thesis  (Bull rebuttal)
            - Bear re-runs against Bull's thesis  (Bear rebuttal)
            - Quant serves as statistical referee concurrently with Pass 2.

        Consensus:
            ConsensusAgent receives the full multi-round transcript
            (initial theses + rebuttals, if any) for its final synthesis.

        All intermediate events are published to Redis when task_id is set.
        ReAct tool-loop mode composes with the rebuttal pass — they are
        independent flags that can both be enabled simultaneously.
        """
        from concurrent.futures import ThreadPoolExecutor

        prediction_date = prediction_date or date.today()

        import redis
        import json
        import os
        r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"), socket_timeout=5)

        def publish(msg: str, agent: str = "System", msg_type: str = "status"):
            if task_id:
                try:
                    r.publish(
                        f"task_updates:{task_id}",
                        json.dumps({"status": "RUNNING", "message": msg, "agent": agent, "type": msg_type})
                    )
                except Exception as exc:
                    self.logger.warning(f"Failed to publish to redis: {exc}")

        # --- streaming callbacks (single-shot path) ---
        def get_stream_callback(agent: str):
            def callback(chunk: str):
                publish(chunk, agent, "stream")
            return callback

        def get_status_callback(agent: str):
            def callback(msg: str):
                publish(msg, agent, "status")
            return callback

        # --- ReAct-aware agent wrapper (unchanged from Phase 1) ---
        react_mode = self.config.use_react
        react_max_turns = getattr(self.config, "react_max_turns", 6)
        do_rebuttals = getattr(self.config, "enable_rebuttals", False)

        def run_agent(agent, agent_name: str) -> AgentResponse:
            if react_mode:
                from .agent_tools import AgentToolRegistry
                registry = AgentToolRegistry(company, news)
                original_dispatch = registry.dispatch

                def traced_dispatch(tool_name, tool_args):
                    publish(f"Calling tool: {tool_name}", agent_name, "react_tool")
                    result = original_dispatch(tool_name, tool_args)
                    status = "error" if result.error else "ok"
                    publish(f"Tool {tool_name} → {status}", agent_name, "react_tool_result")
                    return result

                registry.dispatch = traced_dispatch
                tool_descriptions = registry.get_tool_descriptions()
                react_system_prompt = agent._build_react_system_prompt(tool_descriptions)

                report_date_str = (
                    company.report_date.isoformat() if company.report_date else "unknown"
                )
                initial_user_message = (
                    f"Ticker: {company.ticker}\n"
                    f"Company: {company.company_name}\n"
                    f"Report Date: {report_date_str}\n"
                    f"Consensus EPS Estimate: ${company.consensus_eps:.2f}\n\n"
                    "Analyze this company's earnings outlook. Use the available tools to "
                    "gather the data you need, then return your final_answer."
                )
                messages = [{"role": "user", "content": initial_user_message}]

                for turn in range(react_max_turns):
                    publish(f"ReAct turn {turn + 1}/{react_max_turns}", agent_name, "react_turn")
                    response = agent.llm.chat(
                        system_prompt=react_system_prompt,
                        messages=messages,
                        temperature=agent.config.temperature,
                        max_tokens=agent.config.max_tokens,
                    )
                    messages.append({"role": "assistant", "content": response})

                    try:
                        parsed = json.loads(response)
                    except json.JSONDecodeError as exc:
                        raise AgentResponseError(agent=agent.__class__.__name__, cause=exc)

                    if "final_answer" in parsed:
                        publish(f"Final answer reached on turn {turn + 1}", agent_name, "react_done")
                        return agent._parse_response(json.dumps(parsed["final_answer"]))

                    if "tool" in parsed:
                        tool_name = parsed["tool"]
                        tool_args = parsed.get("args", {}) or {}
                        tool_result = traced_dispatch(tool_name, tool_args)
                        tool_result_msg = {
                            "tool_result": {
                                "tool": tool_name,
                                "data": tool_result.result if tool_result.error is None
                                else {"error": tool_result.error},
                            }
                        }
                        messages.append({"role": "user", "content": json.dumps(tool_result_msg, default=str)})
                        continue

                    raise AgentResponseError(
                        agent=agent.__class__.__name__,
                        cause=Exception("Unexpected response format"),
                    )

                raise AgentResponseError(
                    agent=agent.__class__.__name__,
                    cause=Exception("ReAct loop exceeded max_turns without producing final_answer"),
                )
            else:
                return agent.analyze(
                    company,
                    news,
                    stream_callback=get_stream_callback(agent_name),
                    status_callback=get_status_callback(agent_name),
                    use_react=False,
                )

        def run_rebuttal(agent, agent_name: str, opposing: AgentResponse, rebuttal_prompt: str) -> AgentResponse:
            """Run a rebuttal pass for *agent* against *opposing*'s thesis."""
            return agent.rebuttal_analyze(
                company,
                news,
                opposing,
                rebuttal_prompt,
                stream_callback=get_stream_callback(agent_name),
                status_callback=get_status_callback(agent_name),
            )

        # ================================================================
        # PASS 1 — Initial theses (Bull + Bear + Quant in parallel)
        # ================================================================
        self.logger.info(f"Starting analysis for {company.ticker}")
        react_label = "ReAct tool-loop" if react_mode else "single-shot"
        rebuttal_label = " + rebuttal" if do_rebuttals else ""
        publish(
            f"Pass 1: {react_label}{rebuttal_label} analysis for {company.ticker}...",
            "System",
            "status",
        )

        if user_analysis:
            publish(f"User Analyst provided an analysis: {user_analysis[:50]}...", "Analyst", "status")

        import time
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_bull  = executor.submit(run_agent, self.bull_agent,  "Bull")
            time.sleep(2.0)
            future_bear  = executor.submit(run_agent, self.bear_agent,  "Bear")
            time.sleep(2.0)
            future_quant = executor.submit(run_agent, self.quant_agent, "Quant")

            bull_response = None
            try:
                bull_response = future_bull.result()
            except AgentResponseError as e:
                self.logger.error(f"Bull agent error: {e}")
                publish(f"Bull agent failed: {e.cause}", "System", "status")

            bear_response = None
            try:
                bear_response = future_bear.result()
            except AgentResponseError as e:
                self.logger.error(f"Bear agent error: {e}")
                publish(f"Bear agent failed: {e.cause}", "System", "status")

            quant_response = None
            try:
                quant_response = future_quant.result()
            except AgentResponseError as e:
                self.logger.error(f"Quant agent error: {e}")
                publish(f"Quant agent failed: {e.cause}", "System", "status")

        # ================================================================
        # PASS 2 — Rebuttal cross-examination (optional)
        # ================================================================
        bull_rebuttal: Optional[AgentResponse] = None
        bear_rebuttal: Optional[AgentResponse] = None

        if do_rebuttals and bull_response and bear_response:
            publish("Pass 2: Cross-examination rebuttal round starting...", "System", "status")
            with ThreadPoolExecutor(max_workers=2) as executor:
                future_bull_rebuttal = executor.submit(
                    run_rebuttal,
                    self.bull_agent, "Bull-Rebuttal",
                    bear_response, BULL_REBUTTAL_PROMPT,
                )
                time.sleep(1.2)
                future_bear_rebuttal = executor.submit(
                    run_rebuttal,
                    self.bear_agent, "Bear-Rebuttal",
                    bull_response, BEAR_REBUTTAL_PROMPT,
                )

                try:
                    bull_rebuttal = future_bull_rebuttal.result()
                    publish("Bull rebuttal complete.", "Bull-Rebuttal", "status")
                except AgentResponseError as e:
                    self.logger.error(f"Bull rebuttal error: {e}")
                    publish(f"Bull rebuttal failed: {e.cause}", "System", "status")

                try:
                    bear_rebuttal = future_bear_rebuttal.result()
                    publish("Bear rebuttal complete.", "Bear-Rebuttal", "status")
                except AgentResponseError as e:
                    self.logger.error(f"Bear rebuttal error: {e}")
                    publish(f"Bear rebuttal failed: {e.cause}", "System", "status")
        elif do_rebuttals:
            publish(
                "Rebuttal pass skipped: both Bull and Bear required for cross-examination.",
                "System",
                "status",
            )

        # ================================================================
        # CONSENSUS — receives full multi-round transcript
        # ================================================================
        publish("Consensus Agent synthesizing debate for final prediction...", "System", "status")
        try:
            consensus_response = self.consensus_agent.synthesize(
                company,
                bull_response,
                bear_response,
                quant_response,
                user_analysis,
                get_stream_callback("Consensus"),
                get_status_callback("Consensus"),
                bull_rebuttal=bull_rebuttal,
                bear_rebuttal=bear_rebuttal,
            )
        except AgentResponseError as e:
            self.logger.error(f"Consensus agent error: {e}")
            publish(f"Consensus agent failed: {e.cause}", "System", "status")
            raise e
        publish(f"Consensus Reached: {consensus_response.direction.value.upper()}", "System", "status")

        # ================================================================
        # Build debate_summary & rebuttal_summary
        # ================================================================
        def _agent_desc(label: str, resp: Optional[AgentResponse]) -> str:
            if resp is None:
                return f"{label}: FAILED"
            return (
                f"{label} ({resp.direction.value.upper()}, {resp.confidence:.0f}%):\n"
                f"{resp.reasoning}"
            )

        user_summary = f"\n\nANALYST (USER):\n{user_analysis}" if user_analysis else ""
        mode_tag = f"[{react_label}{rebuttal_label}]"

        debate_summary = (
            f"=== AGENTS & USER EARNINGS DEBATE {mode_tag} ===\n\n"
            f"{_agent_desc('BULL', bull_response)}\n\n"
            f"{_agent_desc('BEAR', bear_response)}\n\n"
            f"{_agent_desc('QUANT', quant_response)}"
            f"{user_summary}\n\n"
            f"{_agent_desc('CONSENSUS', consensus_response)}\n"
        )

        rebuttal_summary: Optional[str] = None
        if bull_rebuttal or bear_rebuttal:
            rebuttal_summary = "=== REBUTTAL ROUND ===\n\n"
            if bull_rebuttal:
                rebuttal_summary += (
                    f"BULL REBUTTAL ({bull_rebuttal.direction.value.upper()}, "
                    f"{bull_rebuttal.confidence:.0f}%):  {bull_rebuttal.reasoning}\n\n"
                )
            if bear_rebuttal:
                rebuttal_summary += (
                    f"BEAR REBUTTAL ({bear_rebuttal.direction.value.upper()}, "
                    f"{bear_rebuttal.confidence:.0f}%):  {bear_rebuttal.reasoning}\n"
                )

        return EarningsPrediction(
            ticker=company.ticker,
            company_name=company.company_name,
            report_date=company.report_date,
            prediction_date=prediction_date,
            direction=consensus_response.direction,
            confidence=consensus_response.confidence,
            expected_price_move=consensus_response.expected_price_move,
            move_vs_implied=consensus_response.move_vs_implied,
            guidance_expectation=consensus_response.guidance_expectation,
            reasoning_summary=consensus_response.reasoning,
            bull_factors=bull_response.bull_factors if bull_response else [],
            bear_factors=bear_response.bear_factors if bear_response else [],
            agent_votes={
                "bull":     bull_response.direction.value  if bull_response  else "failed",
                "bear":     bear_response.direction.value  if bear_response  else "failed",
                "quant":    quant_response.direction.value if quant_response else "failed",
                "analyst":  "user_provided" if user_analysis else "none",
                "consensus": consensus_response.direction.value,
            },
            debate_summary=debate_summary,
            rebuttal_summary=rebuttal_summary,
        )


if __name__ == "__main__":
    # Test script for debugging agents directly
    import os
    import sys
    from datetime import date, datetime
    
    # Ensure we can import from the root directory
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from config.settings import load_config, CompanyData, NewsArticle, ReportTime, PredictionDirection
    
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("AgentDebugger")
    
    # 1. Load Config
    config = load_config()
    # Force ReAct mode for testing if desired
    # config.agent.use_react = True 
    
    logger.info(f"Using Provider: {config.agent.provider} | Model: {config.agent.model_name}")
    
    # 2. Mock Data
    mock_company = CompanyData(
        ticker="META",
        company_name="Meta Platforms, Inc.",
        sector="Communication Services",
        industry="Internet Content & Information",
        market_cap=1.2e12,
        report_date=date(2026, 4, 29),
        report_time=ReportTime.AMC,
        consensus_eps=4.32,
        consensus_revenue=36.1e9
    )
    
    mock_news = [
        NewsArticle(
            headline="Meta focusing on AI infrastructure and efficiency",
            source="Financial Times",
            published_at=datetime.now(),
            body="Meta is reducing work force, thus controlling expenses to allocate more resources to AI infrastructure."
        )
    ]
    
    # 3. Run System
    system = ThreeAgentSystem(config.agent)
    system.initialize()
    
    logger.info("Starting prediction run...")
    try:
        prediction = system.predict(
            company=mock_company,
            news=mock_news,
            user_analysis="META is reducing work force, thus controlling expenses to allocate more resources to AI infrastructure. This should help the company medium to long term."
        )
        
        print("\n" + "="*50)
        print(f"PREDICTION FOR {prediction.ticker}")
        print(f"Direction: {prediction.direction.value.upper()}")
        print(f"Confidence: {prediction.confidence*100:.1f}%")
        print(f"Reasoning: {prediction.reasoning_summary[:200]}...")
        print("="*50 + "\n")
        
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
