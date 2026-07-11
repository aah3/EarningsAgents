"use client";

import { useEffect, useState, useMemo } from "react";
import { useAuth } from "@clerk/nextjs";
import { api, Prediction as ApiPrediction } from "@/lib/api";
import AnalysisResult from "@/components/AnalysisResult";
import StatCard from "@/components/dashboard/StatCard";
import ConsensusPill from "@/components/dashboard/ConsensusPill";
import {
  Activity,
  Target,
  Ruler,
  TrendingUp,
  Search,
  ChevronUp,
  ChevronDown,
  ArrowUpDown,
  XCircle,
} from "lucide-react";
import {
  HistoryRow,
  Outcome,
  Prediction,
  ReportTiming,
  isScored,
} from "./history.types";

function OutcomeCell({
  row,
  onVerify,
  isVerifying,
}: {
  row: HistoryRow;
  onVerify: (e: React.MouseEvent) => void;
  isVerifying: boolean;
}) {
  if (row.outcome === "UNVERIFIED") {
    return (
      <div className="text-right">
        <button
          onClick={onVerify}
          disabled={isVerifying}
          className={`px-3 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-widest transition-all duration-200 border ${
            isVerifying
              ? "bg-white/5 border-white/10 text-gray-500 cursor-not-allowed"
              : "bg-teal/5 hover:bg-teal hover:text-black border-teal/20 hover:border-teal text-teal shadow-sm shadow-teal/5 hover:shadow-teal/20 cursor-pointer active:scale-95"
          }`}
        >
          {isVerifying ? (
            <div className="flex items-center gap-1.5 justify-end">
              <span className="w-2.5 h-2.5 border-2 border-gray-500 border-t-transparent rounded-full animate-spin" />
              <span>Verifying...</span>
            </div>
          ) : (
            "Verify Outcome"
          )}
        </button>
      </div>
    );
  }

  return (
    <div className="text-right space-y-1">
      <div className="flex items-center justify-end gap-2">
        <span
          className={`text-[10px] font-black uppercase tracking-widest px-3 py-1.5 rounded-lg border ${
            row.outcome === "CORRECT"
              ? "text-bull bg-bull/10 border-bull/20 shadow-[0_0_15px_rgba(52,211,153,0.15)]"
              : "text-bear bg-bear/10 border-bear/20 shadow-[0_0_15px_rgba(248,113,113,0.15)]"
          }`}
        >
          {row.outcome === "CORRECT" ? "✓ Correct" : "✗ Wrong"}
        </span>
        <span className="text-[10px] font-mono text-ink-mute/70">
          (Pred: {row.prediction})
        </span>
      </div>
    </div>
  );
}

const SessionBadge = ({ timing }: { timing: ReportTiming }) => {
  if (timing === "BMO") {
    return (
      <span className="px-1.5 py-0.5 bg-human/10 text-human border border-human/20 rounded text-[9px] font-mono font-bold tracking-wider shadow-[0_0_10px_rgba(251,191,36,0.1)] inline-block ml-2 select-none">
        BMO
      </span>
    );
  }
  if (timing === "AMC") {
    return (
      <span className="px-1.5 py-0.5 bg-quant/10 text-quant border border-quant/20 rounded text-[9px] font-mono font-bold tracking-wider shadow-[0_0_10px_rgba(96,165,250,0.1)] inline-block ml-2 select-none">
        AMC
      </span>
    );
  }
  return <span className="text-ink-dim/40 font-mono text-xs ml-2 select-none">—</span>;
};

