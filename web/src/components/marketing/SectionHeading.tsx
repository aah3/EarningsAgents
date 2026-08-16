import { ReactNode } from "react";

/**
 * The one heading shape every marketing section uses: eyebrow, H2, optional
 * standfirst. Centred by default; `align="left"` for sections whose body is a
 * single column.
 */
export default function SectionHeading({
  eyebrow,
  title,
  children,
  align = "center",
  id,
}: {
  eyebrow: string;
  title: ReactNode;
  children?: ReactNode;
  align?: "center" | "left";
  id?: string;
}) {
  const centred = align === "center";
  return (
    <div
      id={id}
      className={`${centred ? "text-center mx-auto max-w-[680px]" : "max-w-[680px]"} mb-12 md:mb-14 scroll-mt-28`}
    >
      <span
        className={`eyebrow text-teal inline-flex items-center gap-2 mb-4 ${centred ? "justify-center" : ""}`}
      >
        <span className="w-1.5 h-1.5 rounded-full bg-teal" />
        {eyebrow}
      </span>
      <h2 className="font-display font-semibold text-[clamp(1.85rem,3.1vw,2.6rem)] leading-[1.12] tracking-[-0.022em] text-ink mb-4">
        {title}
      </h2>
      {children && (
        <p className="font-body text-[16.5px] leading-[1.65] text-ink-mute">
          {children}
        </p>
      )}
    </div>
  );
}
