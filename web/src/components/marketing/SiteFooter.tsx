import Link from "next/link";
import Container from "./Container";

/** Only real destinations. Anything not built yet stays out of the footer
 *  rather than shipping as a `#` that dead-ends the visitor. */
const COLUMNS: { heading: string; links: { label: string; href: string }[] }[] = [
  {
    heading: "Product",
    links: [
      { label: "Dashboard", href: "/dashboard" },
      { label: "Run a prediction", href: "/dashboard" },
      { label: "Prediction history", href: "/dashboard/history" },
      { label: "Earnings calendar", href: "/dashboard/calendar" },
      { label: "Performance", href: "/dashboard/performance" },
    ],
  },
  {
    heading: "Learn",
    links: [
      { label: "How it works", href: "/#how-it-works" },
      { label: "The committee", href: "/#agents" },
      { label: "Track record", href: "/#track-record" },
      { label: "Methodology", href: "/learn" },
      { label: "FAQ", href: "/#faq" },
    ],
  },
];

export default function SiteFooter() {
  return (
    <footer className="border-t border-panel-line pt-16 pb-12">
      <Container>
        <div className="grid gap-12 md:gap-8 md:grid-cols-[minmax(0,1.4fr)_repeat(2,minmax(0,1fr))]">
          <div>
            <div className="flex items-center gap-[11px] font-display font-bold text-[18px] tracking-[-0.01em] text-ink mb-4 select-none">
              <span
                className="w-[28px] h-[28px] rounded-[9px] bg-gradient-to-br from-teal to-teal-deep grid place-items-center"
                style={{ boxShadow: "0 0 20px rgba(45, 212, 191, 0.35)" }}
              >
                <svg className="w-[15px] h-[15px]" viewBox="0 0 24 24" fill="none">
                  <path d="M12 3l8 4.5-8 4.5-8-4.5L12 3z" fill="#04231F" />
                  <path d="M4 12l8 4.5 8-4.5" stroke="#04231F" strokeWidth="1.6" fill="none" />
                  <path d="M4 16.2l8 4.5 8-4.5" stroke="#04231F" strokeWidth="1.6" fill="none" />
                </svg>
              </span>
              EarningsAI
            </div>
            <p className="font-body text-[14px] leading-[1.65] text-ink-mute max-w-[42ch]">
              Multi-agent earnings intelligence. Every call argued, scored, and
              published.
            </p>
          </div>

          {COLUMNS.map((col) => (
            <div key={col.heading}>
              <h3 className="eyebrow text-ink-dim mb-4">{col.heading}</h3>
              <ul className="flex flex-col gap-2.5">
                {col.links.map((l) => (
                  <li key={l.label}>
                    <Link
                      href={l.href}
                      className="font-body text-[14px] text-ink-mute hover:text-teal transition-colors focus-visible:ring-2 focus-visible:ring-teal outline-none rounded-sm"
                    >
                      {l.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-14 pt-7 border-t border-panel-line flex flex-col md:flex-row md:items-center gap-4 justify-between">
          <p className="font-mono text-[11.5px] leading-[1.6] text-ink-dim max-w-[74ch]">
            Research and educational tool. Not investment advice, not a
            recommendation to buy or sell any security. Predictions are model
            output and are frequently wrong.
          </p>
          <p className="font-mono text-[11.5px] text-ink-dim shrink-0">
            © {new Date().getFullYear()} EarningsAI
          </p>
        </div>
      </Container>
    </footer>
  );
}
