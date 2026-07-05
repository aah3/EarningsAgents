import React from "react";
import { Sparkles, Rocket } from "lucide-react";

interface AnalysisHubProps {
  ticker: string;
  setTicker: (val: string) => void;
  reportDate: string;
  setReportDate: (val: string) => void;
  userAnalysis: string;
  setUserAnalysis: (val: string) => void;
  onRunAnalysis: () => void;
  loading: boolean;
}

export default function AnalysisHub({
  ticker,
  setTicker,
  reportDate,
  setReportDate,
  userAnalysis,
  setUserAnalysis,
  onRunAnalysis,
  loading,
}: AnalysisHubProps) {
  // Derive if debate launch is disabled
  const isLaunchDisabled = loading || !ticker.trim() || !reportDate;

  return (
    <div className="relative p-[22px_24px] rounded-[16px] border border-[#26334A] bg-panel shadow-[0_20px_60px_rgba(0,0,0,0.35)] overflow-hidden group">
      {/* Top highlight bar */}
      <div className="absolute top-0 inset-x-0 h-1.5 bg-gradient-to-r from-transparent via-teal to-transparent opacity-50 group-hover:opacity-100 transition-opacity duration-300"></div>

      {/* Header Row */}
      <div className="flex justify-between items-center mb-8 flex-wrap gap-4 select-none">
        <h2 className="text-xl font-display font-semibold text-white uppercase tracking-wider flex items-center gap-3">
          <Sparkles className="w-6 h-6 text-teal" />
          AI Analysis Hub
        </h2>
        <div className="text-[11px] font-mono font-bold text-ink-mute uppercase tracking-widest bg-white/[0.03] border border-panel-line px-4 py-2 rounded-lg">
          SEC EDGAR · Alpha Vantage · Yahoo Finance · FinViz
        </div>
      </div>

      {/* Inputs Row */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 w-full items-end">
        {/* Ticker Input */}
        <div className="lg:col-span-4 space-y-3">
          <label className="block text-[11px] font-mono font-bold uppercase tracking-widest text-teal">
            Target Stock Ticker
          </label>
          <input
            type="text"
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
            placeholder="E.G. NVDA"
            className="w-full bg-[#05070a] border-2 border-panel-line rounded-2xl px-6 py-5 focus:border-teal focus:ring-4 focus:ring-teal/20 outline-none transition-all uppercase font-display font-bold text-4xl lg:text-5xl tracking-widest text-white placeholder-white/10 h-[90px] shadow-inner"
            disabled={loading}
          />
        </div>

        {/* Date Input */}
        <div className="lg:col-span-3 space-y-3">
          <label className="block text-[11px] font-mono font-bold uppercase tracking-widest text-ink-mute">
            Report Date
          </label>
          <input
            type="date"
            value={reportDate}
            onChange={(e) => setReportDate(e.target.value)}
            className="w-full bg-[#05070a] border border-panel-line rounded-2xl px-6 py-5 focus:border-teal focus:ring-2 focus:ring-teal/20 outline-none transition-all text-xl font-body font-bold text-white relative [color-scheme:dark] h-[90px]"
            disabled={loading}
          />
        </div>

        {/* Submit Launch button */}
        <div className="lg:col-span-5 flex flex-col justify-end">
          <button
            onClick={onRunAnalysis}
            disabled={isLaunchDisabled}
            className={`w-full h-[90px] rounded-2xl font-display font-semibold uppercase tracking-widest text-lg lg:text-xl transition-all duration-150 flex items-center justify-center gap-4 outline-none focus-visible:ring-2 focus-visible:ring-teal focus-visible:ring-offset-2 focus-visible:ring-offset-panel select-none
              ${
                isLaunchDisabled
                  ? "bg-panel-line text-ink-dim cursor-not-allowed border-2 border-panel-line shadow-none"
                  : "bg-gradient-to-br from-bull to-bull-deep text-[#04231F] border-2 border-bull shadow-[0_8px_26px_rgba(52,211,153,0.25)] hover:shadow-[0_12px_34px_rgba(52,211,153,0.4)] hover:-translate-y-0.5 cursor-pointer"
              }`}
          >
            {loading ? "Analyzing..." : "Launch Agent Debate"}
            {!loading && <Rocket className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Analyst Context Row */}
      <div className="mt-6 space-y-3">
        <div className="flex justify-between items-center pr-2 select-none">
          <label className="text-[11px] font-mono font-bold uppercase tracking-wider text-ink-mute">
            Your Custom Analysis Context (Optional)
          </label>
          <span className="text-[9px] font-mono text-human font-bold uppercase tracking-widest bg-human/10 px-3 py-1.5 rounded-md border border-human/20">
            ANALYST AGENT INPUT
          </span>
        </div>
        <textarea
          value={userAnalysis}
          onChange={(e) => setUserAnalysis(e.target.value)}
          placeholder="Include your prompt/analysis to be incorporated into the consensus."
          className="w-full bg-[#05070a] border border-panel-line border-l-2 border-l-human rounded-xl px-5 py-4 focus:border-teal focus:ring-1 focus:ring-teal/50 outline-none transition-all text-sm font-body font-medium text-white relative placeholder-white/20 min-h-[80px] resize-y custom-scrollbar"
          disabled={loading}
        />
      </div>
    </div>
  );
}
