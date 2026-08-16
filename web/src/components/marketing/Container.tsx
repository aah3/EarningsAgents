import { ReactNode } from "react";

/**
 * The single width authority for every marketing section.
 *
 * The old landing page capped at 1240px with 40px gutters, which left ~30% of a
 * modern desktop viewport as dead margin on each side. 1520 recovers most of
 * that without letting prose run past a readable measure — long-form copy
 * constrains itself further via `narrow`, and the hero copy via its own cap.
 *
 * 1520 minus the 40px gutters gives the pipeline diagram a 1440px stage. The
 * diagram's viewBox is 1560 wide — it grew when consensus forked into a
 * verdict and a thesis feeding a follow-up step — so it renders at ~0.92 on a
 * full-width desktop. Widening this container further to chase 1:1 would leave
 * almost no margin at 1600px, which is the problem it was raised to fix.
 */
export default function Container({
  children,
  className = "",
  narrow = false,
}: {
  children: ReactNode;
  className?: string;
  /** Caps at a readable prose measure instead of the full section width. */
  narrow?: boolean;
}) {
  return (
    <div
      className={`w-full mx-auto px-5 sm:px-8 lg:px-10 ${
        narrow ? "max-w-[820px]" : "max-w-[1520px]"
      } ${className}`}
    >
      {children}
    </div>
  );
}
