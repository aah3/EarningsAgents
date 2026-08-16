"use client";

import React, { useId, useState } from "react";
import {
  EXAMPLE_OUTCOME,
  NodeId,
  PIPELINE_NODES,
  STAGES,
} from "./pipeline.types";

/* ────────────────────────────────────────────────────────────────────────────
   Geometry

   One viewBox, one set of coordinates. Every connector endpoint below is
   derived from these boxes by hand, so if you move a node you must move the
   edges that touch it — that is the cost of drawing real curves instead of
   letting a layout engine guess. The payoff is that the whole diagram scales
   as a single unit: it is one <svg> at `w-full h-auto`, so it fills whatever
   width the container gives it without a single media query.

   Six columns, centres:  1:107  2:374  3:638  4:852  5:1120  6:1423
   Vertical spine: y = 250 for stages 2-4 and 6. Stage 5 is the fork — the
   verdict sits at 172 and the thesis at 328, symmetric about the spine.

   Two feedback loops share the bottom lane at y=474: rebuttal → debate on the
   left (x 374-638) and follow-up → consensus on the right (x 852-1423). Their
   x ranges are disjoint, so one lane reads as one convention rather than two.
   ──────────────────────────────────────────────────────────────────────── */

const VB_W = 1560;
/** Tight to the drawn content: 14 (stage-label cap height) to 486 (the bottom
 *  of the loop caption plates). Slack here shows up as dead space above and
 *  below the diagram at every viewport width. */
const VB_H = 500;

type Box = { x: number; y: number; w: number; h: number };

const BOX: Record<Exclude<NodeId, "consensus">, Box> = {
  bull: { x: 14, y: 54, w: 186, h: 72 },
  bear: { x: 14, y: 142, w: 186, h: 72 },
  quant: { x: 14, y: 230, w: 186, h: 72 },
  research: { x: 14, y: 360, w: 186, h: 72 },
  debate: { x: 260, y: 84, w: 228, h: 336 },
  rebuttal: { x: 546, y: 176, w: 184, h: 148 },
  verdict: { x: 996, y: 104, w: 248, h: 136 },
  thesis: { x: 996, y: 260, w: 248, h: 136 },
  followup: { x: 1300, y: 180, w: 246, h: 140 },
};

const CONSENSUS = { cx: 852, cy: 250, r: 68, ring: 84, glow: 118 };

/** Hit target per node, in viewBox units. Same rects as BOX; the consensus
 *  disc gets a square around its outer ring and is rounded off in CSS. */
const HOTSPOT: Record<NodeId, Box & { round?: boolean }> = {
  ...BOX,
  consensus: {
    x: CONSENSUS.cx - CONSENSUS.ring,
    y: CONSENSUS.cy - CONSENSUS.ring,
    w: CONSENSUS.ring * 2,
    h: CONSENSUS.ring * 2,
    round: true,
  },
};

/** Where a node's tooltip anchors, in viewBox units. */
const ANCHOR: Record<NodeId, { x: number; y: number; side: "left" | "right" }> =
  {
    bull: { x: 200, y: 90, side: "right" },
    bear: { x: 200, y: 178, side: "right" },
    quant: { x: 200, y: 266, side: "right" },
    research: { x: 200, y: 396, side: "right" },
    debate: { x: 488, y: 250, side: "right" },
    rebuttal: { x: 546, y: 250, side: "left" },
    // Off the outer pulsing ring, not the inner disc, so the tooltip never
    // lands on top of the ring.
    consensus: { x: CONSENSUS.cx - CONSENSUS.ring, y: 250, side: "left" },
    verdict: { x: 996, y: 172, side: "left" },
    thesis: { x: 996, y: 328, side: "left" },
    followup: { x: 1300, y: 250, side: "left" },
  };

const STAGE_X = [107, 374, 638, 852, 1120, 1423];

