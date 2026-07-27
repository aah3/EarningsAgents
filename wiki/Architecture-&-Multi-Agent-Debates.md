# 🏛️ Architecture & Multi-Agent Debates

The **EarningsAgents** framework employs an adversarial, multi-agent debate framework to evaluate upcoming corporate earnings reports. By pitting specialized agents against one another and running rebuttal rounds, the platform combats single-model confirmation bias and delivers well-calibrated probabilistic forecasts.

---

## 👥 The 4 Specialized Agents

```
                        ┌─────────────────────────┐
                        │      Financial Data     │
                        │(Yahoo / SEC / News / AV)│
                        └────────────┬────────────┘
                                     │
         ┌───────────────────────────┼───────────────────────────┐
         ▼                           ▼                           ▼
┌──────────────────┐        ┌──────────────────┐        ┌──────────────────┐
│    BULL AGENT    │        │    BEAR AGENT    │        │   QUANT AGENT    │
│  Advocates BEAT  │        │  Advocates MISS  │        │ Quantitative Data│
└────────┬─────────┘        └────────┬─────────┘        └────────┬─────────┘
         │                           │                           │
         └─────────────┬─────────────┴─────────────┬─────────────┘
                       │                           │
                       ▼                           ▼
         ┌───────────────────────────┐   ┌───────────────────────────┐
         │     Rebuttal Round 1      │   │     Rebuttal Round 2      │
         │  (Cross-Examination)      │   │  (Counter-Argumentation)  │
         └─────────────┬─────────────┘   └─────────────┬─────────────┘
                       │                               │
                       └───────────────┬───────────────┘
                                       ▼
                         ┌───────────────────────────┐
                         │      CONSENSUS AGENT      │
                         │(Synthesizes Vote & Move)  │
                         └─────────────┬─────────────┘
                                       ▼
                       FINAL PREDICTION & BRIER TRACKING
```

### 1. 🐂 Bull Agent (`BullAgent`)
- **Role:** Construct the strongest possible thesis for an earnings **BEAT**.
- **Focus Areas:** Revenue growth momentum, surprise trends over past 4 quarters, expanding margins, product demand catalysts, positive analyst revisions, and upside macro tailwinds.
- **Output:** Bullish confidence percentage, top 3-5 bullish factors, and supporting evidence.

### 2. 🐻 Bear Agent (`BearAgent`)
- **Role:** Construct the strongest possible thesis for an earnings **MISS**.
- **Focus Areas:** Revenue deceleration, margin compression, high short interest, supply chain bottlenecks, rising inventory, macro headwind exposure, downside guidance risk, and rich valuation.
- **Output:** Bearish confidence percentage, top 3-5 bearish factors, and risk flags.

### 3. 📊 Quant Agent (`QuantAgent`)
- **Role:** Provide objective, quantitative assessment unswayed by qualitative narrative.
- **Focus Areas:**
  - **Option Market Implied Move:** ATM straddle pricing around earnings expiration date.
  - **Historical Surprise Distribution:** Mean and standard deviation of EPS/Revenue surprises over the past 8 quarters.
  - **Short Interest & Options Skew:** Put/Call ratio, open interest, and implied volatility (IV) percentile.
- **Output:** Quantitative direction recommendation, options implied move %, and statistical probability metrics.

### 4. ⚖️ Consensus Agent (`ConsensusAgent`)
- **Role:** Act as the impartial judge and synthesizer.
- **Inputs:** Ingests initial reports from Bull, Bear, and Quant agents along with multi-round rebuttal transcripts.
- **Output:**
  - Final prediction direction: `BEAT`, `MISS`, or `MEET`.
  - Confidence percentage ($0-100\%$).
  - Expected stock price move percentage after earnings release.
  - Comprehensive synthesized reasoning summary.

---

## 🔄 The Debate Protocol & Rebuttal Dynamics

1. **Initial Assessment Phase:**
   - Bull, Bear, and Quant agents independently consume company data (fundamentals, SEC filings, financial metrics, options chains, and news).
   - Each agent generates their initial stance and structured evidence packet.

2. **Rebuttal Phase (Cross-Examination):**
   - **Round 1:** The Bull Agent receives the Bear Agent's initial thesis and must specifically refute weak points or over-hyped risks.
   - **Round 2:** The Bear Agent receives the Bull Agent's counter-arguments and identifies blind spots in the bullish narrative.

3. **Synthesis Phase:**
   - The Consensus Agent evaluates the complete transcript: Initial positions + Rebuttal arguments + Quant stats + Optional User Insights.
   - Weighted voting algorithm combines quantitative signals with logical coherence of arguments to produce the final forecast.

---

## 🧠 LLM Client & Multi-Provider Support

The system abstracts LLM interactions through `LLMClient` supporting:
- **Google Gemini:** `gemini-1.5-flash-002`, `gemini-1.5-pro-002`, `gemini-2.0-flash`
- **OpenAI:** `gpt-4o-mini`, `gpt-4o`
- **Anthropic:** `claude-3-5-sonnet`
- **Local LLMs:** Ollama / Local VLLM endpoints when configured via `--local`.
