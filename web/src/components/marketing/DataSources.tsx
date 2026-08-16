import Container from "./Container";

/**
 * Edge-faded marquee of everything the agents can read.
 *
 * The track renders SOURCES twice and translates -50%, which lands exactly on
 * the seam between the two copies — that is what makes the loop invisible.
 * `aria-hidden` on the duplicate keeps screen readers from hearing it twice.
 */
const SOURCES = [
  "Yahoo Finance",
  "SEC EDGAR · 10-K / 10-Q / 8-K",
  "XBRL company facts",
  "Options chains",
  "ATM straddle · implied move",
  "Max pain & skew",
  "NewsAPI headlines",
  "Alpha Vantage sentiment",
  "Earnings calendar",
  "Surprise history",
  "Finviz",
  "Analyst estimates",
];

export default function DataSources() {
  return (
    <section className="py-14 md:py-16 border-t border-panel-line">
      <Container>
        <p className="eyebrow text-ink-dim text-center mb-3">
          What the agents read before they argue
        </p>
        <p className="font-body text-[15px] leading-[1.65] text-ink-mute text-center max-w-[62ch] mx-auto mb-8">
          Run on the shared defaults, or{" "}
          <strong className="font-semibold text-ink">connect your own data sources</strong>{" "}
          — drop in your NewsAPI, Alpha Vantage or EarningsAPI keys, and your own
          Anthropic, OpenAI or Google model key, and every run uses yours. Keys
          are encrypted at rest and never shown back to you in plaintext.
        </p>
      </Container>

      <div className="marquee relative w-full overflow-hidden">
        {/* No gap on the track and a trailing pr-3 on each half: that makes each
            half exactly (items + gaps) wide, so -50% lands seamlessly. An outer
            gap here would offset the loop by half a gap and visibly stutter. */}
        <div className="marquee-track flex w-max">
          {[0, 1].map((copy) => (
            <div key={copy} className="flex gap-3 pr-3" aria-hidden={copy === 1}>
              {SOURCES.map((s) => (
                <span
                  key={s}
                  className="whitespace-nowrap rounded-full border border-panel-line bg-panel-sunk/60 px-4 py-2 font-mono text-[12.5px] text-ink-mute"
                >
                  {s}
                </span>
              ))}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
