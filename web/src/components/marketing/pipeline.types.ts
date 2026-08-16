import type { Accent } from "@/components/ui/accents";

/**
 * The pipeline is described once, here, and consumed three ways: the wide SVG
 * diagram, the stacked mobile stepper, and the agent roster cards further down
 * the page. Copy lives with the data so those three never drift apart.
 *
 * Nothing in here names a company, ticker or quarter — the landing page shows
 * how a call is made, not a call.
 */

export type NodeId =
  | "bull"
  | "bear"
  | "quant"
  | "research"
  | "debate"
  | "rebuttal"
  | "consensus"
  | "verdict"
  | "thesis"
  | "followup";

export type PipelineNode = {
  id: NodeId;
  /** Card title. */
  title: string;
  /** Mono sub-label rendered inside the node. */
  kicker: string;
  /** Tooltip / roster-card body. One or two sentences, plain language. */
  blurb: string;
  accent: Accent;
  /** Which stage of the left-to-right flow this node belongs to. */
  stage: 1 | 2 | 3 | 4 | 5 | 6;
};

/** Stage 5 holds two nodes: consensus forks into a single-quarter call and a
 *  multi-year thesis, and both feed the follow-up conversation in stage 6. */
export const STAGES: { n: number; label: string }[] = [
  { n: 1, label: "Inputs" },
  { n: 2, label: "Debate" },
  { n: 3, label: "Rebuttal" },
  { n: 4, label: "Consensus" },
  { n: 5, label: "Outputs" },
  { n: 6, label: "Follow-up" },
];

export const PIPELINE_NODES: Record<NodeId, PipelineNode> = {
  bull: {
    id: "bull",
    title: "Bull agent",
    kicker: "BUYSIDE CASE",
    blurb:
      "Builds the strongest honest case for an upside surprise — demand signals, pricing power, the company's own beat history, and the catalysts management is most likely to lean on.",
    accent: "bull",
    stage: 1,
  },
  bear: {
    id: "bear",
    title: "Bear agent",
    kicker: "SHORT CASE",
    blurb:
      "Argues the other side — margin pressure, channel build, share loss, and the guidance risk a consensus estimate tends to under-price.",
    accent: "bear",
    stage: 1,
  },
  quant: {
    id: "quant",
    title: "Quant agent",
    kicker: "OPTIONS · MAX PAIN",
    blurb:
      "Reads the market's own forecast: implied move from the at-the-money straddle, max-pain strike, skew, and the historical distribution of surprises.",
    accent: "quant",
    stage: 1,
  },
  research: {
    id: "research",
    title: "Your research",
    kicker: "OPTIONAL HUMAN INPUT",
    blurb:
      "Drop in your own notes, channel checks or thesis. It enters as a first-class input the agents are required to engage with — not a footnote.",
    accent: "human",
    stage: 1,
  },
  debate: {
    id: "debate",
    title: "Debate",
    kicker: "SHARED CONTEXT",
    blurb:
      "Every thesis lands in one shared context. Overlapping claims collapse, contradictions surface, and each argument stays attached to the evidence behind it.",
    accent: "teal",
    stage: 2,
  },
  rebuttal: {
    id: "rebuttal",
    title: "Rebuttal",
    kicker: "CROSS-EXAMINATION",
    blurb:
      "Bull and Bear read each other's case and answer it directly. Claims that cannot survive the challenge get dropped; the ones that do carry more weight downstream.",
    accent: "rebuttal",
    stage: 3,
  },
  consensus: {
    id: "consensus",
    title: "Consensus",
    kicker: "CONFIDENCE-WEIGHTED",
    blurb:
      "Weighs the surviving arguments by evidence strength and agent conviction, then commits to one direction and a calibrated confidence. You can keep questioning it afterwards.",
    accent: "teal",
    stage: 4,
  },
  verdict: {
    id: "verdict",
    title: "Verdict",
    kicker: "THIS QUARTER'S PRINT",
    blurb:
      "The single-quarter call — beat, meet or miss — with a confidence number attached. Scored against the actual report and published, whichever way it lands.",
    accent: "teal",
    stage: 5,
  },
  thesis: {
    id: "thesis",
    title: "Research thesis",
    kicker: "12–36 MONTH VIEW",
    blurb:
      "The other half of the answer: a structural view that outlives the quarter. Long-horizon bull and bear cases, the catalysts and risks behind them, every claim carrying an evidence weight — and versioned, so you can diff it against the last one.",
    accent: "research",
    stage: 5,
  },
  followup: {
    id: "followup",
    title: "Ask the agent",
    kicker: "OPEN-ENDED Q&A",
    blurb:
      "Neither output is the end of it. Question the assumptions, ask which evidence moved the number, push back on a factor you think is wrong — the consensus agent answers from the same context it decided on, and keeps answering.",
    accent: "human",
    stage: 6,
  },
};

/**
 * Illustrative outcome shown on the verdict card. Intentionally company-less:
 * a direction and a confidence, so the diagram reads as "this is the shape of
 * an answer" rather than a live or backtested call on a real name.
 */
export const EXAMPLE_OUTCOME = {
  directions: ["BEAT", "MEET", "MISS"] as const,
  selected: "BEAT",
  confidence: 72,
};
