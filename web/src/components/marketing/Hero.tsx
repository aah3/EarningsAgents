"use client";

import React from "react";
import Link from "next/link";
import { SignInButton, SignedIn, SignedOut } from "@clerk/nextjs";
import { ArrowRight, MousePointerClick } from "lucide-react";
import Container from "./Container";
import PipelineDiagram from "./PipelineDiagram";
import PipelineStepper from "./PipelineStepper";

/**
 * Copy on top, diagram underneath at full container width.
 *
 * The previous hero put the pipeline in a right-hand column beside the
 * paragraph, which squeezed a five-stage flow into ~640px and left both halves
 * cramped. Stacking gives the diagram the whole 1440 and lets the copy sit at a
 * proper centred measure.
 */
export default function Hero() {
  return (
    <section className="relative pt-12 md:pt-16 pb-16 md:pb-24">
      {/* Ambient wash behind the headline. Sits under everything, ignores input. */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-0 top-0 h-[520px] hero-aurora"
      />

      <Container className="relative">
        {/* ── Copy block ───────────────────────────────────────────────── */}
        <div className="flex flex-col items-center text-center max-w-[860px] mx-auto">
          <span className="font-mono text-[11.5px] tracking-[0.14em] uppercase text-teal border border-teal/20 bg-teal/[0.05] px-[13px] py-[7px] rounded-full inline-flex items-center gap-[9px] mb-7 select-none">
            <span className="w-[7px] h-[7px] rounded-full bg-teal shadow-[0_0_10px_rgba(45,212,191,0.8)] animate-blink-dot" />
            Multi-agent earnings intelligence
          </span>

          <h1 className="font-display font-semibold text-[clamp(2.5rem,5.2vw,4.25rem)] leading-[1.03] tracking-[-0.028em] bg-gradient-to-b from-white to-[#B9C4DA] bg-clip-text text-transparent mb-6">
            Earnings predictions,
            <br />
            settled by{" "}
            <span className="bg-gradient-to-r from-teal to-[#7DE8DA] bg-clip-text text-transparent">
              debate.
            </span>
          </h1>

          <p className="font-body text-[17px] md:text-[18.5px] leading-[1.62] text-ink-mute max-w-[62ch] mb-9">
            Bull, Bear, and Quant agents each build a case, then argue it out in a
            rebuttal round — with{" "}
            <strong className="font-semibold text-ink">your own research</strong>{" "}
            thrown into the debate. A{" "}
            <strong className="font-semibold text-ink">Consensus agent</strong>{" "}
            weighs the arguments into a confidence-scored call on the quarter and
            a{" "}
            <strong className="font-semibold text-ink">12–36 month research thesis</strong>.
            And neither is a one-shot answer: keep questioning the Consensus agent
            to unpack its reasoning until you trust the decision.
          </p>

          <div className="flex items-center justify-center gap-3.5 flex-wrap mb-7">
            <SignedOut>
              <SignInButton mode="modal">
                <button
                  className="btn-primary font-body text-[15.5px] font-semibold text-[#04231F] bg-gradient-to-br from-teal to-teal-deep px-[26px] py-3.5 rounded-[12px] transition-transform duration-150 hover:-translate-y-0.5 focus-visible:ring-2 focus-visible:ring-teal focus-visible:ring-offset-2 focus-visible:ring-offset-bg outline-none cursor-pointer"
                  style={{ boxShadow: "0 8px 26px rgba(45, 212, 191, 0.32)" }}
                >
                  Run a live prediction
                </button>
              </SignInButton>
            </SignedOut>
            <SignedIn>
              <Link
                href="/dashboard"
                className="btn-primary font-body text-[15.5px] font-semibold text-[#04231F] bg-gradient-to-br from-teal to-teal-deep px-[26px] py-3.5 rounded-[12px] transition-transform duration-150 hover:-translate-y-0.5 focus-visible:ring-2 focus-visible:ring-teal focus-visible:ring-offset-2 focus-visible:ring-offset-bg outline-none"
                style={{ boxShadow: "0 8px 26px rgba(45, 212, 191, 0.32)" }}
              >
                Run a live prediction
              </Link>
            </SignedIn>
            <Link
              href="/learn"
              className="font-body text-[15.5px] font-medium text-ink px-[22px] py-3.5 rounded-[12px] border border-panel-line inline-flex items-center gap-2 hover:border-ink-dim hover:bg-white/[0.03] transition-colors duration-200 focus-visible:ring-2 focus-visible:ring-teal focus-visible:ring-offset-2 focus-visible:ring-offset-bg outline-none group"
            >
              Read the methodology
              <ArrowRight className="w-4 h-4 text-ink-mute group-hover:translate-x-0.5 transition-transform" />
            </Link>
          </div>

          <div className="font-mono text-[12.5px] text-ink-dim tracking-[0.02em] flex items-center gap-2.5 select-none">
            <span className="w-1.5 h-1.5 rounded-full bg-bull shadow-[0_0_8px_var(--color-bull)]" />
            Every call scored on a public Brier leaderboard — no cherry-picking.
          </div>
        </div>

        {/* ── Diagram ──────────────────────────────────────────────────── */}
        <div className="mt-14 md:mt-20 diagram-panel relative rounded-[22px] border border-panel-line bg-gradient-to-b from-[var(--color-panel-sunk)]/90 to-[#070A12]/60 p-4 md:p-6 overflow-hidden">
          <div className="relative z-10 flex items-center justify-between gap-4 font-mono text-[11px] tracking-[0.12em] text-ink-dim uppercase mb-3 md:mb-1 px-1 select-none">
            <span>Pipeline · how a call is made</span>
            <span className="hidden wide:inline-flex items-center gap-1.5 normal-case tracking-normal font-body text-[12px] text-ink-mute">
              <MousePointerClick className="w-3.5 h-3.5 text-teal" />
              Hover any node
            </span>
            <span className="text-teal">● Example run</span>
          </div>

          {/* `wide` is 1360px (see globals.css), not a stock breakpoint. The
              SVG is 1560 units wide and its stage is the viewport minus the
              container gutters and this panel's padding, so it renders at
              roughly (viewport - 128) / 1560: at 1280 that is 0.73 and the
              10.5px mono sub-labels land at 7.6px, which is unreadable. 1360
              holds the floor near 0.78 — 8.2px sub-labels, 14px node titles —
              and still covers 1366 laptops. Below it the stepper says the same
              thing at full size. Scale plateaus at ~0.89 once the container
              caps at 1520. */}
          <div className="relative z-10 hidden wide:block">
            <PipelineDiagram />
          </div>
          <div className="relative z-10 wide:hidden pt-2 pb-1">
            <PipelineStepper />
          </div>
        </div>
      </Container>
    </section>
  );
}
