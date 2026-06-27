# EarningsAgents Development Roadmap

This roadmap outlines the plan to evolve the **EarningsAgents** proof-of-concept (POC) into a comprehensive, production-ready research platform in the coming weeks, fully integrated with different data sources and AI agents, in time for the next earnings season.

---

## 🗺️ Phase-by-Phase Roadmap

```mermaid
timeline
    title EarningsAgents Release Schedule
    section Week 1: Core & LLM Gateway
        Unified LLM Gateway : Add OpenAI, Anthropic, Gemini API failover
        Robust Rate Limiting : Implement token/RPM buckets per LLM provider
    section Week 2: Alternative Data
        SEC Filings Parsing : Extract MD&A & risk factors from 10-K/10-Q
        Option Flow Signals : Integrate contract volume ratios, volatility surfaces
        Web Search Tooling : Add Tavily/Serper APIs for real-time news retrieval
    section Week 3: Interactive Copilot
        Agent Chat Interface : Support multi-turn chat with Bull, Bear, and Quant
        Custom Document Ingestion : Upload PDF press releases and slide decks
    section Week 4: Backtesting & Analytics
        Historical Backtest Engine : Batch-run predictions on past quarters
        Analytics Dashboard : Implement Brier score and accuracy charts
    section Week 5: Scale & Live Deployment
        Docker Orchestration Tuning : Multi-replica workers & Celery monitoring
        Production Cloud Deploy : Integrate Supabase, Upstash, and Clerk prod
```

### 🔹 Week 1: LLM Gateway & Robust Orchestration
**Goal:** Harden the unified LLM interface and backend pipeline to ensure reliable predictions across multiple providers.
*   **Unified LLM Gateway:**
    *   Optimize [LLMClient](file:///c:/Users/alfredo/Project/EarningsAgents/llm_client.py) to support seamless failovers. If the primary LLM provider (e.g. Gemini) encounters a rate limit (429) or transient error, the gateway should fall back dynamically to OpenAI or Anthropic.
    *   Enhance rate-limiting mechanisms using provider-specific tokens-per-minute (TPM) and requests-per-minute (RPM) limits.
*   **Pipeline Reliability:**
    *   Address edge cases where agents fail to respond with the correct JSON schemas by implementing schema-repair prompts and auto-retry parser hooks.

### 🔹 Week 2: Advanced Data Connectors (Alternative & Filing Ingestion)
**Goal:** Expand data sources to provide the AI agents with deep, institutional-grade context.
*   **SEC EDGAR Parsing:**
    *   Upgrade the current [SECEdgarDataSource](file:///c:/Users/alfredo/Project/EarningsAgents/data/sec_edgar.py) to parse full HTML filings rather than just metadata.
    *   Extract the **Management's Discussion & Analysis (MD&A)** and **Risk Factors (Item 1A)** sections.
*   **Options Market Features:**
    *   Enhance option analytics in [OptionsDataSource](file:///c:/Users/alfredo/Project/EarningsAgents/data/options.py) to calculate the volatility skew, ATM IV trends, and call/put open interest ratios.
    *   Provide these options signals directly to the **Quant Agent** for probability-weighted predictions.
*   **Web Search Integration:**
    *   Add a real-time web search tool (using Tavily or Serper API) to the ReAct agent tool loop in [agent_tools.py](file:///c:/Users/alfredo/Project/EarningsAgents/agent_tools.py) to fetch late-breaking company news, earnings whisper data, or pre-announcements.

### 🔹 Week 3: Interactive Agent Copilot & Chat Engine
**Goal:** Empower users to interactively query consensus predictions and interrogate individual agent perspectives.
*   **Multi-Turn Agent Chat Backend:**
    *   Integrate the `@router.post("/chat")` route in [earnings.py](file:///c:/Users/alfredo/Project/EarningsAgents/api/routers/earnings.py) with [PredictionChat](file:///c:/Users/alfredo/Project/EarningsAgents/database/models.py) database records.
    *   Support conversation routing so users can ask specific questions to the **Bull**, **Bear**, or **Quant** agents individually, or call a panel debate.
*   **Next.js Chat UI:**
    *   Build a sleek, real-time chat interface in the frontend dashboard.
    *   Support Markdown rendering, code snippets, and structured tables for financial data returned by the agents.
*   **Custom Document Uploader:**
    *   Add file upload support (PDF, TXT, CSV) so users can upload external analyst reports, slide decks, or custom notes for the agents to ingest as transient context.

### 🔹 Week 4: Backtesting Engine & Performance Analytics Dashboard
**Goal:** Validate prediction accuracy through historical backtests and display performance metrics inside a premium UI.
*   **Backtest Runner:**
    *   Build a CLI and API runner to perform batch historical prediction runs (e.g. predicting Q1 2024 earnings using data available *just prior* to those report dates).
*   **Performance Metrics Endpoint:**
    *   Develop the `/metrics` endpoint in [earnings.py](file:///c:/Users/alfredo/Project/EarningsAgents/api/routers/earnings.py) to compute:
        *   **Hit Rate (Accuracy %):** Percentage of correct Beat/Miss predictions.
        *   **Average Brier Score:** Evaluating forecast confidence calibration.
        *   **Average Implied vs. Actual Price Move:** How well the model identified mispriced options.
*   **Analytics UI Dashboard:**
    *   Add visual graphs (using Recharts) to the history section of the Next.js app to display historical performance and confidence metrics.

### 🔹 Week 5: Scalability, Security, & Production Deployment
**Goal:** Deploy the multi-container stack to a staging environment and prepare for live trading/research.
*   **Orchestration Tuning:**
    *   Configure production Celery settings (e.g., migrating from SQLite/eventlet to Postgres/prefork on Linux servers).
    *   Deploy **Celery Flower** container for monitoring active workers, queue lengths, and task failure rates.
*   **Security & Auth Hardening:**
    *   Configure live Clerk domains and secure JWT validations on the FastAPI backend.
    *   Enforce rate limits on `/predict` and `/chat` routes to prevent API key depletion.
*   **Production Deployment:**
    *   Configure environment variables in AWS/GCP or a VPS server.
    *   Set up automated migrations using Alembic during the release pipeline.

---

## 🎯 POC Success Criteria
To be ready for the upcoming earnings season, the POC must achieve:
1.  **Prediction Accuracy:** Better than 60% hit rate on S&P 500 company earnings directions (Beat/Miss) over a 20-company backtest.
2.  **Reliability:** 0% unhandled task crashes under a batch load of 10 concurrent ticket runs.
3.  **Low Latency:** Average prediction run (including debate and options analysis) under 45 seconds when utilizing fast models like `gemini-1.5-flash` or `gpt-4o-mini`.
4.  **UI Premium Experience:** Real-time WebSockets streaming the debate live in a clean Next.js terminal component.
