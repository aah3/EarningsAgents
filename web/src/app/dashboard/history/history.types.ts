export type Prediction = "BEAT" | "MISS" | "INLINE";
export type Outcome = "CORRECT" | "WRONG" | "UNVERIFIED";
export type ReportTiming = "BMO" | "AMC" | "UNKNOWN";

export type HistoryRow = {
  id?: number;
  ticker: string;
  company: string;
  sector?: string;
  analysisDate: string;                 // ISO — Prediction.prediction_date (when analysis ran)
  reportDate: string;                   // ISO — Prediction.report_date (actual earnings date)
  reportTiming: ReportTiming;           // before/after market session
  prediction: Prediction;
  confidence: number;                   // 0–100
  actualEps: number | null;
  expectedEps: number | null;
  postEarningsMove: number | null;      // %
  brier: number | null;
  outcome: Outcome;                     // UNVERIFIED until scored
};

export const isScored = (r: HistoryRow) => r.outcome !== "UNVERIFIED";
