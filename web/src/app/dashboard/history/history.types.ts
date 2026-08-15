import type { HistorySortKey } from "@/lib/api";

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
  fiscalPeriod: string | null;          // reporting period, e.g. "2026Q1"
  prediction: Prediction;
  confidence: number;                   // 0–100
  actualEps: number | null;
  expectedEps: number | null;
  postEarningsMove: number | null;      // %
  brier: number | null;
  outcome: Outcome;                     // UNVERIFIED until scored
};

export const isScored = (r: HistoryRow) => r.outcome !== "UNVERIFIED";

/** Column identity for the table header — maps a UI column to its server sort key. */
export type SortKey = HistorySortKey;

export const PAGE_SIZE_OPTIONS = [10, 25, 50, 100] as const;
export const DEFAULT_PAGE_SIZE = 10;
