"use client";

import { useEffect, useState, useMemo, useCallback, useRef } from "react";
import { useAuth } from "@clerk/nextjs";
import {
  api,
  Prediction as ApiPrediction,
  HistoryQuery,
  HistoryStats,
  HistoryFilterOptions,
} from "@/lib/api";
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
  ChevronLeft,
  ChevronRight,
  ArrowUpDown,
  XCircle,
  RefreshCw,
} from "lucide-react";
import {
  HistoryRow,
  Outcome,
  Prediction,
  ReportTiming,
  SortKey,
  PAGE_SIZE_OPTIONS,
  DEFAULT_PAGE_SIZE,
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
    <div className="text-right space-y-1 select-none">
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
        <button
          onClick={onVerify}
          disabled={isVerifying}
          title="Re-verify outcome data"
          className="p-1.5 rounded-lg text-[10px] text-ink-mute hover:text-teal hover:bg-teal/10 border border-panel-line transition-all cursor-pointer disabled:opacity-50"
        >
          {isVerifying ? (
            <span className="w-3 h-3 border-2 border-teal border-t-transparent rounded-full animate-spin inline-block" />
          ) : (
            <RefreshCw className="w-3 h-3" />
          )}
        </button>
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

/** Map an API prediction record onto the flat shape the table renders. */
function toRow(p: ApiPrediction): HistoryRow & { rawPrediction: ApiPrediction } {
  let pred: Prediction = "BEAT";
  const dir = (p.direction || "").toUpperCase();
  if (dir === "MISS") {
    pred = "MISS";
  } else if (dir === "INLINE" || dir === "MEET" || dir === "NEUTRAL") {
    pred = "INLINE";
  }

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
    fiscalPeriod: p.fiscal_period ?? null,
    prediction: pred,
    confidence: Math.round(p.confidence * 100),
    actualEps: p.actual_eps !== undefined && p.actual_eps !== null ? p.actual_eps : null,
    expectedEps:
      p.expected_eps !== undefined && p.expected_eps !== null ? p.expected_eps : null,
    postEarningsMove:
      p.actual_price_move_pct !== undefined && p.actual_price_move_pct !== null
        ? p.actual_price_move_pct * 100
        : null,
    brier:
      p.accuracy_score !== undefined && p.accuracy_score !== null ? p.accuracy_score : null,
    outcome: outcome,
    rawPrediction: p,
  };
}

