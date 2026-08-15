/**
 * Accent registry — the single source of truth for how a semantic accent maps
 * onto surface, border, and text classes.
 *
 * Every class string here is written out in full on purpose. Tailwind scans
 * source files statically, so an interpolated `bg-${accent}/[0.03]` produces no
 * CSS at all. Adding an accent means adding a row here, not composing strings
 * at the call site — which is what kept the two halves of the analysis output
 * from drifting apart in the first place.
 */

export type Accent =
  | "teal"      // system chrome, consensus
  | "bull"      // bullish / correct
  | "bear"      // bearish / wrong
  | "quant"     // quant agent
  | "human"     // analyst / user input
  | "research"  // structural, long-horizon research
  | "rebuttal"  // bull-vs-bear cross-examination
  | "neutral";  // no semantic charge

export type AccentStyle = {
  /** Tinted card surface. */
  cardBg: string;
  /** Card border at low opacity. */
  cardBorder: string;
  /** Card border on hover — one step stronger. */
  cardHover: string;
  /** Icon chip fill. */
  chipBg: string;
  /** Icon chip border. */
  chipBorder: string;
  /** Foreground for the eyebrow and the icon itself. */
  text: string;
  /** Hairline used under a header or between a summary and its list. */
  rule: string;
  /** Solid fill for list bullet markers. */
  dot: string;
};

export const ACCENTS: Record<Accent, AccentStyle> = {
  teal: {
    cardBg: "bg-teal/[0.03]",
    cardBorder: "border-teal/[0.18]",
    cardHover: "hover:border-teal/30 hover:bg-teal/[0.05]",
    chipBg: "bg-teal/12",
    chipBorder: "border-teal/28",
    text: "text-teal",
    rule: "border-teal/15",
    dot: "bg-teal",
  },
  bull: {
    cardBg: "bg-bull/[0.03]",
    cardBorder: "border-bull/[0.18]",
    cardHover: "hover:border-bull/30 hover:bg-bull/[0.05]",
    chipBg: "bg-bull/12",
    chipBorder: "border-bull/28",
    text: "text-bull",
    rule: "border-bull/15",
    dot: "bg-bull",
  },
  bear: {
    cardBg: "bg-bear/[0.03]",
    cardBorder: "border-bear/[0.18]",
    cardHover: "hover:border-bear/30 hover:bg-bear/[0.05]",
    chipBg: "bg-bear/12",
    chipBorder: "border-bear/28",
    text: "text-bear",
    rule: "border-bear/15",
    dot: "bg-bear",
  },
  quant: {
    cardBg: "bg-quant/[0.03]",
    cardBorder: "border-quant/[0.18]",
    cardHover: "hover:border-quant/30 hover:bg-quant/[0.05]",
    chipBg: "bg-quant/12",
    chipBorder: "border-quant/28",
    text: "text-quant",
    rule: "border-quant/15",
    dot: "bg-quant",
  },
  human: {
    cardBg: "bg-human/[0.03]",
    cardBorder: "border-human/[0.18]",
    cardHover: "hover:border-human/30 hover:bg-human/[0.05]",
    chipBg: "bg-human/12",
    chipBorder: "border-human/28",
    text: "text-human",
    rule: "border-human/15",
    dot: "bg-human",
  },
  research: {
    cardBg: "bg-research/[0.03]",
    cardBorder: "border-research/[0.18]",
    cardHover: "hover:border-research/30 hover:bg-research/[0.05]",
    chipBg: "bg-research/12",
    chipBorder: "border-research/28",
    text: "text-research",
    rule: "border-research/15",
    dot: "bg-research",
  },
  rebuttal: {
    cardBg: "bg-rebuttal/[0.03]",
    cardBorder: "border-rebuttal/[0.18]",
    cardHover: "hover:border-rebuttal/30 hover:bg-rebuttal/[0.05]",
    chipBg: "bg-rebuttal/12",
    chipBorder: "border-rebuttal/28",
    text: "text-rebuttal",
    rule: "border-rebuttal/15",
    dot: "bg-rebuttal",
  },
  neutral: {
    cardBg: "bg-[var(--color-panel-sunk)]",
    cardBorder: "border-panel-line",
    cardHover: "hover:border-ink-dim/40",
    chipBg: "bg-white/5",
    chipBorder: "border-panel-line",
    text: "text-ink-mute",
    rule: "border-panel-line",
    dot: "bg-ink-dim",
  },
};

/** Join truthy class fragments. Avoids pulling in clsx for three components. */
export function cx(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}
