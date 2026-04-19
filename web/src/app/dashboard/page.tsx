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
            setMessages([]); // Clear toasts after completion
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
        <div className="space-y-8 pb-20">
            <header className="flex justify-between items-end mb-6">
                <div>
                    <h1 className="text-4xl lg:text-5xl font-extrabold tracking-tight mb-2 font-outfit text-white">Dashboard Overview</h1>
                    <p className="text-gray-400 font-medium text-lg">Your intelligent hub for AI-driven earnings forecasts.</p>
                </div>
            </header>

            {/* AI Analysis Hub (Centralized Core Feature) */}
            <div className="glass p-8 lg:p-10 rounded-3xl border border-white/10 bg-[#0c1017] mb-8 shadow-2xl relative overflow-hidden group">
                <div className="absolute top-0 inset-x-0 h-1.5 bg-gradient-to-r from-transparent via-accent to-transparent opacity-50 group-hover:opacity-100 transition-opacity"></div>

                {loading && (
                    <div className="absolute inset-0 bg-black/60 backdrop-blur-md z-20 flex flex-col items-center justify-center border border-accent/20">
                        <div className="relative w-20 h-20 mb-6">
                            <div className="absolute inset-0 rounded-full border-4 border-white/10"></div>
                            <div className="absolute inset-0 rounded-full border-4 border-transparent border-t-accent animate-spin"></div>
                            <div className="absolute inset-0 flex items-center justify-center text-accent text-2xl">
                                <span className="animate-pulse">⚡</span>
                            </div>
                        </div>
                        <p className="text-accent font-black animate-pulse text-sm tracking-[0.3em] uppercase">Initializing Agent Debate Pipeline</p>
                    </div>
                )}

                <div className="flex justify-between items-center mb-8">
                    <h2 className="text-2xl font-black font-outfit text-white tracking-wide uppercase flex items-center gap-3">
                        <span className="text-accent text-3xl">🎯</span> AI Analysis Hub
                    </h2>
                    <div className="text-[11px] text-gray-500 font-bold uppercase tracking-widest bg-white/5 px-4 py-2 rounded-lg">
                        Aggregating BQL / EDGAR / Alpha Vantage
                    </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 w-full">
                    {/* Giant Ticker Input */}
                    <div className="lg:col-span-4 space-y-3">
                        <label className="text-[11px] font-black uppercase tracking-[0.2em] text-accent">Target Stock Ticker</label>
                        <input
                            type="text"
                            value={ticker}
                            onChange={(e) => setTicker(e.target.value)}
                            placeholder="E.G. NVDA"
                            className="w-full bg-[#05070a] border-2 border-white/10 rounded-2xl px-6 py-5 focus:border-accent focus:ring-4 focus:ring-accent/20 outline-none transition-all uppercase font-black text-4xl lg:text-5xl tracking-widest text-white placeholder-white/10 h-[90px] shadow-inner"
                            suppressHydrationWarning
                        />
                    </div>

                    {/* Date Input */}
                    <div className="lg:col-span-3 space-y-3">
                        <label className="text-[11px] font-bold uppercase tracking-[0.2em] text-gray-400">Report Date</label>
                        <input
                            type="date"
                            value={reportDate}
                            onChange={(e) => setReportDate(e.target.value)}
                            className="w-full bg-[#05070a] border border-white/10 rounded-2xl px-6 py-5 focus:border-accent focus:ring-2 focus:ring-accent/20 outline-none transition-all text-xl font-bold text-white relative [color-scheme:dark] h-[90px]"
                            suppressHydrationWarning
                        />
                    </div>

                    {/* Submit Button */}
                    <div className="lg:col-span-5 flex flex-col justify-end space-y-3">
                        <div className="flex justify-between items-center opacity-0"><label>Spacer</label></div>
                        <button
                            onClick={handleRunAnalysis}
                            disabled={loading || !ticker || !reportDate}
                            className={`w-full h-[90px] rounded-2xl font-black uppercase tracking-[0.2em] text-lg lg:text-xl transition-all shadow-xl flex items-center justify-center gap-4 ${loading || !ticker || !reportDate
                                ? "bg-gray-800 text-gray-500 cursor-not-allowed border-2 border-gray-700"
                                : "bg-accent text-background hover:bg-white hover:text-black border-2 border-accent hover:border-white shadow-[0_0_40px_rgba(45,212,191,0.3)] hover:shadow-[0_0_50px_rgba(255,255,255,0.5)] transform hover:-translate-y-1"
                                }`}
                        >
                            {loading ? "Analyzing..." : "Launch Agent Debate 🚀"}
                        </button>
                    </div>
                </div>

                <div className="mt-6 space-y-3">
                    <div className="flex justify-between items-center pr-2">
                        <label className="text-[10px] font-bold uppercase tracking-[0.15em] text-gray-500">Your Custom Analysis context (Optional)</label>
                        <span className="text-[9px] text-accent font-bold uppercase tracking-widest bg-accent/10 px-3 py-1.5 rounded-md border border-accent/20">Analyst Agent Input</span>
                    </div>
                    <textarea
                        value={userAnalysis}
                        onChange={(e) => setUserAnalysis(e.target.value)}
                        placeholder="Include your prompt/analysis to be incorporated into the consensus."
                        className="w-full bg-[#05070a] border border-white/10 rounded-xl px-5 py-4 focus:border-accent focus:ring-1 focus:ring-accent/50 outline-none transition-all text-sm font-medium text-white relative placeholder-white/20 min-h-[80px] resize-y custom-scrollbar"
                    />
                </div>

                {error && (
                    <div className="mt-4 p-4 bg-red-500/10 border border-red-500/30 rounded-xl text-sm text-red-400 font-bold flex items-start gap-3">
                        <span className="text-xl">⚠️</span>
                        <span className="pt-0.5">{error}</span>
                    </div>
                )}
            </div>

            {/* Dense Stats Summary */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                {stats.map((stat) => (
                    <div key={stat.label} className="p-5 rounded-2xl border border-white/10 bg-[#0c1017] flex items-center gap-4 hover:bg-[#11161d] transition-colors">
                        <div className="text-3xl opacity-80">{stat.icon}</div>
                        <div>
                            <p className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">{stat.label}</p>
                            <div className="flex items-baseline gap-2">
                                <p className="text-2xl font-black text-white tracking-tight">{stat.value}</p>
                                <p className="text-[10px] font-bold" style={{ color: stat.color }}>{stat.subtext.split(' ')[0]}</p>
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {/* Main Content Area (Full Width) */}
            <div className="min-h-[600px] flex flex-col">
                <div className="flex items-center justify-between mb-4 border-b border-white/10 pb-4">
                    <h2 className="text-xl font-bold font-outfit text-white uppercase tracking-widest">
                        {loading ? "Live Agent Debate" : result ? "Comprehensive Analysis Results" : "Recent Institutional Predictions"}
                    </h2>
                    {!loading && (
                        result ? (
                            <button onClick={() => setResult(null)} className="text-[11px] px-4 py-2 bg-white/5 rounded-lg font-bold text-white hover:bg-white/10 uppercase tracking-widest transition-colors flex items-center gap-2">&larr; Back to Dashboard Grid</button>
                        ) : (
                            <a href="/dashboard/history" className="text-[11px] px-4 py-2 bg-white/5 rounded-lg font-bold text-accent hover:bg-accent hover:text-black uppercase tracking-widest transition-colors flex items-center gap-2">View Full Ledger &rarr;</a>
                        )
                    )}
                </div>

                {loading ? (
                    <div className="flex-1 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6 auto-rows-fr min-h-[500px]">
                        {['Bull', 'Bear', 'Quant', 'Consensus'].map((agentName) => (
                            <div key={agentName} className="glass p-6 rounded-2xl border border-white/10 bg-[#0c1017] shadow-xl flex flex-col font-mono text-xs relative overflow-hidden h-full">
                                <div className="absolute top-0 left-0 w-full h-1" style={{ backgroundColor: getAgentColor(agentName).includes('bull') ? '#2dd4bf' : getAgentColor(agentName).includes('bear') ? '#f87171' : getAgentColor(agentName).includes('blue') ? '#60a5fa' : '#c084fc' }}></div>
                                <div className="flex items-center justify-between mb-5 pb-3 border-b border-white/10 shrink-0 mt-2">
                                    <span className={`font-black uppercase tracking-widest text-sm ${getAgentColor(agentName)} text-shadow-sm`}>{agentName} Node</span>
                                    {agentStreams[agentName as keyof typeof agentStreams] === "" ? (
                                        <span className="text-[10px] text-gray-500 uppercase flex items-center gap-2 font-bold tracking-widest">
                                            <div className="w-2 h-2 rounded-full bg-gray-600 animate-pulse"></div> Awaiting
                                        </span>
                                    ) : (
                                        <span className="text-[10px] text-accent uppercase flex items-center gap-2 font-bold tracking-widest">
                                            <div className="w-2 h-2 rounded-full bg-accent animate-ping"></div> Generating
                                        </span>
                                    )}
                                </div>
                                <div className="flex-1 overflow-y-auto pr-4 custom-scrollbar text-gray-300 leading-relaxed font-outfit text-[13px] flex flex-col justify-end">
                                    <span ref={terminalEndRef} className="whitespace-pre-wrap mt-auto">
                                        {agentStreams[agentName as keyof typeof agentStreams] || "Standard output connection established. Listening for real-time analysis tokens..."}
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>
                ) : result ? (
                    <div className="bg-[#0c1017] p-1 rounded-3xl border border-white/10">
                        <AnalysisResult result={result} />
                    </div>
                ) : (
                    <div className="flex-1 glass rounded-2xl overflow-hidden border border-white/10 bg-[#080b11]">
                        <div className="overflow-x-auto">
                            <table className="w-full text-left whitespace-nowrap">
                                <thead className="bg-[#05070a] border-b border-white/10">
                                    <tr className="text-[11px] font-black uppercase tracking-[0.2em] text-gray-500">
                                        <th className="px-8 py-5 text-accent">Ticker</th>
                                        <th className="px-8 py-5 hidden sm:table-cell">Target Date</th>
                                        <th className="px-8 py-5">Status</th>
                                        <th className="px-8 py-5 text-center">Consensus</th>
                                        <th className="px-8 py-5 text-right">Confidence Score</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-white/5">
                                    {history.length > 0 ? history.map((row) => (
                                        <tr key={row.ticker + row.prediction_date} onClick={() => setResult(row)} className="hover:bg-white/[0.04] transition-all group cursor-pointer h-[70px]">
                                            <td className="px-8 py-4 font-black text-white group-hover:pl-10 group-hover:text-accent transition-all text-xl">{row.ticker}</td>
                                            <td className="px-8 py-4 text-sm text-gray-400 font-medium hidden sm:table-cell">{new Date(row.prediction_date).toLocaleDateString()}</td>
                                            <td className="px-8 py-4">
                                                <span className="flex items-center gap-2 text-xs font-bold text-gray-400 uppercase tracking-widest">
                                                    <span className="w-1.5 h-1.5 rounded-full bg-green-500"></span> Validated
                                                </span>
                                            </td>
                                            <td className="px-8 py-4 text-center">
                                                <span
                                                    className={`px-6 py-2 rounded-lg text-xs font-black uppercase tracking-widest inline-block min-w-[100px]
                                                        ${row.direction === 'BEAT' ? 'bg-bull/20 text-bull border-bull/50 border shadow-[0_0_15px_rgba(45,212,191,0.2)]' :
                                                            row.direction === 'MISS' ? 'bg-bear/20 text-bear border-bear/50 border shadow-[0_0_15px_rgba(248,113,113,0.2)]' :
                                                                'bg-gray-800 text-gray-300 border-gray-600 border'}`}
                                                >
                                                    {row.direction}
                                                </span>
                                            </td>
                                            <td className="px-8 py-4 text-right">
                                                <div className="flex flex-col items-end">
                                                    <span className="font-mono font-black text-2xl tracking-tight text-white group-hover:text-accent transition-colors">
                                                        {(row.confidence * 100).toFixed(0)}<span className="text-gray-500 text-lg">%</span>
                                                    </span>
                                                    <div className="w-24 h-1 bg-white/10 rounded-full mt-1 overflow-hidden">
                                                        <div className="h-full bg-accent" style={{ width: `${row.confidence * 100}%` }}></div>
                                                    </div>
                                                </div>
                                            </td>
                                        </tr>
                                    )) : (
                                        <tr>
                                            <td colSpan={5} className="px-8 py-16 text-center text-accent text-sm font-bold uppercase tracking-widest">
                                                <div className="flex flex-col items-center justify-center gap-3">
                                                    <span className="text-4xl text-white/20">📋</span>
                                                    <span>No recent predictions found in ledger.</span>
                                                </div>
                                            </td>
                                        </tr>
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}
            </div>

            {/* Toast Notifications for Status/Retries */}
            {messages.length > 0 && (
                <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-3 pointer-events-none max-w-sm w-full">
                    {messages.slice(-3).map((m, i) => (
                        <div key={i} className="glass bg-[#0c1017]/90 border border-accent/30 p-4 rounded-2xl shadow-[0_0_20px_rgba(45,212,191,0.15)] backdrop-blur-md animate-in slide-in-from-right fade-in duration-300">
                            <div className="flex items-center gap-3">
                                {m.message.includes("Error") || m.message.includes("Limit") ? (
                                    <span className="text-xl animate-pulse">⚠️</span>
                                ) : (
                                    <span className="text-xl text-accent animate-pulse">⚙️</span>
                                )}
                                <div>
                                    {m.agent && <p className="text-[10px] font-black uppercase tracking-widest text-gray-400">{m.agent} Note</p>}
                                    <p className="text-xs font-bold text-white leading-relaxed">{m.message}</p>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
