export type Consensus = "BEAT" | "MISS" | "INLINE";
export type PredictionStatus = "VALIDATED" | "PENDING";

export type PredictionRow = {
  ticker: string;
  sector?: string;
  targetDate: string;   // ISO yyyy-mm-dd
  status: PredictionStatus;
  consensus: Consensus;
  confidence: number;   // 0–100
};

export const MOCK_PREDICTIONS: PredictionRow[] = [
  {
    ticker: "PRGS",
    sector: "Technology",
    targetDate: "2026-06-27",
    status: "VALIDATED",
    consensus: "BEAT",
    confidence: 84,
  },
  {
    ticker: "NKE",
    sector: "Consumer Discretionary",
    targetDate: "2026-06-25",
    status: "VALIDATED",
    consensus: "MISS",
    confidence: 68,
  },
  {
    ticker: "LNN",
    sector: "Industrials",
    targetDate: "2026-07-02",
    status: "PENDING",
    consensus: "INLINE",
    confidence: 72,
  },
  {
    ticker: "MS",
    sector: "Financials",
    targetDate: "2026-07-15",
    status: "PENDING",
    consensus: "BEAT",
    confidence: 58,
  },
  {
    ticker: "PENG",
    sector: "Technology",
    targetDate: "2026-07-22",
    status: "PENDING",
    consensus: "BEAT",
    confidence: 90,
  },
];
