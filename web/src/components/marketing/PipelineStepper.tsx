import { ACCENTS } from "@/components/ui/accents";
import { NodeId, PIPELINE_NODES, STAGES } from "./pipeline.types";

/**
 * The sub-1280px form of the pipeline.
 *
 * The wide SVG is 1440 units across, so anywhere below xl its labels scale
 * into illegibility (see the note at the swap site in Hero). This says the
 * same thing vertically at a readable size, and avoids shipping a
 * horizontally-scrolling hero. Same nodes, same copy — the tooltip text is
 * simply always visible here, since there is no hover on touch.
 */

const STAGE_NODES: NodeId[][] = [
  ["bull", "bear", "quant", "research"],
  ["debate"],
  ["rebuttal"],
  ["consensus"],
  ["verdict", "thesis"],
  ["followup"],
];

export default function PipelineStepper() {
  return (
    /* Capped and centred: at 1000-1279px the container is far wider than this
       list needs, and full-bleed one-line cards read as broken layout. */
    <ol className="relative flex flex-col gap-7 pl-9 max-w-[680px] mx-auto">
      {/* Spine */}
      <span
        aria-hidden="true"
        className="absolute left-[11px] top-2 bottom-2 w-px bg-gradient-to-b from-teal/40 via-panel-line to-transparent"
      />
      {STAGES.map((stage, i) => (
        <li key={stage.n} className="relative">
          <span
            aria-hidden="true"
            className="absolute -left-9 top-1 w-[23px] h-[23px] rounded-full border border-teal/40 bg-panel-sunk grid place-items-center eyebrow text-teal text-[9px]"
          >
            {String(stage.n).padStart(2, "0")}
          </span>
          <h3 className="eyebrow text-ink-dim mb-3">{stage.label}</h3>
          {/* Only stage 1 has more than one node; pairing those up keeps the
              timeline from running to four screens on a tablet. */}
          <div
            className={
              STAGE_NODES[i].length > 1
                ? "grid gap-2.5 sm:grid-cols-2"
                : "flex flex-col gap-2.5"
            }
          >
            {STAGE_NODES[i].map((id) => {
              const node = PIPELINE_NODES[id];
              const a = ACCENTS[node.accent];
              return (
                <div
                  key={id}
                  className={`rounded-xl border p-3.5 ${a.cardBg} ${a.cardBorder}`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`w-2 h-2 rounded-full ${a.dot}`} />
                    <span className="font-display font-semibold text-[15px] text-ink">
                      {node.title}
                    </span>
                  </div>
                  <p className="font-body text-[13px] leading-[1.6] text-ink-mute">
                    {node.blurb}
                  </p>
                </div>
              );
            })}
          </div>
        </li>
      ))}
    </ol>
  );
}
