"use client";

import { useState, useRef, useEffect } from "react";
import { useAuth } from "@clerk/nextjs";
import { api, Prediction } from "@/lib/api";

const stats = [
    { label: "Total Analyses", value: "1,284", icon: "🔍", color: "var(--accent-cyan)" },
    { label: "Success Rate", value: "78.4%", icon: "🎯", color: "var(--bull-green)" },
    { label: "Active Monitors", value: "12", icon: "🔔", color: "var(--quant-blue)" },
    { label: "Avg Confidence", value: "84%", icon: "📊", color: "var(--consensus-purple)" },
];

interface WSMessage {
    status: string;
    message: string;
    agent?: string;
}

export default function DashboardPage() {
    const { getToken } = useAuth();
    const [ticker, setTicker] = useState("");
    const [reportDate, setReportDate] = useState("");
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<Prediction | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [messages, setMessages] = useState<WSMessage[]>([]);

    const terminalEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        terminalEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        if (loading) {
            scrollToBottom();
        }
    }, [messages, loading]);

    const handleRunAnalysis = async () => {
        if (!ticker || !reportDate) {
            setError("Please provide both ticker and report date.");
            return;
        }

        setLoading(true);
        setError(null);
        setResult(null);
        setMessages([]);

        let ws: WebSocket | null = null;

        try {
            const token = await getToken();
            if (!token) throw new Error("Not authenticated");

            // 1. Start Analysis
            const { task_id } = await api.predictTicker(ticker, reportDate, token);

            // Setup WebSocket
            const wsUrl = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";
            ws = new WebSocket(`${wsUrl}/ws/task/${task_id}`);

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    setMessages((prev) => [...prev, data]);
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
        if (a === "bull") return "text-bull font-bold";
        if (a === "bear") return "text-bear font-bold";
        if (a === "quant") return "text-blue-400 font-bold";
        if (a === "consensus") return "text-purple-400 font-bold";
        return "text-accent font-bold";
    };

    return (
        <div className="space-y-12">
            <header>
                <h1 className="text-4xl font-extrabold tracking-tight mb-2 font-outfit">Dashboard Overview</h1>
                <p className="text-gray-400 font-medium">Welcome back. Here is what&apos;s happening with your monitored tickers.</p>
            </header>

            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {stats.map((stat) => (
                    <div key={stat.label} className="glass p-8 rounded-3xl border border-white/5 group hover:bg-white/[0.02] transition-all">
                        <div className="flex justify-between items-start mb-4">
                            <span className="text-3xl">{stat.icon}</span>
                            <div
                                className="w-2 h-2 rounded-full"
                                style={{ backgroundColor: stat.color, boxShadow: `0 0 10px ${stat.color}` }}
                            />
                        </div>
                        <p className="text-sm font-bold text-gray-500 uppercase tracking-widest mb-1">{stat.label}</p>
                        <p className="text-3xl font-black">{stat.value}</p>
                    </div>
                ))}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-12">
                <div className="lg:col-span-2 space-y-8">
                    <div className="flex items-center justify-between">
                        <h2 className="text-2xl font-bold font-outfit">
                            {loading ? "Agent Debate in Progress" : "Recent Predictions"}
                        </h2>
                        {!loading && <button className="text-sm font-bold text-accent hover:underline">View All</button>}
                    </div>

                    {loading ? (
                        <div className="glass p-8 rounded-3xl border border-accent/20 bg-black/60 shadow-2xl h-[400px] flex flex-col font-mono text-sm relative overflow-hidden">
                            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-accent to-transparent opacity-50 animate-pulse"></div>
                            <div className="flex items-center gap-3 mb-6 pb-4 border-b border-white/10">
                                <div className="flex gap-1.5">
                                    <div className="w-3 h-3 rounded-full bg-red-500"></div>
                                    <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
                                    <div className="w-3 h-3 rounded-full bg-green-500"></div>
                                </div>
                                <span className="text-gray-500 font-bold uppercase tracking-widest text-[10px]">Live Terminal</span>
                            </div>

                            <div className="flex-1 overflow-y-auto space-y-3 pr-4 custom-scrollbar">
                                {messages.length === 0 ? (
                                    <div className="text-gray-500 animate-pulse">Connecting to debate stream...</div>
                                ) : (
                                    messages.map((msg, idx) => (
                                        <div key={idx} className="flex gap-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
                                            <span className="text-gray-600 shrink-0">[{new Date().toLocaleTimeString()}]</span>
                                            {msg.agent ? (
                                                <span className={`${getAgentColor(msg.agent)} shrink-0 w-[80px]`}>{msg.agent.toUpperCase()}:</span>
                                            ) : (
                                                <span className="text-gray-500 shrink-0 w-[80px]">SYSTEM:</span>
                                            )}
                                            <span className="text-gray-300 whitespace-pre-wrap">{msg.message}</span>
                                        </div>
                                    ))
                                )}
                                <div ref={terminalEndRef} />
                            </div>
                        </div>
                    ) : result ? (
                        <div className="glass p-10 rounded-3xl border border-accent/20 bg-accent/[0.02] animate-in fade-in slide-in-from-bottom-4 duration-1000">
                            <div className="flex justify-between items-start mb-8">
                                <div>
                                    <h3 className="text-3xl font-black text-accent mb-1">{result.ticker}</h3>
                                    <p className="text-gray-400 font-bold">{result.company_name}</p>
                                </div>
                                <div className="text-right">
                                    <div className="text-[10px] font-bold uppercase tracking-widest text-gray-500 mb-1">Confidence</div>
                                    <div className="text-4xl font-black text-white">{(result.confidence * 100).toFixed(0)}%</div>
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-8 mb-8">
                                <div className="p-6 bg-bull/5 rounded-2xl border border-bull/10">
                                    <p className="text-[10px] font-bold text-bull uppercase tracking-[0.2em] mb-4">Bull Case</p>
                                    <ul className="space-y-3">
                                        {result.bull_factors?.map((f, i) => (
                                            <li key={i} className="text-sm text-gray-300 flex gap-2">
                                                <span className="text-bull">•</span> {f}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                                <div className="p-6 bg-bear/5 rounded-2xl border border-bear/10">
                                    <p className="text-[10px] font-bold text-bear uppercase tracking-[0.2em] mb-4">Bear Case</p>
                                    <ul className="space-y-3">
                                        {result.bear_factors?.map((f, i) => (
                                            <li key={i} className="text-sm text-gray-300 flex gap-2">
                                                <span className="text-bear">•</span> {f}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            </div>

                            <div className="p-6 glass rounded-2xl border border-white/5">
                                <p className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-3">Agent Debate Summary</p>
                                <p className="text-sm text-gray-300 leading-relaxed font-medium whitespace-pre-line">
                                    {result.reasoning_summary}
                                </p>
                            </div>
                        </div>
                    ) : (
                        <div className="glass rounded-3xl overflow-hidden border border-white/5">
                            <table className="w-full text-left">
                                <thead className="bg-white/5 border-b border-white/5">
                                    <tr className="text-[10px] font-bold uppercase tracking-widest text-gray-500">
                                        <th className="px-8 py-5">Ticker</th>
                                        <th className="px-8 py-5">Status</th>
                                        <th className="px-8 py-5">Direction</th>
                                        <th className="px-8 py-5 text-right">Confidence</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-white/5">
                                    {[
                                        { ticker: "AAPL", status: "Analyzed", dir: "BEAT", conf: 82, color: "var(--bull-green)" },
                                        { ticker: "GOOGL", status: "Analyzed", dir: "BEAT", conf: 87, color: "var(--bull-green)" },
                                        { ticker: "NFLX", status: "Needs Review", dir: "MISS", conf: 64, color: "var(--bear-red)" },
                                    ].map((row) => (
                                        <tr key={row.ticker} className="hover:bg-white/[0.01] transition-colors group">
                                            <td className="px-8 py-6 font-bold text-accent group-hover:pl-10 transition-all">{row.ticker}</td>
                                            <td className="px-8 py-6 text-sm text-gray-400 font-medium">{row.status}</td>
                                            <td className="px-8 py-6">
                                                <span
                                                    className="px-4 py-1.5 rounded-full text-[10px] font-black"
                                                    style={{ backgroundColor: `${row.color}15`, color: row.color, border: `1px solid ${row.color}30` }}
                                                >
                                                    {row.dir}
                                                </span>
                                            </td>
                                            <td className="px-8 py-6 text-right font-mono font-bold text-lg">{row.conf}%</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>

                {/* Quick Analysis Form */}
                <div className="space-y-8">
                    <h2 className="text-2xl font-bold font-outfit">Quick Analysis</h2>
                    <div className="glass p-10 rounded-3xl border border-white/5 space-y-8 shadow-2xl relative">
                        {loading && (
                            <div className="absolute inset-0 bg-black/50 backdrop-blur-sm rounded-3xl z-10 flex flex-col items-center justify-center border border-accent/20">
                                <div className="w-12 h-12 border-4 border-accent/20 border-t-accent rounded-full animate-spin mb-4"></div>
                                <p className="text-accent font-bold animate-pulse text-sm tracking-widest uppercase">Analyzing Data</p>
                            </div>
                        )}

                        <div className="space-y-3">
                            <label className="text-[10px] font-bold uppercase tracking-widest text-gray-500">Stock Ticker</label>
                            <input
                                type="text"
                                value={ticker}
                                onChange={(e) => setTicker(e.target.value)}
                                placeholder="e.g. NVDA"
                                className="w-full bg-black/40 border border-white/10 rounded-2xl px-5 py-4 focus:border-accent outline-none transition-all uppercase font-black text-lg"
                            />
                        </div>
                        <div className="space-y-3">
                            <label className="text-[10px] font-bold uppercase tracking-widest text-gray-500">Report Date</label>
                            <input
                                type="date"
                                value={reportDate}
                                onChange={(e) => setReportDate(e.target.value)}
                                className="w-full bg-black/40 border border-white/10 rounded-2xl px-5 py-4 focus:border-accent outline-none transition-all text-sm font-bold text-white relative [color-scheme:dark]"
                            />
                        </div>

                        {error && (
                            <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-xs text-red-500 font-bold">
                                ⚠️ {error}
                            </div>
                        )}

                        <button
                            onClick={handleRunAnalysis}
                            disabled={loading}
                            className={`w-full py-5 rounded-2xl font-black uppercase tracking-widest text-sm transition-all shadow-xl ${loading
                                ? "bg-gray-800 text-gray-500 cursor-not-allowed"
                                : "bg-accent text-background hover:shadow-[0_0_30px_rgba(45,212,191,0.4)] hover:-translate-y-1"
                                }`}
                        >
                            {loading ? "Debate in Progress..." : "Run AI Debate"}
                        </button>

                        <p className="text-[10px] text-gray-600 text-center leading-relaxed">
                            Analysis involves real-time data fetching from Bloomberg, SEC Edgar, and Alpha Vantage.
                            Average completion time: 15-30s.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}
