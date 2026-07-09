"use client";

import { useState, useRef, useEffect, useMemo } from "react";
import { useAuth } from "@clerk/nextjs";
import { Loader2, ArrowLeft, Terminal, AlertTriangle } from "lucide-react";
import { api, Prediction, PredictionMetrics } from "@/lib/api";
import AnalysisResult from "@/components/AnalysisResult";
import AnalysisHub from "@/components/dashboard/AnalysisHub";
import StatsRow from "@/components/dashboard/StatsRow";
import PredictionsTable from "@/components/dashboard/PredictionsTable";

interface WSMessage {
  status: string;
  message: string;
  agent?: string;
  type?: string;
}

export default function DashboardPage() {
  const { getToken } = useAuth();
  const [ticker, setTicker] = useState("");
  const [reportDate, setReportDate] = useState("");
  const [userAnalysis, setUserAnalysis] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<Prediction | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [messages, setMessages] = useState<WSMessage[]>([]);
  const [agentStreams, setAgentStreams] = useState<{
    Bull: string;
    Bear: string;
    Quant: string;
    Consensus: string;
  }>({ Bull: "", Bear: "", Quant: "", Consensus: "" });
  const [metrics, setMetrics] = useState<PredictionMetrics | null>(null);
  const [realPredictions, setRealPredictions] = useState<Prediction[]>([]);
  const [limit, setLimit] = useState<number>(5);
  const [loadingHistory, setLoadingHistory] = useState<boolean>(true);

  const terminalEndRef = useRef<HTMLDivElement>(null);

  const fetchHistory = async () => {
    try {
      setLoadingHistory(true);
      const token = await getToken();
      if (token) {
        const data = await api.getPredictionHistory(token);
        setRealPredictions(data || []);
      }
    } catch (err) {
      console.error("Failed to load prediction history", err);
    } finally {
      setLoadingHistory(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [getToken]);

  const mappedPredictionRows = useMemo(() => {
    const sorted = realPredictions.slice(0, limit);
    return sorted.map((p) => {
      let consensus: "BEAT" | "MISS" | "INLINE" = "BEAT";
      const dir = (p.direction || "").toUpperCase();
      if (dir === "MISS") {
        consensus = "MISS";
      } else if (dir === "INLINE" || dir === "MEET" || dir === "NEUTRAL") {
        consensus = "INLINE";
      }
      
      const status: "VALIDATED" | "PENDING" = p.actual_direction ? "VALIDATED" : "PENDING";
      
      let targetDate = "";
      if (p.report_date) {
        if (typeof p.report_date === "string") {
          targetDate = p.report_date.split("T")[0];
        } else {
          try {
            targetDate = new Date(p.report_date).toISOString().split("T")[0];
          } catch {
            targetDate = String(p.report_date);
          }
        }
      }
      
      return {
        ticker: p.ticker,
        sector: p.sector || undefined,
        targetDate: targetDate,
        status: status,
        consensus: consensus,
        confidence: Math.round(p.confidence * 100),
      };
    });
  }, [realPredictions, limit]);

  const scrollToBottom = () => {
    terminalEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    if (loading) {
      scrollToBottom();
    }
  }, [messages, loading]);

  useEffect(() => {
    async function loadMetrics() {
      try {
        const token = await getToken();
        if (token) {
          const m = await api.getMetrics(token).catch(() => null);
          if (m) setMetrics(m);
        }
      } catch (err) {
        console.error("Failed to load metrics", err);
      }
    }
    loadMetrics();
  }, [getToken]);

  const handleRunAnalysis = async () => {
    if (!ticker || !reportDate) {
      setError("Please provide both ticker and report date.");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);
    setMessages([]);
    setAgentStreams({ Bull: "", Bear: "", Quant: "", Consensus: "" });

    let ws: WebSocket | null = null;

    try {
      const token = await getToken();
      if (!token) throw new Error("Not authenticated");

      // 1. Start Analysis
      const { task_id } = await api.predictTicker(ticker, reportDate, token, userAnalysis);

      // Setup WebSocket
      const wsUrl = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";
      ws = new WebSocket(`${wsUrl}/ws/task/${task_id}`);

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "stream" && data.agent) {
            setAgentStreams((prev) => ({
              ...prev,
              [data.agent as keyof typeof prev]:
                prev[data.agent as keyof typeof prev] + data.message,
            }));
          } else if (data.message) {
            setMessages((prev) => [...prev, data]);
          }
        } catch (e) {
          console.error("Failed to parse WS message", e);
        }
      };

      ws.onerror = (e) => {
        console.error("WebSocket Error:", e);
      };

      // 2. Poll for Status
      let isReady = false;
      let attempts = 0;
      const maxAttempts = 60; // 120 seconds max

      while (!isReady && attempts < maxAttempts) {
        const statusData = await api.getTaskStatus(task_id, token);

        if (statusData.ready) {
          isReady = true;
          if (statusData.error) {
            throw new Error(statusData.error);
          }
          setResult(statusData.result.result || statusData.result);
        } else {
          attempts++;
          await new Promise((resolve) => setTimeout(resolve, 2000));
        }
      }

      if (!isReady) {
        throw new Error("Analysis timed out. Please check prediction history later.");
      }
      
      // Reload history to show the newly ran prediction immediately
      fetchHistory();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "An error occurred during analysis.");
    } finally {
      setLoading(false);
      setMessages([]); // Clear toast messages after completion
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    }
  };

  const getAgentColor = (agent: string) => {
    const a = agent.toLowerCase();
    if (a === "bull") return "text-bull";
    if (a === "bear") return "text-bear";
    if (a === "quant") return "text-quant";
    return "text-teal";
  };

  return (
    <div className="flex flex-col gap-[24px] pb-20">
      {/* App Header */}
      <header className="flex justify-between items-end mb-[24px] select-none">
        <div>
          <h1 className="text-[clamp(1.9rem,3vw,2.3rem)] font-display font-semibold tracking-tight text-white mb-2 leading-none">
            Dashboard Overview
          </h1>
          <p className="text-ink-mute font-body text-sm font-medium">
            Your intelligent hub for AI-driven earnings forecasts.
          </p>
        </div>
      </header>

      {/* AI Analysis Hub Component */}
      <AnalysisHub
        ticker={ticker}
        setTicker={setTicker}
        reportDate={reportDate}
        setReportDate={setReportDate}
        userAnalysis={userAnalysis}
        setUserAnalysis={setUserAnalysis}
        onRunAnalysis={handleRunAnalysis}
        loading={loading}
      />

      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-xl text-sm text-red-400 font-bold flex items-start gap-3 select-none">
          <AlertTriangle className="w-5 h-5 text-bear flex-shrink-0" />
          <span className="pt-0.5">{error}</span>
        </div>
      )}

      {/* Live Stats Row */}
      <StatsRow metrics={metrics} />

      {/* Main Section */}
      <div className="min-h-[500px] flex flex-col">
        {/* Section Header */}
        {(loading || result) && (
          <div className="flex items-center justify-between mb-4 border-b border-panel-line pb-4 select-none">
            <h2 className="text-sm font-mono font-bold text-ink-mute uppercase tracking-widest">
              {loading
                ? "Live Agent Debate Panel"
                : "Comprehensive Analysis Results"}
            </h2>
            {result && (
              <button
                onClick={() => setResult(null)}
                className="text-[11px] font-mono font-bold px-4 py-2 bg-white/5 rounded-lg text-white hover:bg-white/10 uppercase tracking-widest transition-colors flex items-center gap-2 cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-teal"
              >
                <ArrowLeft className="w-3.5 h-3.5" /> Back to Dashboard
              </button>
            )}
          </div>
        )}

        {/* Content Render */}
        {loading ? (
          /* Live Debate Console UI */
          <div className="flex-1 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6 auto-rows-fr min-h-[450px]">
            {(["Bull", "Bear", "Quant", "Consensus"] as const).map((agentName) => {
              const isStreaming = agentStreams[agentName] !== "";
              return (
                <div
                  key={agentName}
                  className="p-6 rounded-2xl border border-panel-line bg-panel flex flex-col font-mono text-xs relative overflow-hidden h-full shadow-xl"
                >
                  {/* Top Color Line */}
                  <div
                    className={`absolute top-0 left-0 w-full h-[3px] bg-linear-to-r from-transparent via-current to-transparent opacity-80 ${getAgentColor(
                      agentName
                    )}`}
                  ></div>

                  {/* Header info */}
                  <div className="flex items-center justify-between mb-4 pb-3 border-b border-panel-line shrink-0 mt-1 select-none">
                    <span
                      className={`font-mono font-bold uppercase tracking-widest text-xs flex items-center gap-2 ${getAgentColor(
                        agentName
                      )}`}
                    >
                      <Terminal className="w-4 h-4" />
                      {agentName} Node
                    </span>
                    {isStreaming ? (
                      <span className="text-[9px] text-teal uppercase flex items-center gap-1.5 font-bold tracking-widest">
                        <Loader2 className="w-3 h-3 animate-spin" /> Live Stream
                      </span>
                    ) : (
                      <span className="text-[9px] text-ink-dim uppercase flex items-center gap-1.5 font-bold tracking-widest">
                        <span className="w-1.5 h-1.5 rounded-full bg-panel-line animate-pulse" /> Awaiting
                      </span>
                    )}
                  </div>

                  {/* Output Text Stream */}
                  <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar text-ink-mute leading-relaxed font-mono text-[12px] flex flex-col justify-end">
                    <div ref={terminalEndRef} className="whitespace-pre-wrap mt-auto">
                      {agentStreams[agentName] ||
                        "Initializing agent pipeline. Listening for consensus debate tokens..."}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        ) : result ? (
          /* Analysis Result Display */
          <div className="bg-panel p-2 rounded-2xl border border-panel-line shadow-lg">
            <AnalysisResult result={result} />
          </div>
        ) : (
          /* Interactive Predictions Table */
          <PredictionsTable
            predictions={mappedPredictionRows}
            limit={limit}
            onLimitChange={setLimit}
            onRowClick={(row) => {
              const found = realPredictions.find(
                (p) =>
                  p.ticker === row.ticker &&
                  (p.report_date || "").startsWith(row.targetDate)
              );
              if (found) {
                setResult(found);
              } else {
                const mapped: Prediction = {
                  ticker: row.ticker,
                  company_name: getCompanyName(row.ticker),
                  report_date: row.targetDate,
                  prediction_date: row.targetDate,
                  direction: row.consensus,
                  confidence: row.confidence / 100,
                  reasoning_summary: getMockReasoning(row.ticker),
                  debate_summary: getMockDebate(row.ticker),
                  bull_factors: getMockFactors().bull,
                  bear_factors: getMockFactors().bear,
                };
                setResult(mapped);
              }
            }}
          />
        )}
      </div>

      {/* Floating Status Notification Toasts */}
      {messages.length > 0 && (
        <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-3 pointer-events-none max-w-sm w-full select-none">
          {messages.slice(-3).map((m, i) => {
            const isError = m.message.includes("Error") || m.message.includes("Limit");
            return (
              <div
                key={i}
                className="bg-panel/95 border border-panel-line p-4 rounded-2xl shadow-[0_8px_30px_rgba(0,0,0,0.5)] backdrop-blur-md animate-in slide-in-from-right fade-in duration-300"
              >
                <div className="flex items-center gap-3">
                  {isError ? (
                    <AlertTriangle className="w-5 h-5 text-bear animate-bounce" />
                  ) : (
                    <Loader2 className="w-5 h-5 text-teal animate-spin" />
                  )}
                  <div>
                    {m.agent && (
                      <p className="text-[9px] font-mono font-bold uppercase tracking-widest text-ink-dim mb-0.5">
                        {m.agent}
                      </p>
                    )}
                    <p className="text-xs font-body font-semibold text-white leading-snug">
                      {m.message}
                    </p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// Mock prediction data mapping helpers for dashboard clicks
const getCompanyName = (ticker: string) => {
  const names: Record<string, string> = {
    PRGS: "Progress Software Corporation",
    NKE: "Nike, Inc.",
    LNN: "Lindsay Corporation",
    MS: "Morgan Stanley",
    PENG: "Penguin Solutions, Inc.",
  };
  return names[ticker] || `${ticker} Corp.`;
};

const getMockReasoning = (ticker: string) => {
  return `Based on multi-agent consensus, ${ticker} exhibits a strong probability of aligning with the projected forecast. Institutional sentiment combined with call options volume indicates positive momentum leading into the report.`;
};

const getMockDebate = (ticker: string) => {
  return `BULL (Buy-side Agent):\nWe expect a strong revenue beat for ${ticker} driven by sector strength and high customer retention. Operational leverage will drive earnings per share above guidance.\n\nBEAR (Short Case Agent):\nMacro headwinds and rising R&D expenses pose downside risks to ${ticker}'s margins. New client contracts are pacing slower than expected.\n\nQUANT (Options & Flow Agent):\nOptions chain data shows implied movement of ±7.4% for ${ticker}. Concentrated volume in call options indicates upward pressure.\n\nCONSENSUS (Consensus Decision):\nThe consensus points to a favorable outcome for ${ticker} backed by solid demand, though margin pressures warrant caution.`;
};

const getMockFactors = () => {
  return {
    bull: ["Strong customer retention", "Positive options volume", "Operational leverage"],
    bear: ["Macro headwinds", "Rising R&D costs", "Slower contract pacing"],
  };
};
