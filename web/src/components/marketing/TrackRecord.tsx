import { Clock, Lock, Ruler } from "lucide-react";
import Container from "./Container";
import Reveal from "./Reveal";
import SectionHeading from "./SectionHeading";

/**
 * Deliberately describes the *method*, not a hit rate.
 *
 * There is no honest aggregate accuracy figure to publish on a marketing page —
 * whatever number sat here would be either cherry-picked or stale within a
 * quarter, which is exactly what the section claims not to do. So the tiles
 * state how scoring works and the leaderboard carries the live numbers.
 */
const FACTS = [
  {
    icon: Lock,
    label: "Written down first",
    body: "The direction and the confidence are persisted before the company reports. Nothing is edited after the fact.",
  },
  {
    icon: Ruler,
    label: "Brier score, lower is better",
    body: "A call graded on confidence, not just direction: (confidence − outcome)². Being loudly wrong costs more than being unsure.",
  },
  {
    icon: Clock,
    label: "Scored daily, automatically",
    body: "A scheduled job reconciles open predictions against actual reported results every morning and publishes the result.",
  },
];

export default function TrackRecord() {
  return (
    <section className="py-20 md:py-28 border-t border-panel-line">
      <Container>
        <div className="grid gap-12 lg:gap-16 lg:grid-cols-[minmax(0,0.92fr)_minmax(0,1.08fr)] items-start">
          <SectionHeading
            eyebrow="Track record"
            title="Graded on the record, not on the pitch"
            align="left"
            id="track-record"
          >
            An earnings model is only worth what its scoreboard says. Every call
            this platform makes is timestamped before the print and graded after
            it — including the ones that go badly.
          </SectionHeading>

          <div className="flex flex-col gap-3.5 lg:mt-2">
            {FACTS.map((f, i) => (
              <Reveal key={f.label} delay={i * 80}>
                <div className="flex gap-4 rounded-2xl border border-panel-line bg-panel-sunk/70 p-5 hover:border-teal/25 transition-colors duration-200">
                  <span className="w-10 h-10 shrink-0 rounded-xl bg-teal/10 border border-teal/25 grid place-items-center">
                    <f.icon className="w-[18px] h-[18px] text-teal" />
                  </span>
                  <div>
                    <h3 className="font-display font-semibold text-[16px] text-ink mb-1.5">
                      {f.label}
                    </h3>
                    <p className="font-body text-[14px] leading-[1.65] text-ink-mute">
                      {f.body}
                    </p>
                  </div>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </Container>
    </section>
  );
}
