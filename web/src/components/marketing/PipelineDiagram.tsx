import React from "react";
import { PipelineData, DEFAULT_PIPELINE } from "./pipeline.types";

interface PipelineDiagramProps {
  data?: PipelineData;
}

export default function PipelineDiagram({ data = DEFAULT_PIPELINE }: PipelineDiagramProps) {
  return (
    <svg
      className="flow w-full h-auto block"
      viewBox="0 0 700 600"
      xmlns="http://www.w3.org/2000/svg"
      role="img"
      aria-label="Pipeline: Bull, Quant, and Bear agents plus your research feed a debate round, weighed by the Consensus agent into a confidence-scored verdict."
    >
      <defs>
        <radialGradient id="coreGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#2DD4BF" stopOpacity={0.35} />
          <stop offset="70%" stopColor="#2DD4BF" stopOpacity={0.05} />
          <stop offset="100%" stopColor="#2DD4BF" stopOpacity={0} />
        </radialGradient>
      </defs>

      {/* Connectors: agents -> debate */}
      <path
        className="flowline"
        style={{ stroke: "var(--color-bull)" }}
        d="M170,116 C230,116 235,270 292,285"
      />
      <path
        className="flowline"
        style={{ stroke: "var(--color-quant)" }}
        d="M170,300 C220,300 235,300 292,300"
      />
      <path
        className="flowline"
        style={{ stroke: "var(--color-bear)" }}
        d="M170,484 C230,484 235,330 292,315"
      />

      {/* Debate -> consensus */}
      <path
        className="flowline"
        style={{ stroke: "var(--color-teal)" }}
        d="M420,300 C470,300 480,270 502,258"
      />

      {/* Your research -> debate (optional) */}
      <path
        className="flowline dashed-opt"
        style={{ stroke: "var(--color-human)" }}
        d="M368,472 C368,432 356,392 356,350"
      />

      {/* Consensus -> verdict */}
      <path
        className="flowline"
        style={{ stroke: "var(--color-teal)" }}
        d="M565,330 C565,370 565,388 565,410"
      />

      {/* AGENT CHIPS */}
      {/* Bull */}
      <g className="node select-none cursor-default">
        <rect
          x="30"
          y="82"
          width="140"
          height="68"
          rx="12"
          fill="var(--color-panel)"
          stroke="var(--color-bull)"
          strokeOpacity={0.9}
          strokeWidth={1.5}
        />
        <circle cx="52" cy="106" r="5" fill="var(--color-bull)" />
        <text x="68" y="111" className="node-label">Bull</text>
        <text x="46" y="132" className="node-sub">BUYSIDE CASE</text>
      </g>

      {/* Quant */}
      <g className="node select-none cursor-default">
        <rect
          x="30"
          y="266"
          width="140"
          height="68"
          rx="12"
          fill="var(--color-panel)"
          stroke="var(--color-quant)"
          strokeOpacity={0.9}
          strokeWidth={1.5}
        />
        <circle cx="52" cy="290" r="5" fill="var(--color-quant)" />
        <text x="68" y="295" className="node-label">Quant</text>
        <text x="46" y="316" className="node-sub">OPTIONS · MAX PAIN</text>
      </g>

      {/* Bear */}
      <g className="node select-none cursor-default">
        <rect
          x="30"
          y="450"
          width="140"
          height="68"
          rx="12"
          fill="var(--color-panel)"
          stroke="var(--color-bear)"
          strokeOpacity={0.9}
          strokeWidth={1.5}
        />
        <circle cx="52" cy="474" r="5" fill="var(--color-bear)" />
        <text x="68" y="479" className="node-label">Bear</text>
        <text x="46" y="500" className="node-sub">SHORT CASE</text>
      </g>

      {/* DEBATE */}
      <g className="node select-none cursor-default">
        <rect
          x="292"
          y="252"
          width="128"
          height="96"
          rx="12"
          fill="var(--color-panel)"
          stroke="var(--color-panel-line)"
        />
        <text x="356" y="292" textAnchor="middle" className="node-label">Debate</text>
        <text x="356" y="312" textAnchor="middle" className="node-sub">&amp; REBUTTAL</text>
        <text x="356" y="330" textAnchor="middle" className="node-tag" fill="var(--color-ink-dim)">round 1 of 1</text>
      </g>

      {/* CONSENSUS CORE */}
      <circle cx="565" cy="255" r="115" fill="url(#coreGlow)" />
      <circle
        className="core-ring"
        cx="565"
        cy="255"
        r="82"
        fill="none"
        stroke="var(--color-teal)"
        strokeOpacity={0.5}
        strokeWidth={1.3}
      />
      <circle
        cx="565"
        cy="255"
        r="66"
        fill="var(--color-panel)"
        stroke="var(--color-teal)"
        strokeOpacity={0.8}
        strokeWidth={1.6}
      />
      <text x="565" y="250" textAnchor="middle" className="core-title">Consensus</text>
      <text x="565" y="270" textAnchor="middle" className="core-sub">CONFIDENCE-WEIGHTED</text>
      
      {/* AI AGENT badge */}
      <g className="select-none cursor-default">
        <rect
          x="524"
          y="158"
          width="82"
          height="21"
          rx="10.5"
          fill="rgba(45, 212, 191, 0.12)"
          stroke="var(--color-teal)"
          strokeOpacity={0.7}
        />
        <circle cx="540" cy="168.5" r="3.3" fill="var(--color-teal)" />
        <text x="550" y="172" className="node-tag" fill="var(--color-teal)">AI AGENT</text>
      </g>

      {/* YOUR RESEARCH (optional / human) */}
      <g className="node select-none cursor-default">
        <rect
          x="300"
          y="472"
          width="140"
          height="66"
          rx="12"
          fill="rgba(251, 191, 36, 0.04)"
          stroke="var(--color-human)"
          strokeOpacity={0.6}
          strokeDasharray="4 4"
        />
        <text x="316" y="500" className="node-label" style={{ fill: "var(--color-human)" }}>Your research</text>
        <text x="316" y="520" className="node-sub" style={{ fill: "var(--color-human)", opacity: 0.8 }}>OPTIONAL HUMAN INPUT</text>
      </g>

      {/* VERDICT CARD */}
      <g className="node select-none cursor-default">
        <rect
          x="470"
          y="410"
          width="190"
          height="130"
          rx="14"
          fill="var(--color-panel)"
          stroke="var(--color-teal)"
          strokeOpacity={0.35}
        />
        <text x="490" y="440" className="verdict-k">VERDICT · {data.ticker}</text>
        <text x="490" y="470" className="verdict-v">{data.verdict}</text>
        <line x1={490} y1={484} x2={640} y2={484} stroke="var(--color-panel-line)" />
        <text x="490" y="508" className="verdict-k">CONFIDENCE</text>
        <text x="490" y="530" className="verdict-c">{data.confidence}</text>
      </g>
    </svg>
  );
}