const HIT_ORDER: NodeId[] = [
  "bull",
  "bear",
  "quant",
  "research",
  "debate",
  "rebuttal",
  "consensus",
  "verdict",
  "thesis",
  "followup",
];

const DIAGRAM_SUMMARY =
  "Six-stage pipeline. Bull, Bear and Quant agents plus your optional research feed a shared debate; a rebuttal round cross-examines the cases and loops back for another round; a consensus agent weighs what survives and forks into two outputs — a confidence-scored verdict for the coming quarter and a twelve-to-thirty-six month research thesis. Both feed an open-ended follow-up conversation with the consensus agent, which can send the question back through the consensus step.";

type Edge = {
  id: string;
  d: string;
  color: string;
  /** Seconds for one dot to traverse the path. */
  dur: number;
  delay: number;
  dashed?: boolean;
  arrow?: "teal" | "rebuttal" | "human" | "research";
};

const EDGES: Edge[] = [
  {
    id: "bull",
    d: "M200,90 C240,90 244,138 260,138",
    color: "var(--color-bull)",
    dur: 2.4,
    delay: 0,
  },
  {
    id: "bear",
    d: "M200,178 C240,178 244,196 260,196",
    color: "var(--color-bear)",
    dur: 2.4,
    delay: 0.35,
  },
  {
    id: "quant",
    d: "M200,266 C240,266 244,254 260,254",
    color: "var(--color-quant)",
    dur: 2.4,
    delay: 0.7,
  },
  {
    id: "research",
    d: "M200,396 C244,396 244,340 260,340",
    color: "var(--color-human)",
    dur: 2.4,
    delay: 1.05,
    dashed: true,
  },
  {
    id: "spine-1",
    d: "M488,250 L538,250",
    color: "var(--color-teal)",
    dur: 1.4,
    delay: 1.4,
    arrow: "teal",
  },
  {
    id: "spine-2",
    // Stops short of the consensus ring at 768 — running to the inner disc
    // would put the arrowhead on top of the pulsing ring.
    d: "M730,250 L760,250",
    color: "var(--color-teal)",
    dur: 1.2,
    delay: 1.75,
    arrow: "teal",
  },
  {
    // The fork. Consensus answers two different questions off one debate.
    id: "fork-verdict",
    d: "M940,250 C968,250 972,172 996,172",
    color: "var(--color-teal)",
    dur: 1.6,
    delay: 2.1,
    arrow: "teal",
  },
  {
    id: "fork-thesis",
    d: "M940,250 C968,250 972,328 996,328",
    color: "var(--color-research)",
    dur: 1.6,
    delay: 2.35,
    arrow: "research",
  },
  {
    id: "verdict-followup",
    d: "M1244,172 C1272,172 1276,215 1300,215",
    color: "var(--color-teal)",
    dur: 1.5,
    delay: 2.7,
    arrow: "teal",
  },
  {
    id: "thesis-followup",
    d: "M1244,328 C1272,328 1276,285 1300,285",
    color: "var(--color-research)",
    dur: 1.5,
    delay: 2.9,
    arrow: "research",
  },
  {
    // Rebuttal feeds the debate another round.
    id: "loop-rebuttal",
    d: "M638,324 L638,454 Q638,474 618,474 L394,474 Q374,474 374,454 L374,428",
    color: "var(--color-rebuttal)",
    dur: 3.4,
    delay: 2.2,
    dashed: true,
    arrow: "rebuttal",
  },
  {
    // Your follow-up questions go back to the consensus agent — the second
    // loop, and the one that makes the verdict a conversation, not a receipt.
    id: "loop-followup",
    d: "M1423,320 L1423,454 Q1423,474 1403,474 L872,474 Q852,474 852,454 L852,338",
    color: "var(--color-human)",
    dur: 4.2,
    delay: 3.1,
    dashed: true,
    arrow: "human",
  },
];

