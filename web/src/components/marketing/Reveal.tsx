"use client";

import { ReactNode, useEffect, useLayoutEffect, useRef } from "react";

/**
 * Fades + lifts its children the first time they scroll into view.
 *
 * Deliberately not a motion library: the whole site animates with CSS
 * keyframes in globals.css, and pulling framer-motion in for one transition
 * would ship ~30kb to a landing page that currently has no animation deps.
 *
 * Progressive enhancement, on purpose. The markup renders with NO reveal class,
 * so the default state — no JS, JS that failed, an IntersectionObserver that
 * never fires — is fully visible content. Script then opts the element into
 * being hidden and animates it back in. Doing it the other way round (hidden in
 * the markup, shown by JS) means one broken observer blanks half the page, and
 * on this page that would be twelve blocks of copy.
 *
 * The classes are applied imperatively rather than through state so there is no
 * render between "visible" and "hidden". React only rewrites className when its
 * own previous value differs, so the added classes survive re-renders.
 */

// useLayoutEffect warns when a client component is server-rendered; it is the
// right hook here because the hidden class must land before the first paint,
// or above-the-fold children visibly fade out and back in.
const useIsomorphicLayoutEffect =
  typeof window !== "undefined" ? useLayoutEffect : useEffect;

export default function Reveal({
  children,
  delay = 0,
  className = "",
}: {
  children: ReactNode;
  /** Stagger, in ms, for siblings revealed together. */
  delay?: number;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useIsomorphicLayoutEffect(() => {
    const el = ref.current;
    if (!el || typeof IntersectionObserver === "undefined") return;

    el.classList.add("reveal");

    // Safety net for the remaining hole: IntersectionObserver exists, so the
    // element got hidden, but the callback never arrives — it does not fire at
    // all while document.visibilityState is "hidden", and a page restored from
    // bfcache or rendered in a background tab hits exactly that. In a visible
    // tab the observer resolves in milliseconds and always wins this race; if
    // it somehow does not, the copy appears anyway. Losing the animation is a
    // far cheaper failure than losing the content.
    const fallback = setTimeout(() => el.classList.add("reveal-in"), 3000);

    const io = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            el.classList.add("reveal-in");
            clearTimeout(fallback);
            io.disconnect();
          }
        }
      },
      { rootMargin: "0px 0px -12% 0px", threshold: 0.05 }
    );
    io.observe(el);
    return () => {
      clearTimeout(fallback);
      io.disconnect();
    };
  }, []);

  return (
    <div ref={ref} className={className} style={{ transitionDelay: `${delay}ms` }}>
      {children}
    </div>
  );
}
