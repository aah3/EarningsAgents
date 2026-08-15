import { ReactNode } from "react";
import { Accent, ACCENTS, cx } from "./accents";

/**
 * The container every narrative section sits in.
 *
 * Radius, padding, border and background tint are derived from `accent` and
 * `density` rather than passed in as class strings — that is the whole point.
 * Previously the same class of card appeared as p-6, p-8 and p-10 with three
 * different radii depending on which file it lived in.
 *
 * Geometry (fixed):
 *   radius   16px  (rounded-2xl)
 *   padding  24px comfortable · 18px compact
 *   border   accent @ 18%
 *   surface  accent @ 3%
 */

export type SectionCardProps = {
  accent?: Accent;
  /** 24px default; `compact` is 18px for nested or dense cards. */
  density?: "comfortable" | "compact";
  /** Lifts border and surface one step on hover. Off for static content. */
  interactive?: boolean;
  children: ReactNode;
  className?: string;
  id?: string;
};

export default function SectionCard({
  accent = "neutral",
  density = "comfortable",
  interactive = false,
  children,
  className,
  id,
}: SectionCardProps) {
  const a = ACCENTS[accent];

  return (
    <section
      id={id}
      className={cx(
        "rounded-2xl border",
        density === "comfortable" ? "p-6" : "p-[18px]",
        a.cardBg,
        a.cardBorder,
        interactive && cx("transition-colors duration-200", a.cardHover),
        className
      )}
    >
      {children}
    </section>
  );
}