const ARROW_COLORS: Record<string, string> = {
  teal: "var(--color-teal)",
  rebuttal: "var(--color-rebuttal)",
  human: "var(--color-human)",
  research: "var(--color-research)",
};

/* ──────────────────────────────────────────────────────────────────────── */

export default function PipelineDiagram() {
  const uid = useId().replace(/:/g, "");
  const [active, setActive] = useState<NodeId | null>(null);

  /** Highlight class for a drawn node. The SVG carries no interactivity of its
   *  own — see the hit layer below for why. */
  const cls = (id: NodeId) => `pipe-node ${active === id ? "is-active" : ""}`;

  return (
    <div className="relative w-full">
      {/* The SVG is decorative; the HTML hit layer further down is the
          interactive surface. This sentence is the accessible description of
          the picture as a whole. */}
      <p className="sr-only">{DIAGRAM_SUMMARY}</p>

      <svg
        className="flow w-full h-auto block"
        viewBox={`0 0 ${VB_W} ${VB_H}`}
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
        focusable="false"
      >
        <defs>
          <radialGradient id={`${uid}-core`} cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#2DD4BF" stopOpacity={0.34} />
            <stop offset="65%" stopColor="#2DD4BF" stopOpacity={0.05} />
            <stop offset="100%" stopColor="#2DD4BF" stopOpacity={0} />
          </radialGradient>
          <linearGradient id={`${uid}-debate`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#16283C" />
            <stop offset="100%" stopColor="#101A2B" />
          </linearGradient>
          {Object.entries(ARROW_COLORS).map(([name, color]) => (
            <marker
              key={name}
              id={`${uid}-arrow-${name}`}
              viewBox="0 0 10 10"
              refX="8"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto-start-reverse"
            >
              <path d="M0,1 L9,5 L0,9 z" fill={color} />
            </marker>
          ))}
        </defs>

        {/* ── Stage rail ─────────────────────────────────────────────────── */}
        {STAGES.map((s, i) => (
          <text
            key={s.n}
            x={STAGE_X[i]}
            y={26}
            textAnchor="middle"
            className="stage-label"
          >
            <tspan className="stage-num">{String(s.n).padStart(2, "0")}</tspan>
            <tspan dx="8">{s.label.toUpperCase()}</tspan>
          </text>
        ))}

        {/* ── Connectors ─────────────────────────────────────────────────── */}
        {EDGES.map((e) => (
          <path
            key={e.id}
            className={`flowline ${e.dashed ? "dashed-opt" : ""}`}
            style={{ stroke: e.color }}
            d={e.d}
            markerEnd={e.arrow ? `url(#${uid}-arrow-${e.arrow})` : undefined}
          />
        ))}

        {/* Packets travelling the wires. `offset-path` reuses the exact same
            `d` string as the visible path, so the two can never drift. */}
        {EDGES.map((e) => (
          <circle
            key={`dot-${e.id}`}
            className="flow-dot"
            r={3.4}
            cx={0}
            cy={0}
            fill={e.color}
            style={{
              offsetPath: `path('${e.d}')`,
              animationDuration: `${e.dur}s`,
              animationDelay: `${e.delay}s`,
            }}
          />
        ))}

        {/* Loop captions, each on a plate that breaks the wire behind it. */}
        <rect x={442} y={462} width={128} height={24} rx={6} fill="var(--color-bg)" />
        <text x={506} y={478} textAnchor="middle" className="node-tag" fill="var(--color-rebuttal)">
          NEXT ROUND
        </text>
        <rect x={1071} y={462} width={132} height={24} rx={6} fill="var(--color-bg)" />
        <text x={1137} y={478} textAnchor="middle" className="node-tag" fill="var(--color-human)">
          ASK AGAIN
        </text>

        {/* ── Stage 1 · inputs ───────────────────────────────────────────── */}
        <AgentCard id="bull" box={BOX.bull} color="var(--color-bull)" cls={cls} />
        <AgentCard id="bear" box={BOX.bear} color="var(--color-bear)" cls={cls} />
        <AgentCard id="quant" box={BOX.quant} color="var(--color-quant)" cls={cls} />

        {/* Separator: the three agents are automatic, what follows is yours. */}
        <line x1={14} y1={330} x2={200} y2={330} stroke="var(--color-panel-line)" />
        <text x={14} y={348} className="node-tag" fill="var(--color-ink-dim)">
          OPTIONAL
        </text>

        <g className={cls("research")}>
          <rect
            {...BOX.research}
            rx={12}
            fill="rgba(251,191,36,0.05)"
            stroke="var(--color-human)"
            strokeOpacity={0.6}
            strokeDasharray="5 4"
          />
          <circle cx={34} cy={385} r={5} fill="var(--color-human)" />
          <text x={48} y={390} className="node-label" fill="var(--color-human)">
            Your research
          </text>
          <text x={28} y={412} className="node-sub" fill="var(--color-human)" opacity={0.85}>
            OPTIONAL HUMAN INPUT
          </text>
        </g>

        {/* ── Stage 2 · debate (the consolidator, deliberately the largest) ─ */}
        <g className={cls("debate")}>
          <rect
            {...BOX.debate}
            rx={16}
            fill={`url(#${uid}-debate)`}
            stroke="var(--color-teal)"
            strokeOpacity={0.28}
            strokeWidth={1.4}
          />
          <rect
            {...BOX.debate}
            rx={16}
            className="node-halo"
            fill="none"
            stroke="var(--color-teal)"
            style={{ animationDelay: "0.6s" }}
          />
          <text x={374} y={138} textAnchor="middle" className="node-label-lg">
            Debate
          </text>
          <text x={374} y={160} textAnchor="middle" className="node-sub">
            SHARED CONTEXT
          </text>
          <line x1={280} y1={182} x2={468} y2={182} stroke="var(--color-panel-line)" />

          {[
            { y: 216, c: "var(--color-bull)", t: "BULL THESIS" },
            { y: 246, c: "var(--color-bear)", t: "BEAR THESIS" },
            { y: 276, c: "var(--color-quant)", t: "QUANT MODEL" },
            { y: 306, c: "var(--color-human)", t: "YOUR RESEARCH" },
          ].map((row, i) => (
            <g key={row.t}>
              <circle cx={292} cy={row.y - 4} r={4} fill={row.c} />
              <text x={306} y={row.y} className="node-tag">
                {row.t}
              </text>
              <rect
                x={418}
                y={row.y - 10}
                width={44}
                height={5}
                rx={2.5}
                fill={row.c}
                opacity={0.22}
              />
              <rect
                x={418}
                y={row.y - 10}
                width={44}
                height={5}
                rx={2.5}
                fill={row.c}
                className="merge-bar"
                style={{ animationDelay: `${i * 0.28}s` }}
              />
            </g>
          ))}

          <line x1={280} y1={332} x2={468} y2={332} stroke="var(--color-panel-line)" />
          <text x={374} y={358} textAnchor="middle" className="node-tag" fill="var(--color-teal)">
            MERGED · DEDUPED
          </text>
          <rect x={280} y={378} width={188} height={6} rx={3} fill="var(--color-panel-line)" />
          <rect x={280} y={378} width={188} height={6} rx={3} fill="var(--color-teal)" className="scan-bar" />
        </g>

        {/* ── Stage 3 · rebuttal ─────────────────────────────────────────── */}
        <g className={cls("rebuttal")}>
          <rect
            {...BOX.rebuttal}
            rx={14}
            fill="var(--color-panel)"
            stroke="var(--color-rebuttal)"
            strokeOpacity={0.55}
            strokeWidth={1.4}
          />
          <rect
            {...BOX.rebuttal}
            rx={14}
            className="node-halo"
            fill="none"
            stroke="var(--color-rebuttal)"
            style={{ animationDelay: "1.2s" }}
          />
          <text x={638} y={218} textAnchor="middle" className="node-label">
            Rebuttal
          </text>
          <text x={638} y={240} textAnchor="middle" className="node-sub">
            CROSS-EXAMINATION
          </text>
          <line x1={566} y1={258} x2={710} y2={258} stroke="var(--color-panel-line)" />
          <circle cx={574} cy={276} r={3.5} fill="var(--color-bull)" />
          <text x={588} y={280} className="node-tag">BULL ANSWERS BEAR</text>
          <circle cx={574} cy={300} r={3.5} fill="var(--color-bear)" />
          <text x={588} y={304} className="node-tag">BEAR ANSWERS BULL</text>
        </g>

        {/* ── Stage 4 · consensus ────────────────────────────────────────── */}
        <circle cx={CONSENSUS.cx} cy={CONSENSUS.cy} r={CONSENSUS.glow} fill={`url(#${uid}-core)`} />
        <g className={cls("consensus")}>
          <circle
            className="core-ring"
            cx={CONSENSUS.cx}
            cy={CONSENSUS.cy}
            r={CONSENSUS.ring}
            fill="none"
            stroke="var(--color-teal)"
            strokeOpacity={0.45}
            strokeWidth={1.3}
          />
          <circle
            cx={CONSENSUS.cx}
            cy={CONSENSUS.cy}
            r={CONSENSUS.r}
            fill="var(--color-panel)"
            stroke="var(--color-teal)"
            strokeOpacity={0.8}
            strokeWidth={1.6}
          />
          <text x={CONSENSUS.cx} y={244} textAnchor="middle" className="core-title">
            Consensus
          </text>
          {/* Two lines, not one: a single "CONFIDENCE-WEIGHTED" run reads as if
              it is bursting the disc at this radius. */}
          <text x={CONSENSUS.cx} y={266} textAnchor="middle" className="core-sub">
            CONFIDENCE
          </text>
          <text x={CONSENSUS.cx} y={281} textAnchor="middle" className="core-sub">
            WEIGHTED
          </text>
        </g>
        <g>
          <rect
            x={811}
            y={128}
            width={82}
            height={21}
            rx={10.5}
            fill="rgba(45,212,191,0.12)"
            stroke="var(--color-teal)"
            strokeOpacity={0.7}
          />
          <circle cx={827} cy={138.5} r={3.3} fill="var(--color-teal)" className="animate-blink-dot" />
          <text x={837} y={142} className="node-tag" fill="var(--color-teal)">
            AI AGENT
          </text>
        </g>

        {/* ── Stage 5a · verdict (the quarter) ───────────────────────────── */}
        <g className={cls("verdict")}>
          <rect
            {...BOX.verdict}
            rx={16}
            fill="var(--color-panel)"
            stroke="var(--color-teal)"
            strokeOpacity={0.4}
          />
          <rect
            {...BOX.verdict}
            rx={16}
            className="node-halo"
            fill="none"
            stroke="var(--color-teal)"
            style={{ animationDelay: "1.8s" }}
          />
          <text x={1016} y={132} className="verdict-k">VERDICT · THIS QUARTER</text>
          <line x1={1016} y1={144} x2={1224} y2={144} stroke="var(--color-panel-line)" />

          {EXAMPLE_OUTCOME.directions.map((d, i) => {
            const on = d === EXAMPLE_OUTCOME.selected;
            return (
              <g key={d}>
                <rect
                  x={1016 + i * 72}
                  y={156}
                  width={64}
                  height={24}
                  rx={7}
                  fill={on ? "rgba(45,212,191,0.16)" : "transparent"}
                  stroke={on ? "var(--color-teal)" : "var(--color-panel-line)"}
                  strokeOpacity={on ? 0.8 : 1}
                />
                <text
                  x={1016 + i * 72 + 32}
                  y={172}
                  textAnchor="middle"
                  className="node-tag"
                  fill={on ? "var(--color-teal)" : "var(--color-ink-dim)"}
                >
                  {d}
                </text>
              </g>
            );
          })}

          <text x={1016} y={202} className="verdict-k">CONFIDENCE</text>
          <text x={1224} y={204} textAnchor="end" className="verdict-c">
            {EXAMPLE_OUTCOME.confidence}%
          </text>
          <rect x={1016} y={212} width={208} height={6} rx={3} fill="var(--color-panel-line)" />
          <rect
            x={1016}
            y={212}
            width={(208 * EXAMPLE_OUTCOME.confidence) / 100}
            height={6}
            rx={3}
            fill="var(--color-teal)"
          />
        </g>

        {/* ── Stage 5b · research thesis (the long horizon) ──────────────── */}
        <g className={cls("thesis")}>
          <rect
            {...BOX.thesis}
            rx={16}
            fill="var(--color-panel)"
            stroke="var(--color-research)"
            strokeOpacity={0.5}
          />
          <rect
            {...BOX.thesis}
            rx={16}
            className="node-halo"
            fill="none"
            stroke="var(--color-research)"
            style={{ animationDelay: "2s" }}
          />
          <text x={1016} y={292} className="node-label" fill="var(--color-research)">
            Research thesis
          </text>
          <text x={1016} y={314} className="node-sub">
            12–36 MONTH VIEW
          </text>
          <line x1={1016} y1={330} x2={1224} y2={330} stroke="var(--color-panel-line)" />
          <circle cx={1022} cy={348} r={3.5} fill="var(--color-research)" />
          <text x={1036} y={352} className="node-tag">STRUCTURAL BULL / BEAR</text>
          <circle cx={1022} cy={370} r={3.5} fill="var(--color-research)" />
          <text x={1036} y={374} className="node-tag">CATALYSTS &amp; RISKS</text>
        </g>

        {/* ── Stage 6 · follow-up conversation ───────────────────────────── */}
        <g className={cls("followup")}>
          <rect
            {...BOX.followup}
            rx={16}
            fill="rgba(251,191,36,0.05)"
            stroke="var(--color-human)"
            strokeOpacity={0.6}
            strokeWidth={1.4}
          />
          <rect
            {...BOX.followup}
            rx={16}
            className="node-halo"
            fill="none"
            stroke="var(--color-human)"
            style={{ animationDelay: "2.4s" }}
          />
          <text x={1320} y={216} className="node-label" fill="var(--color-human)">
            Ask the agent
          </text>
          <text x={1320} y={238} className="node-sub" fill="var(--color-human)" opacity={0.85}>
            OPEN-ENDED Q&amp;A
          </text>
          <line x1={1320} y1={256} x2={1526} y2={256} stroke="var(--color-panel-line)" />
          <circle cx={1326} cy={274} r={3.5} fill="var(--color-human)" />
          <text x={1340} y={278} className="node-tag">CHALLENGE ASSUMPTIONS</text>
          <circle cx={1326} cy={298} r={3.5} fill="var(--color-human)" />
          <text x={1340} y={302} className="node-tag">TRACE THE EVIDENCE</text>
        </g>
      </svg>

      {/* ── Hit layer ────────────────────────────────────────────────────────
          Real <button>s laid over the drawing, rather than handlers on the
          SVG groups. Three reasons: an SVG <g> only receives pointer events
          where its children actually paint, so the gaps between a card's text
          runs were dead zones; <button> gives Tab order and screen-reader
          semantics without putting tabindex on SVG children; and a CSS focus
          ring on an HTML box is predictable in a way one on a <g> is not.

          Percentages work because the svg above is w-full/h-auto with no
          preserveAspectRatio override, so viewBox units map linearly onto this
          wrapper's box at every width. */}
      <div className="absolute inset-0">
        {HIT_ORDER.map((id) => {
          const h = HOTSPOT[id];
          const node = PIPELINE_NODES[id];
          return (
            <button
              key={id}
              type="button"
              className={`pipe-hit ${h.round ? "rounded-full" : ""}`}
              style={{
                left: `${(h.x / VB_W) * 100}%`,
                top: `${(h.y / VB_H) * 100}%`,
                width: `${(h.w / VB_W) * 100}%`,
                height: `${(h.h / VB_H) * 100}%`,
              }}
              aria-label={`${node.title}. ${node.blurb}`}
              onMouseEnter={() => setActive(id)}
              onMouseLeave={() => setActive((c) => (c === id ? null : c))}
              onFocus={() => setActive(id)}
              onBlur={() => setActive((c) => (c === id ? null : c))}
            />
          );
        })}
      </div>

      {/* ── Tooltip ──────────────────────────────────────────────────────── */}
      {active && (
        <div
          className="pipe-tip"
          style={{
            left: `${(ANCHOR[active].x / VB_W) * 100}%`,
            top: `${(ANCHOR[active].y / VB_H) * 100}%`,
            transform:
              ANCHOR[active].side === "right"
                ? "translate(14px, -50%)"
                : "translate(calc(-100% - 14px), -50%)",
          }}
          role="tooltip"
          aria-hidden="true"
        >
          <div className="flex items-center gap-2 mb-1.5">
            <span
              className="w-2 h-2 rounded-full shrink-0"
              style={{ background: `var(--color-${accentVar(active)})` }}
            />
            <span className="font-display font-semibold text-[14px] text-ink">
              {PIPELINE_NODES[active].title}
            </span>
            <span className="eyebrow text-ink-dim ml-auto">
              {String(PIPELINE_NODES[active].stage).padStart(2, "0")}
            </span>
          </div>
          <p className="font-body text-[12.5px] leading-[1.55] text-ink-mute">
            {PIPELINE_NODES[active].blurb}
          </p>
        </div>
      )}
    </div>
  );
}

/** Maps an accent name onto the CSS custom-property suffix it uses. */
function accentVar(id: NodeId): string {
  const a = PIPELINE_NODES[id].accent;
  return a === "neutral" ? "ink-dim" : a;
}

const CARD_DELAY: Partial<Record<NodeId, string>> = {
  bull: "0s",
  bear: "0.2s",
  quant: "0.4s",
};

function AgentCard({
  id,
  box,
  color,
  cls,
}: {
  id: NodeId;
  box: Box;
  color: string;
  cls: (id: NodeId) => string;
}) {
  const node = PIPELINE_NODES[id];
  return (
    <g className={cls(id)}>
      <rect
        {...box}
        rx={12}
        fill="var(--color-panel)"
        stroke={color}
        strokeOpacity={0.85}
        strokeWidth={1.5}
      />
      <rect
        {...box}
        rx={12}
        className="node-halo"
        fill="none"
        stroke={color}
        style={{ animationDelay: CARD_DELAY[id] ?? "0s" }}
      />
      <circle cx={box.x + 20} cy={box.y + 25} r={5} fill={color} />
      <text x={box.x + 34} y={box.y + 30} className="node-label">
        {node.title.replace(" agent", "")}
      </text>
      <text x={box.x + 14} y={box.y + 52} className="node-sub">
        {node.kicker}
      </text>
      {/* Affordance: tells you the card has more behind it before you hover. */}
      <g className="node-hint">
        <circle
          cx={box.x + box.w - 18}
          cy={box.y + 25}
          r={7.5}
          fill="none"
          stroke="var(--color-ink-dim)"
          strokeOpacity={0.55}
        />
        <text
          x={box.x + box.w - 18}
          y={box.y + 29}
          textAnchor="middle"
          className="node-tag"
          fill="var(--color-ink-dim)"
        >
          i
        </text>
      </g>
    </g>
  );
}
