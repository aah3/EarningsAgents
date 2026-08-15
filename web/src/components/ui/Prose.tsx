import { ReactNode } from "react";
import { Accent, ACCENTS, cx } from "./accents";

/**
 * Text primitives wrapping the phase-1 type scale, so no call site writes
 * `text-[15px] ... leading-[1.7]` by hand again. Narrative prose previously
 * rendered at 15px/1.7/ink-mute in the prediction tab and 14px/1.625/ink in the
 * research thesis, for the same class of content.
 */

/** Narrative body copy: bull, bear, quant, pillars, consensus, rebuttals. */
export function Prose({
  children,
  className,
  /** LLM output carries meaningful newlines, so these are preserved by default. */
  preserveBreaks = true,
}: {
  children: ReactNode;
  className?: string;
  preserveBreaks?: boolean;
}) {
  return (
    <p
      className={cx(
        "prose-body text-ink-mute",
        preserveBreaks && "whitespace-pre-line",
        className
      )}
    >
      {children}
    </p>
  );
}

/** The single headline conviction quote. One per view. */
export function ProseLead({ children, className }: { children: ReactNode; className?: string }) {
  return <p className={cx("prose-lead text-ink text-balance", className)}>{children}</p>;
}

/** Shown in place of prose when an agent or source returned nothing. */
export function ProseEmpty({ children }: { children: ReactNode }) {
  return <p className="prose-list text-ink-dim italic">{children}</p>;
}

export type ProseListProps = {
  items: string[];
  /** Tints the marker. Text stays ink-mute so the list reads as one block. */
  accent?: Accent;
  /** Dot is the default; check/cross suit bull and bear factor lists. */
  marker?: "dot" | "check" | "cross";
  /** Rendered when `items` is empty. */
  empty?: string;
  className?: string;
};

/** Factor bullets, catalysts, risk register entries. */
export function ProseList({
  items,
  accent = "neutral",
  marker = "dot",
  empty,
  className,
}: ProseListProps) {
  const a = ACCENTS[accent];

  if (!items || items.length === 0) {
    return empty ? <ProseEmpty>{empty}</ProseEmpty> : null;
  }

  return (
    <ul className={cx("flex flex-col gap-3", className)}>
      {items.map((item, i) => (
        <li key={i} className="prose-list text-ink-mute flex items-start gap-3">
          {marker === "dot" ? (
            <span
              className={cx("w-1.5 h-1.5 rounded-full shrink-0 mt-[7px]", a.dot)}
              aria-hidden="true"
            />
          ) : (
            <span className={cx("font-bold shrink-0 leading-[1.6]", a.text)} aria-hidden="true">
              {marker === "check" ? "✓" : "×"}
            </span>
          )}
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}
