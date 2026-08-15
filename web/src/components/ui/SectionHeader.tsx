import { ReactNode } from "react";
import { Accent, ACCENTS, cx } from "./accents";

/**
 * The one section-header anatomy: a tinted icon chip, a mono eyebrow in the
 * section's accent, and optional horizon/subtitle detail.
 *
 * Rank is expressed by `subtitle` and `muted` — never by swapping the typeface
 * or size. That is what produced four different treatments for peer sections
 * (11px Inter caps, 18px Space Grotesk, 12px Space Mono, and a `label-caps`
 * whose `text-base` override silently never applied).
 */

/**
 * Time horizon the section speaks to. "Bull Case" from the debate and
 * "Bull Case" from the research thesis are both green with an up arrow but
 * describe one quarter versus 12–36 months; this is what tells them apart.
 */
export function HorizonChip({ children }: { children: ReactNode }) {
  return (
    <span className="eyebrow text-[9.5px] tracking-[0.1em] px-[7px] py-0.5 rounded border border-panel-line bg-[var(--color-panel-sunk)] text-ink-dim whitespace-nowrap select-none">
      {children}
    </span>
  );
}

export type SectionHeaderProps = {
  /** Semantic accent; drives the chip tint and the eyebrow colour. */
  accent?: Accent;
  /** Any lucide icon — sized by this component, so callers needn't pass one. */
  icon?: ReactNode;
  /** The label itself. Rendered uppercase by `.eyebrow`. */
  eyebrow: string;
  /** Rank-1 sections only: a line of detail under the eyebrow. */
  subtitle?: string;
  /** Short horizon marker, e.g. "This quarter" or "12–36 mo". */
  horizon?: string;
  /**
   * Rank-3 sub-pillars: dims the eyebrow to ink-dim and leaves the accent on
   * the chip alone, so nested sections don't compete with their parent.
   */
  muted?: boolean;
  /** Adds a hairline under the header, tinted to the accent. */
  divider?: boolean;
  /** Trailing controls (buttons, badges) pinned to the right. */
  actions?: ReactNode;
  className?: string;
  /** Heading level — set from document structure, not from visual weight. */
  as?: "h2" | "h3" | "h4" | "h5";
};

export default function SectionHeader({
  accent = "teal",
  icon,
  eyebrow,
  subtitle,
  horizon,
  muted = false,
  divider = false,
  actions,
  className,
  as: Heading = "h4",
}: SectionHeaderProps) {
  const a = ACCENTS[accent];

  return (
    <div
      className={cx(
        "flex items-center justify-between gap-4 flex-wrap select-none",
        divider && cx("border-b pb-3.5", a.rule),
        className
      )}
    >
      <div className="flex items-center gap-3">
        {icon && (
          <span
            className={cx(
              "w-7 h-7 rounded-[9px] border flex items-center justify-center shrink-0",
              "[&>svg]:w-3.5 [&>svg]:h-3.5",
              a.chipBg,
              a.chipBorder,
              a.text
            )}
            aria-hidden="true"
          >
            {icon}
          </span>
        )}

        <div className="min-w-0">
          <div className="flex items-center gap-2.5 flex-wrap">
            <Heading className={cx("eyebrow", muted ? "text-ink-dim" : a.text)}>
              {eyebrow}
            </Heading>
            {horizon && <HorizonChip>{horizon}</HorizonChip>}
          </div>
          {subtitle && (
            <p className="text-[12.5px] text-ink-dim mt-0.5 leading-snug">{subtitle}</p>
          )}
        </div>
      </div>

      {actions && <div className="flex items-center gap-2 flex-wrap">{actions}</div>}
    </div>
  );
}
