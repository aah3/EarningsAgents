# 🔌 API Reference & Data Schemas

The EarningsAgents backend is powered by FastAPI (running on port `8000`), providing RESTful endpoints, streaming WebSockets, and database persistence via SQLModel and PostgreSQL/SQLite.

---

## 📡 REST Endpoints

### 1. `POST /api/predict`
Triggers an asynchronous prediction task via Celery worker.

- **Request Body (`PredictionRequest`):**
  ```json
  {
    "ticker": "NVDA",
    "report_date": "2026-05-22",
    "user_analysis": "Optional qualitative insights injected into debate context"
  }
  ```
- **Response (`202 Accepted`):**
  ```json
  {
    "task_id": "c9a2f78b-3e11-4f9a-9e12-88d44711fa02",
    "status": "PENDING"
  }
  ```

---

### 2. `GET /api/predict/status/{task_id}`
Checks the execution status of an active prediction task.

- **Response:**
  ```json
  {
    "task_id": "c9a2f78b-3e11-4f9a-9e12-88d44711fa02",
    "status": "SUCCESS",
    "result": {
      "prediction_id": 42,
      "ticker": "NVDA",
      "direction": "BEAT",
      "confidence": 85.0,
      "reasoning_summary": "Strong datacenter revenue growth..."
    }
  }
  ```

---

### 3. `GET /api/history`
Retrieves past prediction records stored in the database.

- **Query Parameters:**
  - `ticker` *(optional)*: Filter by symbol (e.g. `AAPL`).
  - `limit` *(default: 50)*: Maximum items to return.
- **Response:** Array of `Prediction` objects.

---

### 4. `GET /api/calendar`
Fetches upcoming earnings release calendar for the given date range.

- **Query Parameters:**
  - `start_date` *(YYYY-MM-DD)*
  - `end_date` *(YYYY-MM-DD)*

---

### 5. `POST /api/chat`
Interactive conversational AI endpoint for asking follow-up questions about a specific earnings report or prediction.

---

## ⚡ WebSocket Live Protocol

Connect to `ws://localhost:8000/ws/predict/{task_id}` to receive real-time execution steps as agents debate:

```json
{
  "event": "agent_progress",
  "data": {
    "agent": "BullAgent",
    "status": "Analyzing Q1 supply chain and margin metrics...",
    "step": 2,
    "total_steps": 5
  }
}
```

---

## 🗄️ Database SQLModel Schemas

### `User` Table
- `id`: Integer (Primary Key)
- `clerk_id`: String (Unique Clerk Auth ID)
- `email`: String (User email)
- `created_at`: Datetime

### `UserSettings` Table
- `id`: Integer (Primary Key)
- `user_id`: Integer (Foreign Key -> `user.id`)
- `provider`: String (`gemini`, `openai`, `anthropic`)
- `model_name`: String (`gemini-1.5-flash-002`, `gpt-4o`, etc.)
- Encrypted API key fields (Fernet cipher): `gemini_api_key`, `openai_api_key`, `anthropic_api_key`, `newsapi_api_key`, `alphavantage_api_key`.

### `Prediction` Table
- `id`: Integer (Primary Key)
- `ticker`: String (Indexed)
- `company_name`: String
- `report_date`: Datetime
- `direction`: String (`BEAT` / `MISS`)
- `confidence`: Float ($0.0 - 100.0$)
- `expected_price_move`: String
- `bull_factors`: JSON Array (`List[str]`)
- `bear_factors`: JSON Array (`List[str]`)
- `rebuttal_summary`: String (Cross-examination transcript)
- `agent_votes`: JSON Object (`{"Bull": "BEAT", "Bear": "MISS", "Quant": "BEAT"}`)
- `options_features`: JSON Object (`{"implied_move_pct": 5.4, "iv_percentile": 78}`)
- **Scoring Fields:** `actual_direction`, `actual_eps`, `expected_eps`, `actual_price_move_pct`, `accuracy_score` (Brier Score), `scored_at`.
