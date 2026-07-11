# EarningsAgents Codebase Assessment

## 1. Current State: Implementation vs. Stubbed

### Fully Implemented
- **Multi-Agent Orchestration**: The `ThreeAgentSystem` correctly orchestrates parallel agent execution (`BullAgent`, `BearAgent`, `QuantAgent`) using `ThreadPoolExecutor`, feeding into a `ConsensusAgent` (`agents/huggingface_agents.py`). 
- **Data Aggregation**: `DataAggregator` successfully unifies data from Yahoo Finance, FinViz, SEC Edgar (XBRL & transcripts), and AlphaVantage, handling options chain math via `OptionChainAnalyzer` (`data/data_aggregator.py`).
- **Web API**: Built with FastAPI, handling asynchronous generation and cached responses along with SQLite persistence (`api/routers/earnings.py`).

### Stubbed / Incomplete / Failing
- **Brittle JSON Parsing**: `BaseAgent._parse_response()` relies on regex and `ast.literal_eval` to extract JSON from markdown blocks. This code path is fragile and indicates the LLMs frequently fail standard output. 
- **Simulated "Mock" Fallbacks**: If the LLM returns an error (like a 429 API Limit or missing key), `BaseAgent._parse_response` generates a hardcoded, simulated "fake" response (`"LLM API limit reached or key missing. Simulated Quant analysis..."`). This masks actual failures from the runtime but degrades output quality invisibly.
- **Bloomberg Data**: Referenced in `BloombergConfig` but no actual `bloomberg.py` data fetch logic is integrated properly within `data_aggregator.py`, leaving it a stub.

## 2. Architecture Gaps: The Prompting Strategy

### Current Reliance on Zero-Shot Prompting
The system entirely relies on static, zero-shot prompting. `BaseAgent._format_prompt()` bundles all available data (e.g., capping transcripts at 10,000 characters) into one massive string and expects a strict JSON output in one shot. 

### Recommended Upgrade Path
To transition to ReAct-style reasoning and tool use:
1. **Tool-Enabled Context**: Instead of dumping all options data and 10k chars of SEC transcripts upfront, give agents tools like `get_sec_transcript(ticker, quarter)` or `get_options_skew(ticker)`.
2. **ReAct Loop**: Allow agents to output a `thought`, make a `tool_call`, receive the `tool_result`, and only return the structured JSON when confident. 
3. **Structured Outputs**: Deprecate the regex parsing and adopt native `response_format` features (e.g., OpenAI Structured Outputs or Gemini JSON Schema) to strictly define the `AgentResponse` schema.

## 3. Data Layer

### Integrated Sources
- Yahoo Finance (Pricing, historicals, estimates, options)
- Alpha Vantage (News/Sentiment, insider trading fallback)
- SEC EDGAR (XBRL Company Facts, 10-K/10-Q transcripts)
- Finviz (Earnings calendar)
- NewsAPI (Headlines)

### Unpopulated Fields
In the core `CompanyData` struct (`config/settings.py`), the following fields lack a reliable population path from the primary source (Yahoo):
- `report_time`: Defaults to `ReportTime.UNKNOWN` and is rarely populated correctly as Yahoo's calendar often omits BMO/AMC details.
- `fiscal_quarter` and `fiscal_year`: Often remain empty defaults, leading to generic SEC transcript queries that just grab "the latest" rather than the specific relevant quarter.

### Adding a Secondary / Fallback Source
Currently, `DataAggregator` uses a hardcoded, sequential cascade for fallbacks (e.g., `if self.yahoo: ... elif self.alphavantage: ...`). 
**To improve**:
- Implement a `DataSourceChain` or `Strategy` pattern where a method like `get_estimates()` loops through a registered list of `IDataSource` providers until one succeeds. This will make adding a third source (like Financial Modeling Prep) seamless.

## 4. Agent Collaboration Quality

### Current Upstream Input
The `ConsensusAgent.synthesize()` builds a simple markdown template (`synthesis_prompt`) that concatenates the `direction`, `confidence`, `reasoning`, and `key_factors` of the Bull, Bear, and Quant agents. It receives raw text.

### Redesigning for Multi-Round Interaction
To support a dynamic, iterative debate:
1. **Initial Theses**: Execute Bull, Bear, and Quant in parallel to generate initial reports.
2. **Rebuttal Round**: Rerun the Bull and Bear agents, providing them with the exact opposing report. Prompt them to generate a *counter-argument*. 
3. **Quant Scoring**: Feed the rebuttals to the Quant agent to statistically validate the claims of the qualitative agents.
4. **Final Consensus**: The Consensus Agent receives the full conversation history (Thesis -> Rebuttal -> Quant Score) as structured dialogue messages, instead of a flattened summary, enhancing decision depth.

## 5. Feedback and Evaluation Loop

### Current Status
There is absolutely no mechanism to compare predictions against ground truth. The `Prediction` SQLModel (`database/models.py`) only writes forward-looking data. 

### Closing the Loop
**Schema Changes Needed (`database/models.py`)**:
- Extend `Prediction` with:
  - `actual_direction: str` (BEAT/MISS/MEET)
  - `actual_price_move_pct: float`
  - `accuracy_score: float` (e.g., Brier score using the prediction's confidence).

**Pipeline Steps Required**:
1. **Evaluation Job**: A Celery task that runs daily, querying `Prediction` records where `prediction_date < today()` and `actual_direction IS NULL`.
2. **Ground Truth Fetcher**: Query the `DataAggregator` for reported EPS and actual price action.
3. **Scoring**: Compute metrics and store them, enabling a dashboard to visualize which Agent or configuration yields the highest ROI over time.

## 6. Immediate Priorities (Top 5 Ranked)

1. **Implement Native Structured Outputs (JSON Schema)**: Replace the brittle regex parser (`_parse_response`) with provider-native JSON schema functions to eliminate `"Failed to parse agent response"` errors entirely.
2. **Close the Evaluation Loop**: Update `models.py` schema for `actual_direction` and build a ground-truth scorer. Without this, it is impossible to know if the system has alpha.
3. **Enable Tool Calling for Context Lengths**: Instead of injecting 10,000 characters of SEC transcripts, provide a `search_transcript_for_guidance(query)` tool. This fixes context dilution and saves tokens.
4. **Refactor Aggregator Fallback Logic**: Remove the `if self.yahoo: ... elif self.alphavantage` spaghetti. Use a unified `ProviderChain` so new data sources can be snapped in via configuration.
5. **Add a Debate Rebuttal Step**: Modify `ThreeAgentSystem.predict()` to allow a second pass where agents explicitly critique each other before Consensus is reached, unlocking the defining value of multi-agent LLM systems.
