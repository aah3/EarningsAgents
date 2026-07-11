"use client";

import React from "react";
import Link from "next/link";
import { SignInButton, SignedIn, SignedOut } from "@clerk/nextjs";
import PipelineDiagram from "./PipelineDiagram";
import { PipelineData, DEFAULT_PIPELINE } from "./pipeline.types";

interface HeroProps {
  data?: PipelineData;
}

export default function Hero({ data = DEFAULT_PIPELINE }: HeroProps) {
  return (
    <section className="w-full max-w-[1240px] mx-auto grid grid-cols-[minmax(0,0.86fr)_minmax(0,1.14fr)] max-[940px]:grid-cols-1 gap-[56px] max-[940px]:gap-10 items-center px-10 max-[940px]:px-6 pt-14 pb-[90px] max-[940px]:pb-[70px]">
      {/* Left Column: Copy */}
      <div className="copy flex flex-col items-start">
        {/* Eyebrow Pill */}
        <span className="eyebrow font-mono text-[12px] tracking-[0.14em] uppercase text-teal border border-panel-line bg-[rgba(45,212,191,0.05)] px-[13px] py-[7px] rounded-full inline-flex items-center gap-[9px] mb-[26px] select-none">
          <span className="dot w-[7px] h-[7px] rounded-full bg-teal shadow-[0_0_10px_rgba(45,212,191,0.8)] eyebrow-dot-blink" />
          Multi-agent earnings intelligence
        </span>

        {/* H1 Headline */}
        <h1 className="font-display font-semibold text-[clamp(2.4rem,4.4vw,3.7rem)] leading-[1.04] tracking-[-0.025em] bg-gradient-to-b from-[#FFFFFF] to-[#B9C4DA] bg-clip-text text-transparent mb-[22px]">
          Earnings predictions,
          <br />
          settled by{" "}
          <span className="bg-gradient-to-r from-teal to-[#7DE8DA] bg-clip-text text-transparent">
            debate.
          </span>
        </h1>

        {/* Subheading Description */}
        <p className="sub font-body text-[17.5px] leading-[1.62] text-ink-mute max-w-[46ch] mb-[34px]">
          Bull, Bear, and Quant agents each build a case, then argue it out in a
          rebuttal round — with <strong className="font-semibold text-ink">your own research</strong> thrown
          into the debate. A <strong className="font-semibold text-ink">Consensus agent</strong> weighs the
          arguments into one confidence-scored call. And it&apos;s not a one-shot
          verdict: keep questioning the Consensus agent to unpack its reasoning
          until you trust the decision.
        </p>

        {/* CTA Row */}
        <div className="cta-row flex items-center gap-4 flex-wrap mb-[26px]">
          <SignedOut>
            <SignInButton mode="modal">
              <button
                className="btn-primary font-body text-[15.5px] font-semibold text-[#04231F] bg-gradient-to-br from-teal to-teal-deep px-[26px] py-3.5 rounded-[12px] transition-all duration-150 hover:-translate-y-0.5 focus-visible:ring-2 focus-visible:ring-teal focus-visible:ring-offset-2 focus-visible:ring-offset-bg outline-none cursor-pointer"
                style={{ boxShadow: "0 8px 26px rgba(45, 212, 191, 0.32)" }}
              >
                Run a live prediction
              </button>
            </SignInButton>
          </SignedOut>
          <SignedIn>
            <Link
              href="/dashboard"
              className="btn-primary font-body text-[15.5px] font-semibold text-[#04231F] bg-gradient-to-br from-teal to-teal-deep px-[26px] py-3.5 rounded-[12px] transition-all duration-150 hover:-translate-y-0.5 focus-visible:ring-2 focus-visible:ring-teal focus-visible:ring-offset-2 focus-visible:ring-offset-bg outline-none"
              style={{ boxShadow: "0 8px 26px rgba(45, 212, 191, 0.32)" }}
            >
              Run a live prediction
            </Link>
          </SignedIn>
          <Link
            href="#"
            className="btn-ghost font-body text-[15.5px] font-medium text-ink bg-transparent px-[22px] py-3.5 rounded-[12px] border border-panel-line inline-flex items-center gap-[9px] hover:border-ink-dim hover:bg-white/[0.02] transition-colors duration-180 focus-visible:ring-2 focus-visible:ring-teal focus-visible:ring-offset-2 focus-visible:ring-offset-bg outline-none"
          >
            <span className="play w-5 h-5 rounded-full bg-white/[0.08] grid place-items-center text-[9px]">
              ▶
            </span>
            Watch 2-min demo
          </Link>
        </div>

        {/* Proof Line */}
        <div className="proof font-mono text-[12.5px] text-ink-dim tracking-[0.02em] flex items-center gap-2.5 select-none">
          <span className="live w-1.5 h-1.5 rounded-full bg-bull shadow-[0_0_8px_var(--color-bull)]" />
          Every call scored on a public Brier leaderboard — no cherry-picking.
        </div>
      </div>

      {/* Right Column: Pipeline Diagram Wrap */}
      <div className="diagram-wrap max-[940px]:order-2 relative border border-panel-line rounded-[20px] bg-gradient-to-b from-[var(--color-panel-sunk)]/90 to-[#070A12]/60 p-5 shadow-[inset_0_1px_0_rgba(255,255,255,0.03),0_30px_80px_rgba(0,0,0,0.5)] overflow-hidden before:content-[''] before:absolute before:inset-0 before:bg-[linear-gradient(rgba(255,255,255,0.025)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.025)_1px,transparent_1px)] before:bg-[size:34px_34px] before:pointer-events-none">
        {/* Diagram Head */}
        <div className="diagram-head relative flex justify-between items-center font-mono text-[11px] tracking-[0.12em] text-ink-dim uppercase mb-1.5 px-1 py-0.5 select-none z-10">
          <span>PIPELINE · {data.ticker} Q3</span>
          <span className="status text-teal">● {data.status}</span>
        </div>

        {/* SVG Flow diagram */}
        <div className="relative z-10 w-full">
          <PipelineDiagram data={data} />
        </div>
      </div>
    </section>
  );
}