export default function HistoryPage() {
  const { getToken } = useAuth();
  const [history, setHistory] = useState<ApiPrediction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedResult, setSelectedResult] = useState<ApiPrediction | null>(null);
  const [verifyingIds, setVerifyingIds] = useState<Record<number, boolean>>({});

  // Filters State
  const [query, setQuery] = useState("");
  const [predictionFilter, setPredictionFilter] = useState<"ALL" | Prediction>("ALL");
  const [outcomeFilter, setOutcomeFilter] = useState<"ALL" | Outcome>("ALL");
  const [statusFilter, setStatusFilter] = useState<"ALL" | "SCORED" | "PENDING">("ALL");

  // Sorting State
  const [sortKey, setSortKey] = useState<keyof HistoryRow>("reportDate");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const handleVerify = async (e: React.MouseEvent, pred: ApiPrediction) => {
    e.stopPropagation();
    if (!pred.id) return;

    setVerifyingIds((prev) => ({ ...prev, [pred.id!]: true }));
    try {
      const token = await getToken();
      const response = await api.verifyPrediction(pred.id, token || undefined);
      if (response.success && response.result) {
        setHistory((prev) =>
          prev.map((p) => (p.id === pred.id ? { ...p, ...response.result } : p))
        );
      }
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : String(err);
      alert(`Verification failed: ${errMsg}`);
    } finally {
      setVerifyingIds((prev) => ({ ...prev, [pred.id!]: false }));
    }
  };

  useEffect(() => {
    async function loadHistory() {
      try {
        const token = await getToken();
        if (!token) throw new Error("Not authenticated");
        const data = await api.getPredictionHistory(token);
        setHistory(data);
      } catch (err: unknown) {
        const errMsg = err instanceof Error ? err.message : String(err);
        setError(errMsg);
      } finally {
        setLoading(false);
      }
    }
    loadHistory();
  }, [getToken]);

  // Map API Predictions to History Rows
  const rows = useMemo(() => {
    return history.map((p): HistoryRow & { rawPrediction: ApiPrediction } => {
      // Direction mapping: BEAT/MISS/INLINE
      let pred: Prediction = "BEAT";
      const dir = (p.direction || "").toUpperCase();
      if (dir === "MISS") {
        pred = "MISS";
      } else if (dir === "INLINE" || dir === "MEET" || dir === "NEUTRAL") {
        pred = "INLINE";
      }

      // Outcome mapping: CORRECT/WRONG/UNVERIFIED
      let outcome: Outcome = "UNVERIFIED";
      if (p.actual_direction) {
        const correct = p.direction.toLowerCase() === p.actual_direction.toLowerCase();
        outcome = correct ? "CORRECT" : "WRONG";
      }

      return {
        id: p.id,
        ticker: p.ticker,
        company: p.company_name,
        sector: p.sector ?? undefined,
        analysisDate: p.prediction_date,
        reportDate: p.report_date,
        reportTiming: (p.report_timing as ReportTiming) || "UNKNOWN",
        prediction: pred,
        confidence: Math.round(p.confidence * 100),
        actualEps:
          p.actual_eps !== undefined && p.actual_eps !== null ? p.actual_eps : null,
        expectedEps:
          p.expected_eps !== undefined && p.expected_eps !== null ? p.expected_eps : null,
        postEarningsMove:
          p.actual_price_move_pct !== undefined && p.actual_price_move_pct !== null
            ? p.actual_price_move_pct * 100
            : null,
        brier:
          p.accuracy_score !== undefined && p.accuracy_score !== null
            ? p.accuracy_score
            : null,
        outcome: outcome,
        rawPrediction: p,
      };
    });
  }, [history]);

  // Handle header click to cycle: asc -> desc -> asc
  const handleSort = (key: keyof HistoryRow) => {
    if (sortKey !== key) {
      setSortKey(key);
      setSortDir("desc");
    } else {
      setSortDir((prev) => (prev === "asc" ? "desc" : "asc"));
    }
  };

  const compareBy = (key: keyof HistoryRow, dir: "asc" | "desc") => {
    return (a: HistoryRow, b: HistoryRow) => {
      const valA = a[key];
      const valB = b[key];

      const isNullA = valA === null || valA === undefined;
      const isNullB = valB === null || valB === undefined;

      if (isNullA && isNullB) return 0;
      if (isNullA) return 1;
      if (isNullB) return -1;

      if (key === "analysisDate" || key === "reportDate") {
        const timeA = new Date(valA as string).getTime();
        const timeB = new Date(valB as string).getTime();
        return dir === "asc" ? timeA - timeB : timeB - timeA;
      }

      if (typeof valA === "string" && typeof valB === "string") {
        return dir === "asc" ? valA.localeCompare(valB) : valB.localeCompare(valA);
      } else {
        const numA = valA as number;
        const numB = valB as number;
        return dir === "asc" ? numA - numB : numB - numA;
      }
    };
  };

  // Filter and Sort Rows
  const visibleRows = useMemo(() => {
    return rows
      .filter((r) =>
        `${r.ticker} ${r.company}`
          .toLowerCase()
          .includes(query.trim().toLowerCase())
      )
      .filter(
        (r) =>
          predictionFilter === "ALL" || r.prediction === predictionFilter
      )
      .filter((r) => outcomeFilter === "ALL" || r.outcome === outcomeFilter)
      .filter(
        (r) =>
          statusFilter === "ALL" ||
          (statusFilter === "SCORED" ? isScored(r) : !isScored(r))
      )
      .slice()
      .sort(compareBy(sortKey, sortDir));
  }, [rows, query, predictionFilter, outcomeFilter, statusFilter, sortKey, sortDir]);

  // Compute Filter-Aware KPIs
  const kpis = useMemo(() => {
    const scoredRows = visibleRows.filter((r) => isScored(r));
    const totalVisible = visibleRows.length;
    const scoredCount = scoredRows.length;
    const correctCount = scoredRows.filter((r) => r.outcome === "CORRECT").length;

    const winRate =
      scoredCount > 0 ? `${((correctCount / scoredCount) * 100).toFixed(0)}%` : "—";
    const brierSum = scoredRows.reduce((acc, r) => acc + (r.brier ?? 0), 0);
    const avgBrier = scoredCount > 0 ? (brierSum / scoredCount).toFixed(4) : "—";

    const confSum = visibleRows.reduce((acc, r) => acc + r.confidence, 0);
    const avgConfidence = totalVisible > 0 ? `${(confSum / totalVisible).toFixed(0)}%` : "—";

    return {
      total: totalVisible,
      winRate,
      scoredCount,
      avgBrier,
      avgConfidence,
    };
  }, [visibleRows]);

  const handleReset = () => {
    setQuery("");
    setPredictionFilter("ALL");
    setOutcomeFilter("ALL");
    setStatusFilter("ALL");
    setSortKey("reportDate");
    setSortDir("desc");
  };

  const exportToCSV = () => {
    const headers = [
      "Ticker",
      "Company",
      "Sector",
      "Analysis Date",
      "Report Date",
      "Report Timing",
      "Prediction",
      "Confidence %",
      "Actual EPS",
      "Post-Earnings Move %",
      "Brier Score",
      "Outcome",
    ];

    const rowsData = visibleRows.map((r) => [
      r.ticker,
      `"${r.company.replace(/"/g, '""')}"`,
      r.sector || "—",
      r.analysisDate ? new Date(r.analysisDate).toISOString().split("T")[0] : "",
      r.reportDate ? new Date(r.reportDate).toISOString().split("T")[0] : "",
      r.reportTiming,
      r.prediction,
      r.confidence,
      r.actualEps !== null ? r.actualEps : "",
      r.postEarningsMove !== null ? r.postEarningsMove.toFixed(2) : "",
      r.brier !== null ? r.brier.toFixed(4) : "",
      r.outcome,
    ]);

    const csvContent = [
      headers.join(","),
      ...rowsData.map((e) => e.join(",")),
    ].join("\n");

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute(
      "download",
      `earnings_analysis_history_${new Date().toISOString().split("T")[0]}.csv`
    );
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const renderSortIndicator = (key: keyof HistoryRow) => {
    if (sortKey !== key) {
      return (
        <ArrowUpDown className="w-3.5 h-3.5 opacity-30 group-hover:opacity-75 transition-opacity" />
      );
    }
    return sortDir === "asc" ? (
      <ChevronUp className="w-3.5 h-3.5 text-teal" />
    ) : (
      <ChevronDown className="w-3.5 h-3.5 text-teal" />
    );
  };

  const getAriaSort = (key: keyof HistoryRow) => {
    if (sortKey !== key) return "none";
    return sortDir === "asc" ? "ascending" : "descending";
  };

  const getConfidenceBarColor = (score: number) => {
    if (score >= 80) return "bg-bull";
    if (score >= 60) return "bg-teal";
    return "bg-bear";
  };

  return (
    <div className="space-y-6 pb-20">
      <header className="flex justify-between items-end mb-[20px]">
        <div>
          <h1 className="text-[clamp(1.9rem,3vw,2.3rem)] font-display font-semibold tracking-tight text-white mb-2 leading-none">
            Analysis History
          </h1>
        </div>
        {selectedResult && (
          <button
            onClick={() => setSelectedResult(null)}
            className="text-xs font-bold text-teal hover:text-[#7DE8DA] uppercase tracking-widest transition-colors flex items-center gap-2 mb-2 cursor-pointer outline-none"
          >
            ← Back to History
          </button>
        )}
      </header>

      {/* KPI Cards Row */}
      {!selectedResult && !loading && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 select-none animate-in fade-in duration-300">
          <StatCard
            icon={<Activity className="w-6 h-6" />}
            label="Predictions Shown"
            value={String(kpis.total)}
            context={`of ${rows.length} total`}
            tone="teal"
          />
          <StatCard
            icon={<Target className="w-6 h-6" />}
            label="Win Rate"
            value={kpis.winRate}
            context={
              kpis.scoredCount > 0
                ? `${kpis.scoredCount} scored`
                : "no scored predictions"
            }
            tone="bull"
          />
          <StatCard
            icon={<Ruler className="w-6 h-6" />}
            label="Avg Brier Score"
            value={kpis.avgBrier}
            context="lower is better"
            tone="quant"
          />
          <StatCard
            icon={<TrendingUp className="w-6 h-6" />}
            label="Avg Confidence"
            value={kpis.avgConfidence}
            context="across shown"
            tone="teal"
          />
        </div>
      )}

      {loading ? (
        <div className="glass p-20 rounded-3xl border border-white/5 flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-teal border-t-transparent rounded-full animate-spin" />
          <p className="text-gray-500 font-bold uppercase tracking-widest text-xs">
            Fetching your history...
          </p>
        </div>
      ) : error ? (
        <div className="glass p-20 rounded-3xl border border-red-500/20 bg-red-500/5 text-center">
          <p className="text-red-500 font-black mb-2">Error loading history</p>
          <p className="text-gray-400 text-sm">{error}</p>
        </div>
      ) : rows.length === 0 ? (
        <div className="glass p-20 rounded-3xl border border-white/5 text-center">
          <p className="text-gray-500 font-black mb-2">No analyses yet</p>
          <p className="text-gray-400 text-sm mb-8">
            Run your first analysis from the dashboard to see it here.
          </p>
        </div>
      ) : selectedResult ? (
        <AnalysisResult result={selectedResult} />
      ) : (
        <div className="rounded-[16px] border border-[#26334A] bg-panel overflow-hidden flex flex-col shadow-[0_20px_60px_rgba(0,0,0,0.35)] animate-in fade-in duration-300">
          {/* Table Header and Actions */}
          <div className="px-6 py-[22px] border-b border-panel-line flex items-center justify-between flex-wrap gap-4 select-none">
            <div className="flex items-center gap-3">
              <h2 className="text-lg font-display font-semibold text-white uppercase tracking-wider">
                Historical Ledger
              </h2>
              <span className="text-[11px] font-mono font-bold text-ink-mute bg-[var(--color-panel-sunk)] border border-panel-line px-2.5 py-1 rounded-[8px] select-none">
                Showing {visibleRows.length} of {rows.length}
              </span>
            </div>
            <div className="flex items-center gap-4">
              <button
                onClick={exportToCSV}
                className="text-xs font-mono font-bold text-teal hover:text-[#7DE8DA] transition-colors uppercase tracking-widest flex items-center gap-1.5 outline-none rounded bg-transparent border-0 cursor-pointer"
              >
                Export CSV
              </button>
              <span className="border-l border-panel-line h-4" />
              <a
                href="/dashboard/performance"
                className="text-xs font-mono font-bold text-teal hover:text-[#7DE8DA] transition-colors uppercase tracking-widest flex items-center gap-1.5 outline-none rounded"
              >
                View performance dashboard &rarr;
              </a>
            </div>
          </div>

          {/* Controls Row */}
          <div className="p-6 border-b border-panel-line bg-white/[0.01] flex flex-wrap gap-6 items-center justify-between">
            {/* Search Input */}
            <div className="relative w-full sm:w-72">
              <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-ink-dim select-none">
                <Search className="w-4 h-4" />
              </span>
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search ticker or company..."
                aria-label="Search predictions by stock ticker or company name"
                className="w-full bg-[#05070a] border border-panel-line rounded-xl pl-10 pr-4 py-2.5 focus:border-teal focus:ring-2 focus:ring-teal/20 outline-none text-sm text-white placeholder-white/20 transition-all font-body"
              />
            </div>

            {/* Segment Filters Group */}
            <div className="flex flex-wrap items-center gap-6">
              {/* Prediction Filter */}
              <div className="flex items-center gap-2.5">
                <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-ink-dim select-none">
                  Prediction:
                </span>
                <div className="flex gap-0.5 p-1 bg-[var(--color-panel-sunk)] border border-panel-line rounded-[10px] select-none">
                  {(["ALL", "BEAT", "MISS", "INLINE"] as const).map((p) => (
                    <button
                      key={p}
                      onClick={() => setPredictionFilter(p)}
                      className={`px-3 py-1.5 rounded-md font-mono text-[11px] uppercase transition-all select-none cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-teal
                        ${
                          predictionFilter === p
                            ? "bg-teal/14 text-teal"
                            : "text-ink-mute hover:text-white"
                        }`}
                    >
                      {p === "ALL" ? "All" : p.toLowerCase()}
                    </button>
                  ))}
                </div>
              </div>

              {/* Outcome Filter */}
              <div className="flex items-center gap-2.5">
                <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-ink-dim select-none">
                  Outcome:
                </span>
                <div className="flex gap-0.5 p-1 bg-[var(--color-panel-sunk)] border border-panel-line rounded-[10px] select-none">
                  {(["ALL", "CORRECT", "WRONG", "UNVERIFIED"] as const).map((o) => (
                    <button
                      key={o}
                      onClick={() => setOutcomeFilter(o)}
                      className={`px-3 py-1.5 rounded-md font-mono text-[11px] uppercase transition-all select-none cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-teal
                        ${
                          outcomeFilter === o
                            ? "bg-teal/14 text-teal"
                            : "text-ink-mute hover:text-white"
                        }`}
                    >
                      {o === "ALL" ? "All" : o.toLowerCase()}
                    </button>
                  ))}
                </div>
              </div>

              {/* Status Filter */}
              <div className="flex items-center gap-2.5">
                <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-ink-dim select-none">
                  Status:
                </span>
                <div className="flex gap-0.5 p-1 bg-[#0e1524] border border-panel-line rounded-[10px] select-none">
                  {(["ALL", "SCORED", "PENDING"] as const).map((s) => (
                    <button
                      key={s}
                      onClick={() => setStatusFilter(s)}
                      className={`px-3 py-1.5 rounded-md font-mono text-[11px] uppercase transition-all select-none cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-teal
                        ${
                          statusFilter === s
                            ? "bg-teal/14 text-teal"
                            : "text-ink-mute hover:text-white"
                        }`}
                    >
                      {s === "ALL" ? "All" : s.toLowerCase()}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Table Container */}
          <div className="overflow-x-auto max-h-[600px] custom-scrollbar">
            <table className="w-full text-left whitespace-nowrap border-collapse">
              <thead className="sticky top-0 bg-[#05070a] border-b border-panel-line text-ink-dim select-none z-10">
                <tr>
                  <th className="pl-8 pr-4 py-5 label-caps" aria-sort={getAriaSort("ticker")}>
                    <button
                      onClick={() => handleSort("ticker")}
                      className="flex items-center gap-2 group text-left label-caps hover:text-white transition-colors cursor-pointer outline-none focus-visible:text-teal"
                    >
                      Ticker
                      {renderSortIndicator("ticker")}
                    </button>
                  </th>
                  <th className="px-6 py-5 label-caps" aria-sort={getAriaSort("sector")}>
                    <button
                      onClick={() => handleSort("sector")}
                      className="flex items-center gap-2 group text-left label-caps hover:text-white transition-colors cursor-pointer outline-none focus-visible:text-teal"
                    >
                      Sector
                      {renderSortIndicator("sector")}
                    </button>
                  </th>
                  <th className="px-6 py-5 label-caps" aria-sort={getAriaSort("analysisDate")}>
                    <button
                      onClick={() => handleSort("analysisDate")}
                      className="flex items-center gap-2 group text-left label-caps hover:text-white transition-colors cursor-pointer outline-none focus-visible:text-teal"
                    >
                      Analysis Date
                      {renderSortIndicator("analysisDate")}
                    </button>
                  </th>
                  <th className="px-6 py-5 label-caps" aria-sort={getAriaSort("reportDate")}>
                    <button
                      onClick={() => handleSort("reportDate")}
                      className="flex items-center gap-2 group text-left label-caps hover:text-white transition-colors cursor-pointer outline-none focus-visible:text-teal"
                    >
                      Report Date
                      {renderSortIndicator("reportDate")}
                    </button>
                  </th>
                  <th className="px-6 py-5 label-caps" aria-sort={getAriaSort("prediction")}>
                    <button
                      onClick={() => handleSort("prediction")}
                      className="flex items-center gap-2 group text-left label-caps hover:text-white transition-colors cursor-pointer outline-none focus-visible:text-teal"
                    >
                      Prediction
                      {renderSortIndicator("prediction")}
                    </button>
                  </th>
                  <th className="px-6 py-5 label-caps" aria-sort={getAriaSort("confidence")}>
                    <button
                      onClick={() => handleSort("confidence")}
                      className="flex items-center gap-2 group text-left label-caps hover:text-white transition-colors cursor-pointer outline-none focus-visible:text-teal"
                    >
                      Confidence
                      {renderSortIndicator("confidence")}
                    </button>
                  </th>
                  <th className="px-6 py-5 label-caps" aria-sort={getAriaSort("expectedEps")}>
                    <button
                      onClick={() => handleSort("expectedEps")}
                      className="flex items-center gap-2 group text-left label-caps hover:text-white transition-colors cursor-pointer outline-none focus-visible:text-teal"
                    >
                      Expected EPS
                      {renderSortIndicator("expectedEps")}
                    </button>
                  </th>
                  <th className="px-6 py-5 label-caps" aria-sort={getAriaSort("actualEps")}>
                    <button
                      onClick={() => handleSort("actualEps")}
                      className="flex items-center gap-2 group text-left label-caps hover:text-white transition-colors cursor-pointer outline-none focus-visible:text-teal"
                    >
                      Actual EPS
                      {renderSortIndicator("actualEps")}
                    </button>
                  </th>
                  <th className="px-6 py-5 label-caps" aria-sort={getAriaSort("postEarningsMove")}>
                    <button
                      onClick={() => handleSort("postEarningsMove")}
                      className="flex items-center gap-2 group text-left label-caps hover:text-white transition-colors cursor-pointer outline-none focus-visible:text-teal"
                    >
                      Post-Earnings Move
                      {renderSortIndicator("postEarningsMove")}
                    </button>
                  </th>
                  <th className="px-6 py-5 label-caps" aria-sort={getAriaSort("brier")}>
                    <button
                      onClick={() => handleSort("brier")}
                      className="flex items-center gap-2 group text-left label-caps hover:text-white transition-colors cursor-pointer outline-none focus-visible:text-teal"
                    >
                      Brier
                      {renderSortIndicator("brier")}
                    </button>
                  </th>
                  <th className="pl-4 pr-8 py-5 text-right label-caps" aria-sort={getAriaSort("outcome")}>
                    <button
                      onClick={() => handleSort("outcome")}
                      className="flex items-center gap-2 ml-auto group text-right label-caps hover:text-white transition-colors cursor-pointer outline-none focus-visible:text-teal"
                    >
                      Outcome
                      {renderSortIndicator("outcome")}
                    </button>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 font-body">
                {visibleRows.map((row) => (
                  <tr
                    key={(row.id ?? row.ticker) + row.analysisDate}
                    tabIndex={0}
                    onClick={() => setSelectedResult(row.rawPrediction)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        setSelectedResult(row.rawPrediction);
                      }
                    }}
                    className={`hover:bg-white/[0.02] transition-colors group cursor-pointer relative focus:outline-none focus:bg-white/[0.04] ${
                      row.outcome === "WRONG"
                        ? "border-l-2 border-bear/60"
                        : "border-l-2 border-transparent"
                    }`}
                  >
                    {/* Ticker & Company Name */}
                    <td className="pl-8 pr-4 py-4 min-w-[160px]">
                      <div className="font-display font-bold text-accent text-lg leading-tight truncate">
                        {row.ticker}
                      </div>
                      <div
                        title={row.company}
                        className="text-[10px] text-ink-mute font-bold uppercase tracking-tighter truncate max-w-[150px]"
                      >
                        {row.company}
                      </div>
                    </td>

                    {/* Sector */}
                    <td className="px-6 py-4 text-sm text-ink-mute font-medium">
                      {(!row.sector || row.sector === "Unknown") ? "—" : row.sector}
                    </td>

                    {/* Analysis Date */}
                    <td className="px-6 py-4 text-sm text-ink-mute font-mono">
                      {new Date(row.analysisDate).toLocaleDateString(undefined, {
                        year: "numeric",
                        month: "2-digit",
                        day: "2-digit",
                      })}
                    </td>

                    {/* Report Date + Session Badge */}
                    <td className="px-6 py-4 text-sm text-white font-mono flex items-center h-full">
                      <span className="align-middle">
                        {new Date(row.reportDate).toLocaleDateString(undefined, {
                          year: "numeric",
                          month: "2-digit",
                          day: "2-digit",
                        })}
                      </span>
                      <SessionBadge timing={row.reportTiming} />
                    </td>

                    {/* Prediction Pill */}
                    <td className="px-6 py-4">
                      <ConsensusPill consensus={row.prediction} />
                    </td>

                    {/* Confidence Score Bar */}
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-16 h-1.5 bg-white/10 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${getConfidenceBarColor(
                              row.confidence
                            )}`}
                            style={{ width: `${row.confidence}%` }}
                          />
                        </div>
                        <span className="font-data text-white text-sm">
                          {row.confidence}%
                        </span>
                      </div>
                    </td>

                    {/* Expected EPS */}
                    <td className="px-6 py-4 font-mono text-sm text-white/70">
                      {row.expectedEps !== null ? (
                        `$${row.expectedEps.toFixed(2)}`
                      ) : (
                        <span className="text-ink-dim/40">—</span>
                      )}
                    </td>

                    {/* Actual EPS */}
                    <td className="px-6 py-4 font-mono text-sm text-white">
                      {row.actualEps !== null ? (
                        `$${row.actualEps.toFixed(2)}`
                      ) : (
                        <span className="text-ink-dim/40">—</span>
                      )}
                    </td>

                    {/* Post-Earnings Move */}
                    <td className="px-6 py-4 font-mono text-sm">
                      {row.postEarningsMove !== null ? (
                        <span
                          className={
                            row.postEarningsMove >= 0 ? "text-bull" : "text-bear"
                          }
                        >
                          {row.postEarningsMove >= 0 ? "+" : ""}
                          {row.postEarningsMove.toFixed(2)}%
                        </span>
                      ) : (
                        <span className="text-ink-dim/40">—</span>
                      )}
                    </td>

                    {/* Brier Score */}
                    <td className="px-6 py-4 font-mono text-sm">
                      {row.brier !== null ? (
                        <span
                          className={
                            row.brier <= 0.1
                              ? "text-bull-deep font-semibold"
                              : "text-ink-mute"
                          }
                        >
                          {row.brier.toFixed(4)}
                        </span>
                      ) : (
                        <span className="text-ink-dim/40">—</span>
                      )}
                    </td>

                    {/* Outcome Badge / Verify Action */}
                    <td className="pl-4 pr-8 py-4">
                      <OutcomeCell
                        row={row}
                        onVerify={(e) => handleVerify(e, row.rawPrediction)}
                        isVerifying={row.id ? !!verifyingIds[row.id] : false}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Empty State */}
          {visibleRows.length === 0 && (
            <div className="flex flex-col items-center justify-center py-16 text-center select-none">
              <XCircle className="w-12 h-12 text-ink-dim mb-3" />
              <p className="text-gray-500 font-bold uppercase tracking-widest text-xs mb-4">
                No predictions match this filter
              </p>
              <button
                onClick={handleReset}
                className="px-4 py-2 bg-teal text-black rounded-lg text-xs font-black uppercase tracking-widest hover:bg-teal/80 transition-colors"
              >
                Reset Filters
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
