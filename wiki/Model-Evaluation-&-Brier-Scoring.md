# 🎯 Model Evaluation & Brier Scoring

Evaluating prediction performance in a quantitative, mathematically rigorous manner is integrated directly into EarningsAgents using **Brier Score calibration**.

---

## 📐 The Brier Score Formula

The accuracy of each directional prediction is scored using the quadratic proper scoring rule:

$$Brier = \left( \frac{\text{Confidence \%}}{100} - \text{Correct} \right)^2$$

Where:
- $\text{Confidence \%}$ is the probability ($0-100\%$) assigned by the Consensus Agent to the chosen outcome.
- $\text{Correct} = 1.0$ if the predicted direction (`BEAT` or `MISS`) matches the actual post-earnings outcome.
- $\text{Correct} = 0.0$ if the predicted direction was incorrect.

---

## 📊 Score Interpretation Scale

| Brier Score Range | Calibration Quality | Description |
| :--- | :--- | :--- |
| **`0.00 – 0.05`** | 🌟 Exceptional | High confidence prediction that was completely correct. |
| **`0.06 – 0.25`** | ✅ Good Calibration | Reasonably confident prediction that matched the actual outcome. |
| **`0.26 – 0.50`** | ⚠️ Moderate Calibration | Low confidence prediction or minor miscalibration. |
| **`0.51 – 1.00`** | ❌ Poor Calibration | High confidence prediction that proved completely wrong. |

---

## 🔄 Automated Daily Scoring Routine

```
                             Daily Celery Beat (06:00 UTC)
                                           │
                                           ▼
                               Query Unscored Predictions
                              (database/models.py)
                                           │
                                           ▼
                               Fetch Actual Earnings
                              (Yahoo Finance / Earnings API)
                                           │
                        ┌──────────────────┴──────────────────┐
                        ▼                                     ▼
            Actual Direction (BEAT/MISS)           Actual Price Move %
                        │                                     │
                        └──────────────────┬──────────────────┘
                                           ▼
                              Calculate Brier Score
                              Save to database (`Prediction`)
```

### 1. Data Fetching
- The daily Celery Beat task (`api.tasks.score_predictions_task`) queries all `Prediction` records with `actual_direction IS NULL`.
- It fetches reported EPS, consensus estimate EPS, and price movement over the post-earnings trading session.

### 2. Direction Determination
- If $\text{Reported EPS} > \text{Expected EPS}$, actual direction = `BEAT`.
- If $\text{Reported EPS} < \text{Expected EPS}$, actual direction = `MISS`.
- If equal, actual direction = `MEET`.

### 3. Database Persistence
- Populates `actual_direction`, `actual_eps`, `expected_eps`, `actual_price_move_pct`, `accuracy_score`, and `scored_at`.