export default function HistoryPage() {
  const { getToken } = useAuth();
  const [items, setItems] = useState<ApiPrediction[]>([]);
  const [total, setTotal] = useState(0);
  const [stats, setStats] = useState<HistoryStats | null>(null);
  const [filterOptions, setFilterOptions] = useState<HistoryFilterOptions>({
    sectors: [],
    fiscal_periods: [],
    report_dates: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedResult, setSelectedResult] = useState<ApiPrediction | null>(null);
  const [verifyingIds, setVerifyingIds] = useState<Record<number, boolean>>({});
  const [exporting, setExporting] = useState(false);

  // Filters State
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [predictionFilter, setPredictionFilter] = useState<"ALL" | Prediction>("ALL");
  const [outcomeFilter, setOutcomeFilter] = useState<"ALL" | Outcome>("ALL");
  const [statusFilter, setStatusFilter] = useState<"ALL" | "SCORED" | "PENDING">("ALL");
  const [sectorFilter, setSectorFilter] = useState<string>("ALL");
  const [dateFilter, setDateFilter] = useState<string>("ALL");
  const [periodFilter, setPeriodFilter] = useState<string>("ALL");

  // Sorting + paging State
  const [sortKey, setSortKey] = useState<SortKey>("report_date");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [pageSize, setPageSize] = useState<number>(DEFAULT_PAGE_SIZE);
  const [offset, setOffset] = useState(0);

  // Debounce the search box so typing doesn't fire a request per keystroke.
  // Resetting the offset here (rather than in a follow-up effect) keeps the
  // query change and the page reset in the same render, so the fetch effect
  // fires once instead of twice.
  useEffect(() => {
    const handle = setTimeout(() => {
      setDebouncedQuery(query);
      setOffset(0);
    }, 300);
    return () => clearTimeout(handle);
  }, [query]);

  /** Wrap a filter setter so changing it also returns to the first page. */
  function withPageReset<T>(setter: (value: T) => void) {
    return (value: T) => {
      setter(value);
      setOffset(0);
    };
  }

  const changePrediction = withPageReset(setPredictionFilter);
  const changeOutcome = withPageReset(setOutcomeFilter);
  const changeStatus = withPageReset(setStatusFilter);
  const changeSector = withPageReset(setSectorFilter);
  const changeDate = withPageReset(setDateFilter);
  const changePeriod = withPageReset(setPeriodFilter);
  const changePageSize = withPageReset(setPageSize);

  const buildQuery = useCallback(
    (overrides: Partial<HistoryQuery> = {}): HistoryQuery => ({
      limit: pageSize,
      offset,
      sort_by: sortKey,
      sort_dir: sortDir,
      q: debouncedQuery.trim() || undefined,
      prediction: predictionFilter === "ALL" ? undefined : predictionFilter,
      outcome: outcomeFilter === "ALL" ? undefined : outcomeFilter,
      status: statusFilter === "ALL" ? undefined : statusFilter,
      sector: sectorFilter === "ALL" ? undefined : sectorFilter,
      report_date: dateFilter === "ALL" ? undefined : dateFilter,
      fiscal_period: periodFilter === "ALL" ? undefined : periodFilter,
      ...overrides,
    }),
    [
      pageSize,
      offset,
      sortKey,
      sortDir,
      debouncedQuery,
      predictionFilter,
      outcomeFilter,
      statusFilter,
      sectorFilter,
      dateFilter,
      periodFilter,
    ]
  );

  // Guards against an earlier in-flight request resolving after a later one
  const requestSeq = useRef(0);

  useEffect(() => {
    let cancelled = false;
    const seq = ++requestSeq.current;

    async function loadHistory() {
      try {
        setLoading(true);
        const token = await getToken();
        if (!token) throw new Error("Not authenticated");
        const page = await api.getPredictionHistory(token, buildQuery());
        if (cancelled || seq !== requestSeq.current) return;
        setItems(page.items || []);
        setTotal(page.total || 0);
        setStats(page.stats);
        setError(null);
      } catch (err: unknown) {
        if (cancelled || seq !== requestSeq.current) return;
        const errMsg = err instanceof Error ? err.message : String(err);
        setError(errMsg);
      } finally {
        if (!cancelled && seq === requestSeq.current) setLoading(false);
      }
    }
    loadHistory();
    return () => {
      cancelled = true;
    };
  }, [getToken, buildQuery]);

  // Filter dropdown options come from the whole table, not the current page
  useEffect(() => {
    async function loadFilters() {
      try {
        const token = await getToken();
        if (!token) return;
        const opts = await api.getHistoryFilterOptions(token);
        setFilterOptions(opts);
      } catch {
        // Non-fatal: the table still works, the dropdowns just stay empty
      }
    }
    loadFilters();
  }, [getToken]);

  const handleVerify = async (e: React.MouseEvent, pred: ApiPrediction) => {
    e.stopPropagation();
    if (!pred.id) return;

    setVerifyingIds((prev) => ({ ...prev, [pred.id!]: true }));
    try {
      const token = await getToken();
      const response = await api.verifyPrediction(pred.id, token || undefined);
      if (response.success && response.result) {
        setItems((prev) =>
          prev.map((p) => (p.id === pred.id ? { ...p, ...response.result } : p))
        );
        // Scoring changed — cached pages and aggregates are now stale
        api.invalidateHistoryCache();
      }
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : String(err);
      alert(`Verification failed: ${errMsg}`);
    } finally {
      setVerifyingIds((prev) => ({ ...prev, [pred.id!]: false }));
    }
  };

  const rows = useMemo(() => items.map(toRow), [items]);

  // Handle header click to cycle: asc -> desc
  const handleSort = (key: SortKey) => {
    if (sortKey !== key) {
      setSortKey(key);
      setSortDir("desc");
    } else {
      setSortDir((prev) => (prev === "asc" ? "desc" : "asc"));
    }
    setOffset(0);
  };

  const handleReset = () => {
    setQuery("");
    setPredictionFilter("ALL");
    setOutcomeFilter("ALL");
    setStatusFilter("ALL");
    setSectorFilter("ALL");
    setDateFilter("ALL");
    setPeriodFilter("ALL");
    setSortKey("report_date");
    setSortDir("desc");
    setOffset(0);
  };

  // Export every row matching the current filters, not just the visible page.
  const exportToCSV = async () => {
    setExporting(true);
    try {
      const token = await getToken();
      if (!token) throw new Error("Not authenticated");

      // Pull every row matching the current filters, in server-max chunks —
      // the API caps a single page at MAX_HISTORY_PAGE_SIZE.
      const CHUNK = 1000;
      const collected: ApiPrediction[] = [];
      for (let at = 0; at < total; at += CHUNK) {
        const chunk = await api.getPredictionHistory(
          token,
          buildQuery({ limit: CHUNK, offset: at })
        );
        if (!chunk.items?.length) break;
        collected.push(...chunk.items);
      }
      const exportRows = collected.map(toRow);

      const headers = [
        "Ticker",
        "Company",
        "Sector",
        "Analysis Date",
        "Report Date",
        "Report Timing",
        "Reporting Period",
        "Prediction",
        "Confidence %",
        "Expected EPS",
        "Actual EPS",
        "Post-Earnings Move %",
        "Brier Score",
        "Outcome",
      ];

      const rowsData = exportRows.map((r) => [
        r.ticker,
        `"${r.company.replace(/"/g, '""')}"`,
        r.sector || "—",
        r.analysisDate ? new Date(r.analysisDate).toISOString().split("T")[0] : "",
        r.reportDate ? new Date(r.reportDate).toISOString().split("T")[0] : "",
        r.reportTiming,
        r.fiscalPeriod || "",
        r.prediction,
        r.confidence,
        r.expectedEps !== null ? r.expectedEps : "",
        r.actualEps !== null ? r.actualEps : "",
        r.postEarningsMove !== null ? r.postEarningsMove.toFixed(2) : "",
        r.brier !== null ? r.brier.toFixed(4) : "",
        r.outcome,
      ]);

      const csvContent = [headers.join(","), ...rowsData.map((e) => e.join(","))].join("\n");

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
      URL.revokeObjectURL(url);
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : String(err);
      alert(`Export failed: ${errMsg}`);
    } finally {
      setExporting(false);
    }
  };

  const renderSortIndicator = (key: SortKey) => {
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

  const getAriaSort = (key: SortKey) => {
    if (sortKey !== key) return "none";
    return sortDir === "asc" ? "ascending" : "descending";
  };

  const getConfidenceBarColor = (score: number) => {
    if (score >= 80) return "bg-bull";
    if (score >= 60) return "bg-teal";
    return "bg-bear";
  };

  // KPI values come from server-computed aggregates over the full filtered set
  const kpis = useMemo(() => {
    const winRate =
      stats?.win_rate !== null && stats?.win_rate !== undefined
        ? `${(stats.win_rate * 100).toFixed(0)}%`
        : "—";
    const avgBrier =
      stats?.avg_brier !== null && stats?.avg_brier !== undefined
        ? stats.avg_brier.toFixed(4)
        : "—";
    const avgConfidence =
      stats?.avg_confidence !== null && stats?.avg_confidence !== undefined
        ? `${(stats.avg_confidence * 100).toFixed(0)}%`
        : "—";
    return {
      total: stats?.total ?? 0,
      scoredCount: stats?.scored_count ?? 0,
      winRate,
      avgBrier,
      avgConfidence,
    };
  }, [stats]);

  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  const currentPage = Math.floor(offset / pageSize) + 1;
  const rangeStart = total === 0 ? 0 : offset + 1;
  const rangeEnd = Math.min(offset + pageSize, total);
  const hasFilters =
    !!query ||
    predictionFilter !== "ALL" ||
    outcomeFilter !== "ALL" ||
    statusFilter !== "ALL" ||
    sectorFilter !== "ALL" ||
    dateFilter !== "ALL" ||
    periodFilter !== "ALL";

  // Compact page-number window around the current page
  const pageNumbers = useMemo(() => {
    const windowSize = 5;
    let start = Math.max(1, currentPage - Math.floor(windowSize / 2));
    const end = Math.min(pageCount, start + windowSize - 1);
    start = Math.max(1, end - windowSize + 1);
    return Array.from({ length: end - start + 1 }, (_, i) => start + i);
  }, [currentPage, pageCount]);

  const goToPage = (page: number) => {
    const clamped = Math.min(Math.max(1, page), pageCount);
    setOffset((clamped - 1) * pageSize);
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
      {!selectedResult && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 select-none animate-in fade-in duration-300">
          <StatCard
            icon={<Activity className="w-6 h-6" />}
            label="Predictions Matched"
            value={String(kpis.total)}
            context={hasFilters ? "matching filters" : "all time"}
            tone="teal"
          />
          <StatCard
            icon={<Target className="w-6 h-6" />}
            label="Win Rate"
            value={kpis.winRate}
            context={
              kpis.scoredCount > 0 ? `${kpis.scoredCount} scored` : "no scored predictions"
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
            context="across matched"
            tone="teal"
          />
        </div>
      )}

      {error ? (
        <div className="glass p-20 rounded-3xl border border-red-500/20 bg-red-500/5 text-center">
          <p className="text-red-500 font-black mb-2">Error loading history</p>
          <p className="text-gray-400 text-sm">{error}</p>
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
                {total === 0 ? "No results" : `Showing ${rangeStart}–${rangeEnd} of ${total}`}
              </span>
              {loading && (
                <span className="w-3.5 h-3.5 border-2 border-teal border-t-transparent rounded-full animate-spin inline-block" />
              )}
            </div>
            <div className="flex items-center gap-4">
              <button
                onClick={exportToCSV}
                disabled={exporting || total === 0}
                title="Export every row matching the current filters"
                className="text-xs font-mono font-bold text-teal hover:text-[#7DE8DA] transition-colors uppercase tracking-widest flex items-center gap-1.5 outline-none rounded bg-transparent border-0 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {exporting ? "Exporting..." : "Export CSV"}
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
                      onClick={() => changePrediction(p)}
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
                      onClick={() => changeOutcome(o)}
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
                      onClick={() => changeStatus(s)}
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

              {/* Reporting Period Filter Dropdown */}
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-ink-dim select-none">
                  Period:
                </span>
                <select
                  value={periodFilter}
                  onChange={(e) => changePeriod(e.target.value)}
                  aria-label="Filter by Reporting Period"
                  className="bg-[#05070a] border border-panel-line rounded-[10px] px-3 py-1.5 font-mono text-[11px] text-white focus:border-teal outline-none cursor-pointer transition-colors"
                >
                  <option value="ALL">
                    All Periods ({filterOptions.fiscal_periods.length})
                  </option>
                  {filterOptions.fiscal_periods.map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
                </select>
              </div>

              {/* Sector Filter Dropdown */}
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-ink-dim select-none">
                  Sector:
                </span>
                <select
                  value={sectorFilter}
                  onChange={(e) => changeSector(e.target.value)}
                  aria-label="Filter by Sector"
                  className="bg-[#05070a] border border-panel-line rounded-[10px] px-3 py-1.5 font-mono text-[11px] text-white focus:border-teal outline-none cursor-pointer transition-colors"
                >
                  <option value="ALL">All Sectors ({filterOptions.sectors.length})</option>
                  {filterOptions.sectors.map((sec) => (
                    <option key={sec} value={sec}>
                      {sec}
                    </option>
                  ))}
                </select>
              </div>

              {/* Report Date Filter Dropdown */}
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-ink-dim select-none">
                  Report Date:
                </span>
                <select
                  value={dateFilter}
                  onChange={(e) => changeDate(e.target.value)}
                  aria-label="Filter by Report Date"
                  className="bg-[#05070a] border border-panel-line rounded-[10px] px-3 py-1.5 font-mono text-[11px] text-white focus:border-teal outline-none cursor-pointer transition-colors"
                >
                  <option value="ALL">
                    All Dates ({filterOptions.report_dates.length})
                  </option>
                  {filterOptions.report_dates.map((d) => (
                    <option key={d} value={d}>
                      {d}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Table Container */}
          <div className="overflow-x-auto custom-scrollbar">
            <table className="w-full text-left whitespace-nowrap border-collapse">
              <thead className="sticky top-0 bg-[#05070a] border-b border-panel-line text-ink-dim select-none z-10">
                <tr>
                  <th
                    className="pl-8 pr-4 py-5 label-caps sticky left-0 z-30 bg-[#05070a] border-r border-panel-line shadow-[4px_0_12px_rgba(0,0,0,0.6)]"
                    aria-sort={getAriaSort("ticker")}
                  >
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
                  <th className="px-6 py-5 label-caps" aria-sort={getAriaSort("analysis_date")}>
                    <button
                      onClick={() => handleSort("analysis_date")}
                      className="flex items-center gap-2 group text-left label-caps hover:text-white transition-colors cursor-pointer outline-none focus-visible:text-teal"
                    >
                      Analysis Date
                      {renderSortIndicator("analysis_date")}
                    </button>
                  </th>
                  <th className="px-6 py-5 label-caps" aria-sort={getAriaSort("report_date")}>
                    <button
                      onClick={() => handleSort("report_date")}
                      className="flex items-center gap-2 group text-left label-caps hover:text-white transition-colors cursor-pointer outline-none focus-visible:text-teal"
                    >
                      Report Date
                      {renderSortIndicator("report_date")}
                    </button>
                  </th>
                  <th className="px-6 py-5 label-caps" aria-sort={getAriaSort("fiscal_period")}>
                    <button
                      onClick={() => handleSort("fiscal_period")}
                      className="flex items-center gap-2 group text-left label-caps hover:text-white transition-colors cursor-pointer outline-none focus-visible:text-teal"
                    >
                      Period
                      {renderSortIndicator("fiscal_period")}
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
                  <th className="px-6 py-5 label-caps" aria-sort={getAriaSort("expected_eps")}>
                    <button
                      onClick={() => handleSort("expected_eps")}
                      className="flex items-center gap-2 group text-left label-caps hover:text-white transition-colors cursor-pointer outline-none focus-visible:text-teal"
                    >
                      Expected EPS
                      {renderSortIndicator("expected_eps")}
                    </button>
                  </th>
                  <th className="px-6 py-5 label-caps" aria-sort={getAriaSort("actual_eps")}>
                    <button
                      onClick={() => handleSort("actual_eps")}
                      className="flex items-center gap-2 group text-left label-caps hover:text-white transition-colors cursor-pointer outline-none focus-visible:text-teal"
                    >
                      Actual EPS
                      {renderSortIndicator("actual_eps")}
                    </button>
                  </th>
                  <th
                    className="px-6 py-5 label-caps"
                    aria-sort={getAriaSort("post_earnings_move")}
                  >
                    <button
                      onClick={() => handleSort("post_earnings_move")}
                      className="flex items-center gap-2 group text-left label-caps hover:text-white transition-colors cursor-pointer outline-none focus-visible:text-teal"
                    >
                      Post-Earnings Move
                      {renderSortIndicator("post_earnings_move")}
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
                  <th
                    className="pl-4 pr-8 py-5 text-right label-caps"
                    aria-sort={getAriaSort("outcome")}
                  >
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
                {rows.map((row) => (
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
                    {/* Ticker & Company Name (Frozen Column) */}
                    <td className="pl-8 pr-4 py-4 min-w-[160px] sticky left-0 z-20 bg-[#0b0f17] group-hover:bg-[#121927] border-r border-panel-line transition-colors shadow-[4px_0_12px_rgba(0,0,0,0.6)]">
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
                      {!row.sector || row.sector === "Unknown" ? "—" : row.sector}
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
                    <td className="px-6 py-4 text-sm text-white font-mono">
                      <span className="inline-flex items-center">
                        <span className="align-middle">
                          {new Date(row.reportDate).toLocaleDateString(undefined, {
                            year: "numeric",
                            month: "2-digit",
                            day: "2-digit",
                          })}
                        </span>
                        <SessionBadge timing={row.reportTiming} />
                      </span>
                    </td>

                    {/* Reporting Period */}
                    <td className="px-6 py-4">
                      {row.fiscalPeriod ? (
                        <span className="px-2 py-1 rounded-md bg-teal/8 border border-teal/20 text-teal font-mono text-[11px] font-bold tracking-wider select-none">
                          {row.fiscalPeriod}
                        </span>
                      ) : (
                        <span className="text-ink-dim/40 font-mono text-sm">—</span>
                      )}
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
                        <span className="font-data text-white text-sm">{row.confidence}%</span>
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
                          className={row.postEarningsMove >= 0 ? "text-bull" : "text-bear"}
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
                            row.brier <= 0.1 ? "text-bull-deep font-semibold" : "text-ink-mute"
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
          {rows.length === 0 && !loading && (
            <div className="flex flex-col items-center justify-center py-16 text-center select-none">
              <XCircle className="w-12 h-12 text-ink-dim mb-3" />
              <p className="text-gray-500 font-bold uppercase tracking-widest text-xs mb-4">
                {hasFilters
                  ? "No predictions match this filter"
                  : "No analyses yet — run one from the dashboard"}
              </p>
              {hasFilters && (
                <button
                  onClick={handleReset}
                  className="px-4 py-2 bg-teal text-black rounded-lg text-xs font-black uppercase tracking-widest hover:bg-teal/80 transition-colors cursor-pointer"
                >
                  Reset Filters
                </button>
              )}
            </div>
          )}

          {/* Pagination Footer */}
          {total > 0 && (
            <div className="px-6 py-4 border-t border-panel-line bg-white/[0.01] flex items-center justify-between flex-wrap gap-4 select-none">
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-ink-dim">
                  Rows:
                </span>
                <select
                  value={pageSize}
                  onChange={(e) => changePageSize(Number(e.target.value))}
                  aria-label="Rows per page"
                  className="bg-[#05070a] border border-panel-line rounded-[10px] px-3 py-1.5 font-mono text-[11px] text-white focus:border-teal outline-none cursor-pointer transition-colors"
                >
                  {PAGE_SIZE_OPTIONS.map((n) => (
                    <option key={n} value={n}>
                      {n}
                    </option>
                  ))}
                </select>
                <span className="text-[11px] font-mono text-ink-mute ml-2">
                  Page {currentPage} of {pageCount}
                </span>
              </div>

              <nav className="flex items-center gap-1" aria-label="History pagination">
                <button
                  onClick={() => goToPage(currentPage - 1)}
                  disabled={currentPage <= 1}
                  aria-label="Previous page"
                  className="p-2 rounded-lg text-ink-mute hover:text-teal hover:bg-teal/10 border border-panel-line transition-all cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:bg-transparent disabled:hover:text-ink-mute"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>

                {pageNumbers[0] > 1 && (
                  <span className="px-2 text-ink-dim font-mono text-[11px]">…</span>
                )}

                {pageNumbers.map((n) => (
                  <button
                    key={n}
                    onClick={() => goToPage(n)}
                    aria-current={n === currentPage ? "page" : undefined}
                    className={`min-w-[32px] px-2.5 py-1.5 rounded-md font-mono text-[11px] transition-all cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-teal ${
                      n === currentPage
                        ? "bg-teal/14 text-teal border border-teal/30"
                        : "text-ink-mute hover:text-white border border-transparent"
                    }`}
                  >
                    {n}
                  </button>
                ))}

                {pageNumbers[pageNumbers.length - 1] < pageCount && (
                  <span className="px-2 text-ink-dim font-mono text-[11px]">…</span>
                )}

                <button
                  onClick={() => goToPage(currentPage + 1)}
                  disabled={currentPage >= pageCount}
                  aria-label="Next page"
                  className="p-2 rounded-lg text-ink-mute hover:text-teal hover:bg-teal/10 border border-panel-line transition-all cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:bg-transparent disabled:hover:text-ink-mute"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </nav>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
