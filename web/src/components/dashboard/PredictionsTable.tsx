"use client";

import React, { useState, useMemo } from "react";
import Link from "next/link";
import { Search, ChevronUp, ChevronDown, ArrowUpDown, XCircle } from "lucide-react";
import { MOCK_PREDICTIONS, PredictionRow, Consensus, PredictionStatus } from "./predictions.types";
import ConsensusPill from "./ConsensusPill";
import StatusBadge from "./StatusBadge";

type SortKey = "ticker" | "targetDate" | "status" | "consensus" | "confidence";
type SortDir = "asc" | "desc" | "none";

interface PredictionsTableProps {
  predictions?: PredictionRow[];
  onRowClick?: (row: PredictionRow) => void;
  limit?: number;
  onLimitChange?: (limit: number) => void;
}

export default function PredictionsTable({ onRowClick, predictions, limit, onLimitChange }: PredictionsTableProps) {
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<"ALL" | PredictionStatus>("ALL");
  const [consensusFilter, setConsensusFilter] = useState<"ALL" | Consensus>("ALL");
  const [sortKey, setSortKey] = useState<SortKey>("targetDate");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const dataList = predictions || MOCK_PREDICTIONS;

  // Handle header click to cycle: none -> asc -> desc -> none
  const handleSort = (key: SortKey) => {
    if (sortKey !== key) {
      setSortKey(key);
      setSortDir("asc");
    } else {
      if (sortDir === "asc") {
        setSortDir("desc");
      } else if (sortDir === "desc") {
        setSortDir("none");
      } else {
        setSortDir("asc");
      }
    }
  };

  // Reset all filters
  const handleReset = () => {
    setQuery("");
    setStatusFilter("ALL");
    setConsensusFilter("ALL");
    setSortKey("targetDate");
    setSortDir("desc");
  };

  // Helper for sorting
  const compareBy = (key: SortKey, dir: SortDir) => {
    return (a: PredictionRow, b: PredictionRow) => {
      if (dir === "none") return 0;
      let valA = a[key];
      let valB = b[key];

      if (key === "targetDate") {
        valA = new Date(a.targetDate).getTime();
        valB = new Date(b.targetDate).getTime();
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

  // Filter and sort prediction rows
  const processedRows = useMemo(() => {
    return dataList
      .filter((r) => r.ticker.toLowerCase().includes(query.trim().toLowerCase()))
      .filter((r) => statusFilter === "ALL" || r.status === statusFilter)
      .filter((r) => consensusFilter === "ALL" || r.consensus === consensusFilter)
      .slice()
      .sort(compareBy(sortKey, sortDir));
  }, [dataList, query, statusFilter, consensusFilter, sortKey, sortDir]);

  // Render sorting arrows helper
  const renderSortIndicator = (key: SortKey) => {
    if (sortKey !== key || sortDir === "none") {
      return <ArrowUpDown className="w-3.5 h-3.5 opacity-30 group-hover:opacity-75 transition-opacity" />;
    }
    return sortDir === "asc" ? (
      <ChevronUp className="w-3.5 h-3.5 text-teal" />
    ) : (
      <ChevronDown className="w-3.5 h-3.5 text-teal" />
    );
  };

  // Get Aria-Sort attribute value
  const getAriaSort = (key: SortKey) => {
    if (sortKey !== key || sortDir === "none") return "none";
    return sortDir === "asc" ? "ascending" : "descending";
  };

  // Get color for confidence bar
  const getConfidenceBarColor = (score: number) => {
    if (score >= 80) return "bg-bull";
    if (score >= 60) return "bg-teal";
    return "bg-bear";
  };

  return (
    <div className="flex-1 rounded-[16px] border border-[#26334A] bg-panel overflow-hidden flex flex-col shadow-[0_20px_60px_rgba(0,0,0,0.35)]">
      {/* Table Top Header */}
      <div className="px-6 py-[22px] border-b border-panel-line flex items-center justify-between flex-wrap gap-4 select-none">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-display font-semibold text-white uppercase tracking-wider">
            Recent Predictions
          </h2>
          <span className="text-[11px] font-mono font-bold text-ink-mute bg-[var(--color-panel-sunk)] border border-panel-line px-2.5 py-1 rounded-[8px] select-none">
            Showing {processedRows.length} of {dataList.length}
          </span>
          {onLimitChange && (
            <div className="flex items-center gap-1.5 text-[11px] font-mono font-bold text-ink-mute bg-[var(--color-panel-sunk)] border border-panel-line px-2.5 py-1 rounded-[8px] select-none">
              <span>Show:</span>
              <select
                value={limit || 5}
                onChange={(e) => onLimitChange(Number(e.target.value))}
                className="bg-transparent text-white focus:outline-none cursor-pointer font-bold border-none p-0 outline-none"
              >
                <option value={5} className="bg-panel text-white">5</option>
                <option value={10} className="bg-panel text-white">10</option>
                <option value={25} className="bg-panel text-white">25</option>
                <option value={50} className="bg-panel text-white">50</option>
                <option value={100} className="bg-panel text-white">100</option>
              </select>
            </div>
          )}
        </div>
        <Link
          href="/dashboard/history"
          className="text-xs font-mono font-bold text-teal hover:text-[#7DE8DA] transition-colors uppercase tracking-widest flex items-center gap-1.5 focus-visible:ring-2 focus-visible:ring-teal outline-none rounded"
        >
          View full ledger &rarr;
        </Link>
      </div>

      {/* Controls: Search and Filters */}
      <div className="p-6 border-b border-panel-line bg-white/[0.01] flex flex-wrap gap-3 items-center justify-between">
        {/* Search */}
        <div className="relative w-full sm:w-72">
          <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-ink-dim select-none">
            <Search className="w-4 h-4" />
          </span>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by Ticker..."
            aria-label="Search predictions by stock ticker"
            className="w-full bg-[#05070a] border border-panel-line rounded-xl pl-10 pr-4 py-2.5 focus:border-teal focus:ring-2 focus:ring-teal/20 outline-none text-sm text-white placeholder-white/20 transition-all font-body"
          />
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Status Filter */}
          <div className="flex items-center gap-2.5">
            <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-ink-dim select-none">
              Status:
            </span>
            <div className="flex gap-0.5 p-1 bg-[var(--color-panel-sunk)] border border-panel-line rounded-[10px] select-none">
              {(["ALL", "VALIDATED", "PENDING"] as const).map((s) => (
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
                  {s === "ALL" ? "All" : s === "VALIDATED" ? "Validated" : "Pending"}
                </button>
              ))}
            </div>
          </div>

          {/* Consensus Filter */}
          <div className="flex items-center gap-2.5">
            <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-ink-dim select-none">
              Consensus:
            </span>
            <div className="flex gap-0.5 p-1 bg-[var(--color-panel-sunk)] border border-panel-line rounded-[10px] select-none">
              {(["ALL", "BEAT", "MISS", "INLINE"] as const).map((c) => (
                <button
                  key={c}
                  onClick={() => setConsensusFilter(c)}
                  className={`px-3 py-1.5 rounded-md font-mono text-[11px] uppercase transition-all select-none cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-teal
                    ${
                      consensusFilter === c
                        ? "bg-teal/14 text-teal"
                        : "text-ink-mute hover:text-white"
                    }`}
                >
                  {c}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Predictions Table Grid */}
      <div className="overflow-x-auto">
        <table className="w-full text-left whitespace-nowrap border-collapse">
          <thead>
            <tr className="bg-[#05070a] border-b border-panel-line text-ink-dim select-none">
              <th className="px-8 py-5 label-caps" aria-sort={getAriaSort("ticker")}>
                <button
                  onClick={() => handleSort("ticker")}
                  className="flex items-center gap-2 group text-left label-caps hover:text-white transition-colors cursor-pointer outline-none focus-visible:text-teal"
                >
                  Ticker
                  {renderSortIndicator("ticker")}
                </button>
              </th>
              <th className="px-8 py-5 label-caps text-left text-ink-dim font-semibold">
                Sector
              </th>
              <th className="px-8 py-5 label-caps" aria-sort={getAriaSort("targetDate")}>
                <button
                  onClick={() => handleSort("targetDate")}
                  className="flex items-center gap-2 group text-left label-caps hover:text-white transition-colors cursor-pointer outline-none focus-visible:text-teal"
                >
                  Target Date
                  {renderSortIndicator("targetDate")}
                </button>
              </th>
              <th className="px-8 py-5 label-caps" aria-sort={getAriaSort("status")}>
                <button
                  onClick={() => handleSort("status")}
                  className="flex items-center gap-2 group text-left label-caps hover:text-white transition-colors cursor-pointer outline-none focus-visible:text-teal"
                >
                  Status
                  {renderSortIndicator("status")}
                </button>
              </th>
              <th className="px-8 py-5 text-center label-caps" aria-sort={getAriaSort("consensus")}>
                <button
                  onClick={() => handleSort("consensus")}
                  className="flex items-center gap-2 mx-auto group text-center label-caps hover:text-white transition-colors cursor-pointer outline-none focus-visible:text-teal"
                >
                  Consensus
                  {renderSortIndicator("consensus")}
                </button>
              </th>
              <th className="px-8 py-5 text-right label-caps" aria-sort={getAriaSort("confidence")}>
                <button
                  onClick={() => handleSort("confidence")}
                  className="flex items-center gap-2 ml-auto group text-right label-caps hover:text-white transition-colors cursor-pointer outline-none focus-visible:text-teal"
                >
                  Confidence Score
                  {renderSortIndicator("confidence")}
                </button>
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5 font-body">
            {processedRows.length > 0 ? (
              processedRows.map((row) => (
                <tr
                  key={row.ticker + row.targetDate}
                  onClick={() => onRowClick?.(row)}
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      onRowClick?.(row);
                    }
                  }}
                  className="hover:bg-white/[0.03] transition-colors duration-150 group cursor-pointer h-[70px] outline-none focus-visible:bg-white/[0.04]"
                >
                  <td className="px-8 py-4 font-display font-semibold text-white group-hover:text-teal transition-colors text-lg">
                    {row.ticker}
                  </td>
                  <td className="px-8 py-4 text-sm text-ink-mute font-medium">
                    {(!row.sector || row.sector === "Unknown") ? "—" : row.sector}
                  </td>
                  <td className="px-8 py-4 text-sm text-ink-mute font-medium">
                    {new Date(row.targetDate).toLocaleDateString(undefined, {
                      year: "numeric",
                      month: "short",
                      day: "numeric",
                    })}
                  </td>
                  <td className="px-8 py-4">
                    <StatusBadge status={row.status} />
                  </td>
                  <td className="px-8 py-4 text-center">
                    <ConsensusPill consensus={row.consensus} />
                  </td>
                  <td className="px-8 py-4 text-right">
                    <div className="flex items-center justify-end gap-3 select-none">
                      <span className="font-data font-semibold text-2xl tracking-tight text-white group-hover:text-teal transition-colors select-none">
                        {row.confidence}<span className="text-ink-dim text-lg select-none">%</span>
                      </span>
                      <div className="w-[64px] h-[5px] bg-white/10 rounded-full overflow-hidden select-none flex-shrink-0">
                        <div
                          className={`h-full ${getConfidenceBarColor(row.confidence)}`}
                          style={{ width: `${row.confidence}%` }}
                        ></div>
                      </div>
                    </div>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={6} className="px-8 py-16 text-center select-none">
                  <div className="flex flex-col items-center justify-center gap-4">
                    <XCircle className="w-12 h-12 text-ink-dim opacity-30 animate-pulse" />
                    <span className="text-ink-mute text-sm font-semibold tracking-wider font-display">
                      No predictions match these filters
                    </span>
                    <button
                      onClick={handleReset}
                      className="px-5 py-2 bg-teal/15 border border-teal/30 hover:bg-teal/25 text-teal font-mono font-semibold text-xs uppercase tracking-widest rounded-lg transition-all duration-150 outline-none focus-visible:ring-2 focus-visible:ring-teal cursor-pointer"
                    >
                      Reset Filters
                    </button>
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
