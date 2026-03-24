"use client";

import { useState, useRef, useEffect } from "react";
import { useAuth } from "@clerk/nextjs";
import { api, Prediction } from "@/lib/api";
import AnalysisResult from "@/components/AnalysisResult";

const stats = [
    { label: "Total Analyses", value: "1,284", icon: "🔍", color: "var(--accent-cyan)", subtext: "+14% this week" },
    { label: "Success Rate", value: "78.4%", icon: "🎯", color: "var(--bull-green)", subtext: "Top 1% of models" },
    { label: "Active Monitors", value: "12", icon: "🔔", color: "var(--quant-blue)", subtext: "3 alerts triggered" },
    { label: "Avg Confidence", value: "84%", icon: "📊", color: "var(--consensus-purple)", subtext: "Across all sectors" },
];

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
    const [history, setHistory] = useState<Prediction[]>([]);

    const terminalEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        terminalEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        if (loading) {
            scrollToBottom();
        }
    }, [messages, loading]);

    useEffect(() => {
        if (loading) {
            scrollToBottom();
        }
    }, [messages, loading]);

    useEffect(() => {
        async function loadHistory() {
            try {
                const token = await getToken();
                if (token) {
                    const data = await api.getPredictionHistory(token);
                    setHistory(data.slice(0, 5)); // show top 5
                }
            } catch (err) {
                console.error("Failed to load history", err);
            }
        }
        loadHistory();
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
                        setAgentStreams(prev => ({
                            ...prev,
                            [data.agent as keyof typeof prev]: prev[data.agent as keyof typeof prev] + data.message
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
            }

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
                    await new Promise(resolve => setTimeout(resolve, 2000));
                }
            }

            if (!isReady) {
                throw new Error("Analysis timed out. Please check history later.");
            }

        } catch (err: any) {
            setError(err.message || "An error occurred during analysis.");
        } finally {
            setLoading(false);
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.close();
            }
        }
    };



    const getAgentColor = (agent?: string) => {
        if (!agent) return "text-gray-400";
        const a = agent.toLowerCase();
        if (a === "bull") return "text-bull text-shadow-bull";
        if (a === "bear") return "text-bear text-shadow-bear";
        if (a === "quant") return "text-blue-400";
        if (a === "consensus") return "text-purple-400";
        return "text-accent";
    };

    return (
        <div className="space-y-10 pb-20">
            <header className="mb-10">
                <h1 className="text-4xl lg:text-5xl font-extrabold tracking-tight mb-3 font-outfit text-white">Dashboard Overview</h1>
                <p className="text-gray-400 font-medium text-lg">Your intelligent hub for AI-driven earnings forecasts.</p>
            </header>

            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {stats.map((stat) => (
                    <div key={stat.label} className="relative overflow-hidden p-8 rounded-3xl border border-white/10 bg-[#0c1017] group hover:border-white/20 hover:shadow-[0_0_30px_rgba(45,212,191,0.05)] transition-all duration-300 transform hover:-translate-y-1">
                        <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-bl from-white/5 to-transparent rounded-bl-full -z-0 opacity-50 group-hover:opacity-100 transition-opacity duration-300"></div>
                        <div className="relative z-10 flex justify-between items-start mb-6">
                            <span className="text-3xl drop-shadow-lg">{stat.icon}</span>
                            <div
                                className="w-2.5 h-2.5 rounded-full ring-4 ring-black/20"
                                style={{ backgroundColor: stat.color, boxShadow: `0 0 15px ${stat.color}` }}
                            />
                        </div>
                        <p className="relative z-10 text-xs font-bold text-gray-500 uppercase tracking-widest mb-1">{stat.label}</p>
                        <p className="relative z-10 text-4xl font-black text-white tracking-tight mb-2">{stat.value}</p>
                        <p className="relative z-10 text-[10px] font-semibold text-gray-500 tracking-wide uppercase">{stat.subtext}</p>
                    </div>
                ))}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-10 mt-6 min-h-[500px]">
                {/* Main Content Area */}
                <div className="lg:col-span-2 space-y-6 flex flex-col">
                    <div className="flex items-center justify-between px-2">
                        <h2 className="text-2xl font-bold font-outfit text-white">
                            {loading ? "Agent Debate in Progress" : result ? "Analysis Results" : "Recent Predictions"}
                        </h2>
                        {!loading && (
                            result ? (
                                <button onClick={() => setResult(null)} className="text-xs font-bold text-accent hover:text-white uppercase tracking-widest transition-colors flex items-center gap-2">&larr; Back to Overview</button>
                            ) : (
                                <a href="/dashboard/history" className="text-xs font-bold text-accent hover:text-white uppercase tracking-widest transition-colors flex items-center gap-2">View History &rarr;</a>
                            )
                        )}
                    </div>

                    {loading ? (
                        <div className="flex-1 grid grid-cols-2 gap-4 auto-rows-fr min-h-[500px]">
                            {['Bull', 'Bear', 'Quant', 'Consensus'].map((agentName) => (
                                <div key={agentName} className="glass p-5 rounded-3xl border border-white/5 bg-[#0c1017] shadow-xl flex flex-col font-mono text-xs relative overflow-hidden h-full">
                                    <div className="flex items-center justify-between mb-4 pb-3 border-b border-white/10 shrink-0">
                                        <span className={`font-black uppercase tracking-widest text-[11px] ${getAgentColor(agentName)}`}>{agentName} Agent</span>
                                        {agentStreams[agentName as keyof typeof agentStreams] === "" ? (
                                            <span className="text-[9px] text-gray-500 uppercase flex items-center gap-1.5 font-bold tracking-widest">
                                                <div className="w-1.5 h-1.5 rounded-full bg-gray-500 animate-pulse"></div> Waiting
                                            </span>
                                        ) : (
                                            <span className="text-[9px] text-accent uppercase flex items-center gap-1.5 font-bold tracking-widest">
                                                <div className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse"></div> Thinking
                                            </span>
                                        )}
                                    </div>
                                    <div className="flex-1 overflow-y-auto pr-3 custom-scrollbar text-gray-300 leading-relaxed font-outfit text-sm flex flex-col justify-end">
                                        <span className="whitespace-pre-wrap mt-auto">
                                            {agentStreams[agentName as keyof typeof agentStreams] || "Connection established. Awaiting analysis..."}
                                        </span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : result ? (
                        <AnalysisResult result={result} />
                    ) : (
                        <div className="flex-1 glass rounded-3xl overflow-hidden border border-white/5 bg-[#0c1017]">
                            <div className="max-h-[500px] overflow-y-auto custom-scrollbar">
                                <table className="w-full text-left">
                                    <thead className="bg-[#080b11] border-b border-white/10 sticky top-0 z-10">
                                        <tr className="text-[10px] font-bold uppercase tracking-[0.15em] text-gray-400">
                                            <th className="px-8 py-6">Ticker</th>
                                            <th className="px-8 py-6 hidden sm:table-cell">Status</th>
                                            <th className="px-8 py-6 text-center">Prediction</th>
                                            <th className="px-8 py-6 text-right">Confidence</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-white/5">
                                        {history.length > 0 ? history.map((row) => (
                                            <tr key={row.ticker + row.prediction_date} onClick={() => setResult(row)} className="hover:bg-white/[0.02] transition-colors group cursor-pointer">
                                                <td className="px-8 py-6 font-black text-white group-hover:pl-10 group-hover:text-accent transition-all text-lg">{row.ticker}</td>
                                                <td className="px-8 py-6 text-sm text-gray-400 font-medium hidden sm:table-cell">Analyzed</td>
                                                <td className="px-8 py-6 text-center">
                                                    <span
                                                        className={`px-5 py-1.5 rounded-full text-xs font-black
                                                            ${row.direction === 'BEAT' ? 'bg-bull/10 text-bull border-bull/30 border' :
                                                              row.direction === 'MISS' ? 'bg-bear/10 text-bear border-bear/30 border' :
                                                              'bg-gray-500/10 text-gray-400 border-gray-500/30 border'}`}
                                                    >
                                                        {row.direction}
                                                    </span>
                                                </td>
                                                <td className="px-8 py-6 text-right font-mono font-bold text-xl tracking-tight text-white group-hover:text-accent transition-colors">{(row.confidence * 100).toFixed(0)}%</td>
                                            </tr>
                                        )) : (
                                            <tr>
                                                <td colSpan={4} className="px-8 py-6 text-center text-gray-500 text-sm font-bold uppercase tracking-widest">
                                                    No recent predictions found.
                                                </td>
                                            </tr>
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}
                </div>

                {/* Quick Analysis Form */}
                <div className="space-y-6">
                    <h2 className="text-2xl font-bold font-outfit px-2 text-white">Quick Analysis</h2>
                    <div className="glass p-8 rounded-3xl border border-white/10 bg-[#0c1017] space-y-8 shadow-2xl relative overflow-hidden group">
                        <div className="absolute top-0 inset-x-0 h-1 bg-gradient-to-r from-transparent via-accent/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>

                        {loading && (
                            <div className="absolute inset-0 bg-black/60 backdrop-blur-md rounded-3xl z-10 flex flex-col items-center justify-center border border-accent/20">
                                <div className="relative w-16 h-16 mb-6">
                                    <div className="absolute inset-0 rounded-full border-4 border-white/10"></div>
                                    <div className="absolute inset-0 rounded-full border-4 border-transparent border-t-accent animate-spin"></div>
                                    <div className="absolute inset-0 flex items-center justify-center text-accent">
                                        <span className="animate-pulse">⚡</span>
                                    </div>
                                </div>
                                <p className="text-accent font-bold animate-pulse text-xs tracking-[0.2em] uppercase">Processing Data Pipeline</p>
                            </div>
                        )}

                        <div className="space-y-2.5">
                            <label className="text-[10px] font-bold uppercase tracking-[0.15em] text-gray-400">Stock Ticker</label>
                            <input
                                type="text"
                                value={ticker}
                                onChange={(e) => setTicker(e.target.value)}
                                placeholder="E.G. NVDA"
                                className="w-full bg-[#080b11] border border-white/10 rounded-2xl px-5 py-4 focus:border-accent focus:ring-1 focus:ring-accent/50 outline-none transition-all uppercase font-black text-lg tracking-wider text-white placeholder-white/20"
                            />
                        </div>
                        <div className="space-y-2.5">
                            <label className="text-[10px] font-bold uppercase tracking-[0.15em] text-gray-400">Report Date</label>
                            <input
                                type="date"
                                value={reportDate}
                                onChange={(e) => setReportDate(e.target.value)}
                                className="w-full bg-[#080b11] border border-white/10 rounded-2xl px-5 py-4 focus:border-accent focus:ring-1 focus:ring-accent/50 outline-none transition-all text-sm font-bold text-white relative [color-scheme:dark]"
                            />
                        </div>
                        <div className="space-y-2.5">
                            <div className="flex justify-between items-center">
                                <label className="text-[10px] font-bold uppercase tracking-[0.15em] text-gray-400">Your Analysis (Optional)</label>
                                <span className="text-[9px] text-accent/80 font-bold uppercase tracking-widest bg-accent/10 px-2 py-1 rounded-md">Analyst Agent</span>
                            </div>
                            <textarea
                                value={userAnalysis}
                                onChange={(e) => setUserAnalysis(e.target.value)}
                                placeholder="Include your prompt/analysis to be incorporated into the consensus."
                                className="w-full bg-[#080b11] border border-white/10 rounded-2xl px-5 py-4 focus:border-accent focus:ring-1 focus:ring-accent/50 outline-none transition-all text-sm font-bold text-white relative placeholder-white/20 min-h-[100px] resize-y custom-scrollbar"
                            />
                        </div>

                        {error && (
                            <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-xs text-red-500 font-bold flex items-start gap-3">
                                <span>⚠️</span>
                                <span>{error}</span>
                            </div>
                        )}

                        <button
                            onClick={handleRunAnalysis}
                            disabled={loading}
                            className={`w-full py-5 rounded-2xl font-black uppercase tracking-[0.15em] text-xs transition-all shadow-xl flex items-center justify-center gap-3 ${loading
                                ? "bg-gray-800 text-gray-500 cursor-not-allowed border border-gray-700"
                                : "bg-accent text-background hover:bg-accent/90 hover:shadow-[0_0_30px_rgba(45,212,191,0.4)] hover:-translate-y-1"
                                }`}
                        >
                            {loading ? "System Analyzing..." : "Launch Agent Debate"}
                        </button>

                        <div className="pt-4 border-t border-white/5">
                            <p className="text-[11px] text-gray-500 leading-relaxed font-medium">
                                Analysis aggregates institutional-grade real-time data from <strong className="text-white/70">Bloomberg BQL</strong>, <strong className="text-white/70">SEC Edgar</strong>, and <strong className="text-white/70">Alpha Vantage</strong>.
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
