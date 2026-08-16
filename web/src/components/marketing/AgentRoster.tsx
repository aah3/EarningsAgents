import {
  PenLine,
  Scale,
  Sigma,
  TrendingDown,
  TrendingUp,
  type LucideIcon,
} from "lucide-react";
import { ACCENTS } from "@/components/ui/accents";
import Container from "./Container";
import Reveal from "./Reveal";
import SectionHeading from "./SectionHeading";
import { NodeId, PIPELINE_NODES } from "./pipeline.types";

/** Card metadata that is presentation-only; the copy itself lives in
 *  pipeline.types so the diagram tooltips and these cards cannot disagree. */
const ROSTER: { id: NodeId; icon: LucideIcon; span?: boolean; note: string }[] = [
  { id: "bull", icon: TrendingUp, note: "Runs in parallel · Pass 1" },
  { id: "bear", icon: TrendingDown, note: "Runs in parallel · Pass 1" },
  { id: "quant", icon: Sigma, note: "Runs in parallel · Pass 1" },
  {
    id: "consensus",
    icon: Scale,
    span: true,
    note: "Final pass · answers follow-up questions",
  },
  { id: "research", icon: PenLine, note: "Yours, optional, weighted like any other case" },
];

export default function AgentRoster() {
  return (
    <section className="py-20 md:py-28 border-t border-panel-line">
      <Container>
        <SectionHeading
          eyebrow="The committee"
          title="Four agents with genuinely different jobs"
          id="agents"
        >
          Each one is prompted to be good at its own argument, not to be
          agreeable. The disagreement is the point — a call that survives it is
          worth more than one nobody challenged.
        </SectionHeading>

        <div className="grid gap-4 md:gap-5 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
          {ROSTER.map((entry, i) => {
            const node = PIPELINE_NODES[entry.id];
            const a = ACCENTS[node.accent];
            const Icon = entry.icon;
            return (
              <Reveal
                key={entry.id}
                delay={i * 70}
                className={entry.span ? "lg:col-span-2" : ""}
              >
                <div
                  className={`h-full rounded-2xl border p-6 transition-colors duration-200 ${a.cardBg} ${a.cardBorder} ${a.cardHover}`}
                >
                  <div className="flex items-center gap-3 mb-4">
                    <span
                      className={`w-10 h-10 rounded-xl border grid place-items-center shrink-0 ${a.chipBg} ${a.chipBorder}`}
                    >
                      <Icon className={`w-[18px] h-[18px] ${a.text}`} />
                    </span>
                    <div className="min-w-0">
                      <h3 className="font-display font-semibold text-[17px] text-ink leading-tight">
                        {node.title}
                      </h3>
                      <span className={`eyebrow ${a.text}`}>{node.kicker}</span>
                    </div>
                  </div>
                  <p className="font-body text-[14.5px] leading-[1.68] text-ink-mute mb-5">
                    {node.blurb}
                  </p>
                  <div
                    className={`pt-3.5 border-t font-mono text-[11px] tracking-[0.06em] text-ink-dim ${a.rule}`}
                  >
                    {entry.note}
                  </div>
                </div>
              </Reveal>
            );
          })}
        </div>
      </Container>
    </section>
  );
}
