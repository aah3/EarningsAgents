export type Consensus = "BEAT" | "MISS" | "INLINE";
export type PredictionStatus = "VALIDATED" | "PENDING";

export type PredictionRow = {
  ticker: string;
  targetDate: string;   // ISO yyyy-mm-dd
  status: PredictionStatus;
  consensus: Consensus;
  confidence: number;   // 0–100
};

export const MOCK_PREDICTIONS: PredictionRow[] = [
  {
    ticker: "PRGS",
    targetDate: "2026-06-27",
    status: "VALIDATED",
    consensus: "BEAT",
    confidence: 84,
  },
  {
    ticker: "NKE",
    targetDate: "2026-06-25",
    status: "VALIDATED",
    consensus: "MISS",
    confidence: 68,
  },
  {
    ticker: "LNN",
    targetDate: "2026-07-02",
    status: "PENDING",
    consensus: "INLINE",
    confidence: 72,
  },
  {
    ticker: "MS",
    targetDate: "2026-07-15",
    status: "PENDING",
    consensus: "BEAT",
    confidence: 58,
  },
  {
    ticker: "PENG",
    targetDate: "2026-07-22",
    status: "PENDING",
    consensus: "BEAT",
    confidence: 90,
  },
];
