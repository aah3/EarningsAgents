import {
  CalendarClock,
  Database,
  MessageCircleQuestion,
  MessagesSquare,
  Target,
} from "lucide-react";
import Container from "./Container";
import Reveal from "./Reveal";
import SectionHeading from "./SectionHeading";

const STEPS = [
  {
    icon: CalendarClock,
    title: "Pick a company and a report date",
    body: "Search any listed name. The calendar knows when it reports, so you can queue a call days ahead of the print or run one the morning of.",
  },
  {
    icon: Database,
    title: "Agents pull their own evidence",
    body: "Fundamentals, filings, headlines and the live options chain — fetched at run time, not from a stale snapshot, and cited back in the output. Connect your own provider keys and they use those instead.",
  },
  {
    icon: MessagesSquare,
    title: "They argue, rebut, and converge",
    body: "Three cases in parallel, then a cross-examination round, then a consensus agent that has to justify the weight it gave each side.",
  },
  {
    icon: MessageCircleQuestion,
    title: "You question the result",
    body: "Two outputs land: a call on the quarter and a 12–36 month research thesis. Neither is final — challenge an assumption, ask which evidence moved the number, and the consensus agent answers from the context it decided on.",
  },
  {
    icon: Target,
    title: "The call gets scored",
    body: "Every prediction is written down before the report lands and graded against it afterwards with a Brier score. Wrong calls stay on the record.",
  },
];

export default function HowItWorks() {
  return (
    <section className="py-20 md:py-28 border-t border-panel-line">
      <Container>
        <SectionHeading eyebrow="How it works" title="Five steps, no black box" id="how-it-works">
          You can follow the reasoning at every stage — which agent said what,
          what evidence it leaned on, where the consensus disagreed with it, and
          what it says when you push back.
        </SectionHeading>

        {/* 2xl, not the `wide` breakpoint the hero uses: custom breakpoints
            sort ahead of the built-ins, so `wide:grid-cols-5` loses to
            `lg:grid-cols-3` (see globals.css). Five columns below ~1500px give
            220px cards that wrap every title to three lines anyway, so 3 + 2
            is the better layout in that band regardless. */}
        <div className="grid gap-4 md:gap-5 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-5">
          {STEPS.map((step, i) => (
            <Reveal key={step.title} delay={i * 80}>
              <div className="h-full rounded-2xl border border-panel-line bg-panel-sunk/70 p-6 hover:border-teal/25 transition-colors duration-200">
                <div className="flex items-center justify-between mb-5">
                  <span className="w-10 h-10 rounded-xl bg-teal/10 border border-teal/25 grid place-items-center">
                    <step.icon className="w-[18px] h-[18px] text-teal" />
                  </span>
                  <span className="eyebrow text-ink-dim">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                </div>
                <h3 className="font-display font-semibold text-[17px] leading-[1.3] text-ink mb-2.5">
                  {step.title}
                </h3>
                <p className="font-body text-[14px] leading-[1.65] text-ink-mute">
                  {step.body}
                </p>
              </div>
            </Reveal>
          ))}
        </div>
      </Container>
    </section>
  );
}
