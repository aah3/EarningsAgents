export type PipelineData = {
  ticker: string;
  status: string;      // e.g. "ANALYZING"
  verdict: string;     // e.g. "Beat & raise"
  confidence: string;  // e.g. "72%"
};

export const DEFAULT_PIPELINE: PipelineData = {
  ticker: "AVGO",
  status: "ANALYZING",
  verdict: "Beat & raise",
  confidence: "72%",
};
