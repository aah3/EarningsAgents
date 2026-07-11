"use client";

import React from "react";
import Link from "next/link";
import SiteNav from "@/components/marketing/SiteNav";
import { ArrowLeft, BookOpen, BarChart3, ShieldAlert, Award } from "lucide-react";

export default function LearnPage() {
  return (
    <main className="min-h-screen bg-bg text-ink pb-24">
      <SiteNav />

      <div className="w-full max-w-[800px] mx-auto px-6 pt-12 md:pt-16">
        {/* Back Link */}
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-ink-mute hover:text-teal font-body text-sm font-semibold transition-colors mb-10 group"
        >
          <ArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
          Back to Home
        </Link>

        {/* Header section */}
        <header className="mb-14">
          <span className="eyebrow font-mono text-[11px] tracking-[0.15em] uppercase text-teal border border-panel-line bg-[rgba(45,212,191,0.05)] px-3 py-1.5 rounded-full inline-flex items-center gap-2 mb-6">
            Methodology & Science
          </span>
          <h1 className="font-display font-semibold text-4xl md:text-5xl leading-tight text-white mb-6">
            How EarningsAI Forecasts Market Direction
          </h1>
          <p className="text-lg font-body font-normal text-ink-mute leading-relaxed">
            An in-depth look at our multi-agent model architecture, consensus pricing, options market signals, and Brier score tracking.
          </p>
        </header>

        {/* Section 1: How it works / Pipeline */}
        <section id="how-it-works" className="scroll-mt-24 mb-16 border-t border-panel-line pt-12">
          <h2 className="flex items-center gap-3 font-display font-semibold text-2xl text-white mb-6">
            <BookOpen className="w-6 h-6 text-teal" />
            1. Multi-Agent Debate Architecture
          </h2>
          <div className="space-y-6 font-body font-normal text-ink-mute leading-relaxed text-[15px]">
            <p>
              Traditional financial models rely on a single set of assumptions. EarningsAI replicates a professional investment committee by deploying three distinct specialist agents:
            </p>
            <ul className="space-y-4 pl-4 border-l-2 border-panel-line">
              <li>
                <strong className="text-white">The Bull Agent:</strong> Identifies potential catalysts, low valuation support, secular growth tails, and optimistic scenarios.
              </li>
              <li>
                <strong className="text-white">The Bear Agent:</strong> Searches for execution risks, margin pressures, competitive headwinds, and inventory/distribution channel build-up.
              </li>
              <li>
                <strong className="text-white">The Quant Agent:</strong> Processes statistical models, options pricing metrics, historical surprise probabilities, and volatility statistics.
              </li>
            </ul>
            <p>
              Once each agent builds its initial case, they enter a **Cross-Examination (Rebuttal) Round**. In this phase, the Bull and Bear agents analyze each other&apos;s cases, highlight logical inconsistencies, and challenge underlying assumptions. Finally, a **Consensus Agent** synthesizes the entire debate alongside any user-provided research to make a final confidence-scored forecast.
            </p>
          </div>
        </section>

        {/* Section 2: Analyst Upgrades & Expectations */}
        <section className="mb-16 border-t border-panel-line pt-12">
          <h2 className="flex items-center gap-3 font-display font-semibold text-2xl text-white mb-6">
            <BarChart3 className="w-6 h-6 text-teal" />
            2. Analyst Upgrades, Downgrades & Expectations
          </h2>
          <div className="space-y-6 font-body font-normal text-ink-mute leading-relaxed text-[15px]">
            <p>
              Sell-side research analysts (from investment banks like Goldman Sachs, Morgan Stanley, etc.) evaluate companies by projecting future cash flows, gross margins, and earnings per share (EPS). Upgrades and downgrades occur when a company’s performance deviates from consensus estimates or when macro factors change their cost of capital.
            </p>
            <p>
              However, corporate management frequently engages in **Expectations Management**. By guiding estimates slightly lower before an earnings print, they set a &quot;low bar&quot; that is easier to &quot;beat and raise&quot; (beating estimates and raising guidance), driving positive post-earnings stock momentum.
            </p>
            <p>
              Our agents analyze this dynamic by comparing **Consensus Estimates** against the **Options Market Implied Move**. If options are pricing a 10% move but consensus expectations are extremely conservative, a minor beat is often already priced in, leading to a &quot;sell the news&quot; price decline.
            </p>
          </div>
        </section>

        {/* Section 3: Brier Score */}
        <section className="mb-16 border-t border-panel-line pt-12">
          <h2 className="flex items-center gap-3 font-display font-semibold text-2xl text-white mb-6">
            <Award className="w-6 h-6 text-teal" />
            3. Measuring Accuracy: The Brier Score
          </h2>
          <div className="space-y-6 font-body font-normal text-ink-mute leading-relaxed text-[15px]">
            <p>
              To maintain absolute transparency and prevent &quot;cherry-picking&quot; of results, EarningsAI measures prediction accuracy using the **Brier Score**.
            </p>
            <div className="bg-[var(--color-panel-sunk)] border border-panel-line rounded-2xl p-6 my-6">
              <h4 className="font-mono text-xs text-teal uppercase tracking-widest mb-3">Formula</h4>
              <p className="font-mono text-lg text-white text-center py-4 bg-[#05070a] rounded-xl border border-panel-line">
                BS = (f - o)²
              </p>
              <div className="mt-4 text-xs space-y-2 text-ink-dim">
                <p>• <strong className="text-ink-mute">f</strong> = Forecast probability (e.g. 78% confidence = 0.78)</p>
                <p>• <strong className="text-ink-mute">o</strong> = Actual outcome (1 if the prediction direction is correct, 0 if incorrect)</p>
              </div>
            </div>
            <p>
              The Brier score is a **proper score function**, meaning that the best way to get a good score is to forecast your true subjective probability. It penalizes overconfidence on incorrect forecasts:
            </p>
            <ul className="space-y-3 list-disc list-inside pl-2">
              <li>
                <strong className="text-white">0.0 (Perfect Score):</strong> You predicted BEAT with 100% confidence, and the company beat estimates.
              </li>
              <li>
                <strong className="text-white">0.25 (Random Guessing):</strong> You assigned a 50% probability to the correct outcome.
              </li>
              <li>
                <strong className="text-white">1.0 (Absolute Worst):</strong> You predicted BEAT with 100% confidence, and the company missed estimates.
              </li>
            </ul>
            <p>
              By evaluating our models over multiple prints using the average Brier Score, we ensure that our AI consensus does not just guess directions, but correctly measures its own uncertainty.
            </p>
          </div>
        </section>
      </div>
    </main>
  );
}
