import { Plus } from "lucide-react";
import Container from "./Container";
import SectionHeading from "./SectionHeading";

/** Native <details> rather than a JS accordion: it is keyboard-accessible,
 *  findable by in-page search, and works before hydration. */
const ITEMS = [
  {
    q: "Is this investment advice?",
    a: "No. It is a research tool that shows you an argued case and a confidence number. Nothing here is a recommendation to buy or sell anything, and every prediction can be — and sometimes is — wrong.",
  },
  {
    q: "Why a debate instead of one model?",
    a: "A single prompt tends to launder its own assumptions: it finds evidence for whatever it decided first. Forcing a bull case, a bear case and a market-implied case to be written separately, then to answer each other, surfaces the disagreement instead of averaging it away.",
  },
  {
    q: "Where does the data come from — and can I connect my own?",
    a: "Market and fundamental data from Yahoo Finance, filings and XBRL company facts from SEC EDGAR, headlines and sentiment from news providers, and live options analytics — implied move, max pain, skew — from the options chain. Sources are fetched at run time and cited in the output. You can also connect your own: NewsAPI, Alpha Vantage and EarningsAPI keys go in your settings, are encrypted at rest, and take priority over the shared defaults for every run on your account.",
  },
  {
    q: "What is the research thesis, and how is it different from the verdict?",
    a: "They answer different questions off the same debate. The verdict is a single-quarter call on the coming print, scored once the company reports. The thesis is a 12–36 month structural view — long-horizon bull and bear cases, catalysts, risks, each claim carrying an evidence weight — and it is versioned, so you can compare it against the last one and see what changed.",
  },
  {
    q: "Is the verdict the end of it?",
    a: "No. Both outputs open into a conversation with the consensus agent: challenge an assumption, ask which piece of evidence moved the confidence number, or argue a factor was weighted wrong. It answers from the same context it decided on, so the reasoning stays inspectable rather than being re-improvised.",
  },
  {
    q: "What does the confidence number actually mean?",
    a: "It is the consensus agent's stated probability that its direction is right, and it is scored as such. A 70% call that lands wrong is penalised more than a 55% one, which is the whole point of grading with a Brier score rather than a raw hit rate.",
  },
  {
    q: "Can I add my own research?",
    a: "Yes. Your notes go in as an input the agents have to engage with directly, and the rebuttal round will push back on them the same way it pushes back on the Bull and Bear cases.",
  },
  {
    q: "Which model runs the agents?",
    a: "Configurable per account — Anthropic, OpenAI or Google. You can supply your own API key, which is encrypted at rest and never returned in plaintext.",
  },
];

export default function Faq() {
  return (
    <section className="py-20 md:py-28 border-t border-panel-line">
      <Container>
        <SectionHeading eyebrow="FAQ" title="Questions worth asking first" id="faq" />

        <div className="max-w-[820px] mx-auto divide-y divide-panel-line border-y border-panel-line">
          {ITEMS.map((item) => (
            <details key={item.q} className="group">
              {/* list-none kills the marker in Chrome/Firefox; Safari needs the
                  ::-webkit-details-marker rule as well or a triangle survives. */}
              <summary className="flex items-start gap-4 cursor-pointer list-none [&::-webkit-details-marker]:hidden py-5 px-1 focus-visible:ring-2 focus-visible:ring-teal focus-visible:ring-offset-2 focus-visible:ring-offset-bg outline-none rounded-lg">
                <h3 className="font-display font-medium text-[16.5px] leading-[1.45] text-ink flex-1 group-hover:text-teal transition-colors">
                  {item.q}
                </h3>
                <Plus className="w-[18px] h-[18px] shrink-0 mt-0.5 text-ink-dim transition-transform duration-200 group-open:rotate-45" />
              </summary>
              <p className="font-body text-[15px] leading-[1.7] text-ink-mute pb-6 px-1 pr-10 max-w-[68ch]">
                {item.a}
              </p>
            </details>
          ))}
        </div>
      </Container>
    </section>
  );
}
