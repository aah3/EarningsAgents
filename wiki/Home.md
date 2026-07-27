# 📚 Welcome to the EarningsAgents Wiki

Welcome to the official **EarningsAgents** technical documentation and developer knowledge base.

---

## 💡 README vs. GitHub Wiki: What goes where?

| Feature | `README.md` | GitHub Wiki |
| :--- | :--- | :--- |
| **Primary Purpose** | Repositories' "front door" and project landing page. | In-depth technical knowledge base and operational manual. |
| **Audience** | Starters, prospective users, high-level evaluators. | Core developers, quantitative analysts, devops, and integrators. |
| **Content Scope** | Quick setup, basic features, high-level architecture diagram. | Deep-dive specs, debate mechanics, API schemas, deployment, math formulas. |
| **Format** | Single concise markdown file. | Multi-page organized wiki structured by domain. |

---

## 🗺️ Wiki Navigation

Explore the sections below for comprehensive documentation on the EarningsAgents platform:

1. [**Architecture & Multi-Agent Debates**](./Architecture-&-Multi-Agent-Debates.md)
   - Detailed breakdown of Bull, Bear, Quant, and Consensus agents.
   - Rebuttal round dynamics, prompt engineering strategies, and consensus resolution logic.

2. [**API Reference & Data Schemas**](./API-Reference-&-Data-Schemas.md)
   - FastAPI REST endpoints (`/predict`, `/history`, `/calendar`, `/chat`, `/health`).
   - Real-time WebSocket protocol and state change streaming.
   - SQLModel database schemas (`Prediction`, `User`, `Chat`).

3. [**Data Ingestion & Options Analytics**](./Data-Ingestion-&-Options-Analytics.md)
   - Financial data providers (Yahoo Finance, SEC EDGAR, NewsAPI, Alpha Vantage).
   - ATM straddles option pricing, implied move calculations, and volatility metrics.

4. [**Deployment & Celery Operations**](./Deployment-&-Celery-Operations.md)
   - Docker Compose multi-container setup (API, Worker, Beat Scheduler, Postgres, Redis).
   - Production deployment configurations (Railway, cloud platforms).
   - Task queue management and worker scaling strategies.

5. [**Model Evaluation & Brier Scoring**](./Model-Evaluation-&-Brier-Scoring.md)
   - Brier Score calibration mathematics and accuracy verification.
   - Automated Celery Beat scoring engine and manual trigger tools.

6. [**Developer Guide & Testing**](./Developer-Guide-&-Testing.md)
   - CLI usage guide (`main.py` single, daily, weekly modes).
   - Pytest execution, Makefile shortcuts, and smoke test suites.
   - Guidelines for extending agents and adding LLM providers.
