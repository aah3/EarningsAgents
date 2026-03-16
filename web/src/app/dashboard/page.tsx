"use client";

import { useState, useRef, useEffect } from "react";
import { useAuth } from "@clerk/nextjs";
import { api, Prediction } from "@/lib/api";

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

    const [chatMessages, setChatMessages] = useState<{role: string, content: string}[]>([]);
    const [chatInput, setChatInput] = useState("");
    const [chatLoading, setChatLoading] = useState(false);
    const chatEndRef = useRef<HTMLDivElement>(null);

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
        if (chatMessages.length > 0) {
            chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
        }
    }, [chatMessages]);

    const handleRunAnalysis = async () => {
        if (!ticker || !reportDate) {
            setError("Please provide both ticker and report date.");
            return;
        }

        setLoading(true);
        setError(null);
        setResult(null);
        setMessages([]);
        setChatMessages([]);
        setChatInput("");

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

    const handleSendChatMessage = async () => {
        if (!chatInput.trim() || !result) return;
        
        const currentMessages = [...chatMessages];
        const newUserMsg = { role: "user", content: chatInput.trim() };
        
        setChatMessages([...currentMessages, newUserMsg]);
        setChatInput("");
        setChatLoading(true);
        
        try {
            const token = await getToken();
            if (!token) throw new Error("Not authenticated");
            
            // Send the entire context
            // prediction_id is not inherently present in the `result` from celery task if not returned, so we'll pass ticker
            const chatRes = await api.chatWithConsensus(result.ticker, [...currentMessages, newUserMsg], undefined, token);
            
            if (chatRes && chatRes.response) {
                setChatMessages([...currentMessages, newUserMsg, { role: "model", content: chatRes.response }]);
            } else {
                setChatMessages([...currentMessages, newUserMsg, { role: "model", content: "⚠️ No response received from Consensus Agent." }]);
            }
            
        } catch (err: any) {
             setChatMessages([...currentMessages, newUserMsg, { role: "model", content: "⚠️ Error contacting Consensus Agent: " + err.message }]);
        } finally {
            setChatLoading(false);
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
                            {loading ? "Agent Debate in Progress" : "Recent Predictions"}
                        </h2>
                        {!loading && <button className="text-xs font-bold text-accent hover:text-white uppercase tracking-widest transition-colors flex items-center gap-2">View History &rarr;</button>}
                    </div>

                    {loading ? (
                        <div className="flex-1 glass p-8 rounded-3xl border border-accent/30 bg-[#080b11] shadow-2xl flex flex-col font-mono text-sm relative overflow-hidden min-h-[400px]">
                            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-accent to-transparent opacity-50 animate-[pulse_2s_ease-in-out_infinite]"></div>
                            <div className="flex items-center gap-3 mb-6 pb-4 border-b border-white/10 shrink-0">
                                <div className="flex gap-2">
                                    <div className="w-3 h-3 rounded-full bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.5)]"></div>
                                    <div className="w-3 h-3 rounded-full bg-yellow-500 shadow-[0_0_10px_rgba(234,179,8,0.5)]"></div>
                                    <div className="w-3 h-3 rounded-full bg-green-500 shadow-[0_0_10px_rgba(34,197,94,0.5)]"></div>
                                </div>
                                <span className="text-gray-400 font-bold uppercase tracking-widest text-[10px]">Debate Connect / Live Stream</span>
                            </div>

                            <div className="flex-1 overflow-y-auto space-y-3 pr-4 custom-scrollbar text-[13px] leading-relaxed">
                                {messages.length === 0 ? (
                                    <div className="text-gray-500 animate-pulse font-medium">Establishing secure connection to debate server...</div>
                                ) : (
                                    messages.map((msg, idx) => (
                                        <div key={idx} className="flex gap-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
                                            <span className="text-gray-600 shrink-0 select-none">[{new Date().toLocaleTimeString(undefined, { hour12: false })}]</span>
                                            {msg.agent ? (
                                                <span className={`${getAgentColor(msg.agent)} shrink-0 w-[85px] uppercase tracking-wider`}>{msg.agent}:</span>
                                            ) : (
                                                <span className="text-gray-500 shrink-0 w-[85px] uppercase tracking-wider">SYSTEM:</span>
                                            )}
                                            <span className="text-gray-300 whitespace-pre-wrap">{msg.message}</span>
                                        </div>
                                    ))
                                )}
                                <div ref={terminalEndRef} />
                            </div>
                        </div>
                    ) : result ? (
                        <div className="flex-1 glass p-10 rounded-3xl border border-accent/20 bg-gradient-to-b from-[#0c1017] to-[#080b11] shadow-2xl animate-in fade-in slide-in-from-bottom-4 duration-700">
                            <div className="flex justify-between items-start mb-10 pb-6 border-b border-white/5">
                                <div>
                                    <div className="flex items-center gap-4 mb-2">
                                        <h3 className="text-4xl font-black text-white">{result.ticker}</h3>
                                        <span className={`px-4 py-1.5 rounded-full text-xs font-black uppercase tracking-widest
                                            ${result.direction === 'BEAT' ? 'bg-bull/10 text-bull border border-bull/30' :
                                                result.direction === 'MISS' ? 'bg-bear/10 text-bear border border-bear/30' :
                                                    'bg-gray-500/10 text-gray-400 border border-gray-500/30'}
                                        `}>
                                            {result.direction}
                                        </span>
                                    </div>
                                    <p className="text-gray-400 font-bold tracking-wide uppercase text-xs">{result.company_name}</p>
                                </div>
                                <div className="text-right">
                                    <div className="text-[10px] font-bold uppercase tracking-widest text-gray-500 mb-2">AI Confidence</div>
                                    <div className="text-5xl font-black text-transparent bg-clip-text bg-gradient-to-r from-white to-gray-500">
                                        {(result.confidence * 100).toFixed(0)}%
                                    </div>
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-8 mb-10">
                                <div className="p-6 bg-[#0a1a10] rounded-2xl border border-bull/20 shadow-inner">
                                    <div className="flex items-center gap-3 mb-5">
                                        <div className="w-8 h-8 rounded-full bg-bull/20 flex items-center justify-center border border-bull/30">
                                            <span className="text-bull font-black text-lg">↗</span>
                                        </div>
                                        <p className="text-xs font-black text-bull uppercase tracking-[0.2em]">Bull Case</p>
                                    </div>
                                    <ul className="space-y-4">
                                        {result.bull_factors?.map((f, i) => (
                                            <li key={i} className="text-sm text-gray-300 flex items-start gap-3 leading-relaxed">
                                                <span className="text-bull mt-1 font-bold">✓</span> {f}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                                <div className="p-6 bg-[#1a0a0a] rounded-2xl border border-bear/20 shadow-inner">
                                    <div className="flex items-center gap-3 mb-5">
                                        <div className="w-8 h-8 rounded-full bg-bear/20 flex items-center justify-center border border-bear/30">
                                            <span className="text-bear font-black text-lg">↘</span>
                                        </div>
                                        <p className="text-xs font-black text-bear uppercase tracking-[0.2em]">Bear Case</p>
                                    </div>
                                    <ul className="space-y-4">
                                        {result.bear_factors?.map((f, i) => (
                                            <li key={i} className="text-sm text-gray-300 flex items-start gap-3 leading-relaxed">
                                                <span className="text-bear mt-1 font-bold">×</span> {f}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            </div>

                            <div className="p-8 rounded-2xl border border-white/5 bg-black/40 relative overflow-hidden">
                                <div className="absolute top-0 left-0 w-1 h-full bg-consensus"></div>
                                <p className="text-xs font-black text-consensus uppercase tracking-[0.2em] mb-4 flex items-center gap-2">
                                    <span className="w-1.5 h-1.5 rounded-full bg-consensus animate-pulse"></span>
                                    Consensus Summary
                                </p>
                                <p className="text-[15px] text-gray-300 leading-relaxed font-medium whitespace-pre-line">
                                    {result.reasoning_summary}
                                </p>
                            </div>

                            {/* Interactive Consensus Chat */}
                            <div className="mt-8 p-6 rounded-2xl border border-white/5 bg-[#080b11] shadow-inner flex flex-col">
                                <h4 className="text-xs font-black text-consensus uppercase tracking-[0.2em] mb-4 flex items-center gap-2">
                                    <span className="text-lg">💬</span> Chat with Consensus Agent
                                </h4>
                                
                                <div className="max-h-[300px] overflow-y-auto mb-4 space-y-4 pr-2 custom-scrollbar">
                                    {chatMessages.length === 0 ? (
                                        <p className="text-sm text-gray-500 italic">Have questions about this prediction? Ask the Consensus Analyst directly.</p>
                                    ) : (
                                        chatMessages.map((msg, idx) => (
                                            <div key={idx} className={`p-4 rounded-xl text-sm ${msg.role === 'user' ? 'bg-white/5 text-gray-200 ml-4 border border-white/10' : 'bg-consensus/10 text-gray-300 mr-4 border border-consensus/30'}`}>
                                                <div className={`text-[10px] font-bold uppercase tracking-widest mb-2 ${msg.role === 'user' ? 'text-gray-400' : 'text-consensus'}`}>
                                                    {msg.role === 'user' ? 'You' : 'Consensus Analyst'}
                                                </div>
                                                <div className="whitespace-pre-wrap">{msg.content}</div>
                                            </div>
                                        ))
                                    )}
                                    {chatLoading && (
                                        <div className="p-4 rounded-xl bg-consensus/10 text-consensus mr-4 border border-consensus/30 flex items-center gap-3 w-fit">
                                            <span className="animate-pulse w-2 h-2 bg-consensus rounded-full"></span>
                                            <span className="animate-pulse text-xs font-bold uppercase tracking-widest">Thinking...</span>
                                        </div>
                                    )}
                                    <div ref={chatEndRef} />
                                </div>
                                
                                <div className="flex gap-3 relative">
                                    <input
                                        type="text"
                                        placeholder="E.g. What about the macroeconomic risks?"
                                        value={chatInput}
                                        onChange={(e) => setChatInput(e.target.value)}
                                        onKeyDown={(e) => e.key === 'Enter' && handleSendChatMessage()}
                                        className="flex-1 bg-black/50 border border-white/10 rounded-xl px-4 py-3 focus:border-consensus focus:ring-1 focus:ring-consensus/50 outline-none transition-all text-sm font-medium text-white placeholder-white/20"
                                        disabled={chatLoading}
                                    />
                                    <button
                                        onClick={handleSendChatMessage}
                                        disabled={chatLoading || !chatInput.trim()}
                                        className="px-6 rounded-xl font-bold uppercase tracking-widest text-xs transition-colors bg-consensus text-background hover:bg-consensus/90 disabled:opacity-50 disabled:cursor-not-allowed"
                                    >
                                        Send
                                    </button>
                                </div>
                            </div>
                        </div>
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
                                        {[
                                            { ticker: "AAPL", status: "Analyzed", dir: "BEAT", conf: 82, color: "var(--bull-green)" },
                                            { ticker: "GOOGL", status: "Analyzed", dir: "BEAT", conf: 87, color: "var(--bull-green)" },
                                            { ticker: "NFLX", status: "Review Suggested", dir: "MISS", conf: 64, color: "var(--bear-red)" },
                                            { ticker: "MSFT", status: "Analyzed", dir: "BEAT", conf: 91, color: "var(--bull-green)" },
                                            { ticker: "TSLA", status: "Analyzed", dir: "MEET", conf: 55, color: "var(--gray-500)" },
                                        ].map((row) => (
                                            <tr key={row.ticker} className="hover:bg-white/[0.02] transition-colors group cursor-pointer">
                                                <td className="px-8 py-6 font-black text-white group-hover:pl-10 group-hover:text-accent transition-all text-lg">{row.ticker}</td>
                                                <td className="px-8 py-6 text-sm text-gray-400 font-medium hidden sm:table-cell">{row.status}</td>
                                                <td className="px-8 py-6 text-center">
                                                    <span
                                                        className="px-5 py-1.5 rounded-full text-xs font-black"
                                                        style={{ backgroundColor: `${row.color}15`, color: row.color, border: `1px solid ${row.color}30` }}
                                                    >
                                                        {row.dir}
                                                    </span>
                                                </td>
                                                <td className="px-8 py-6 text-right font-mono font-bold text-xl tracking-tight text-white group-hover:text-accent transition-colors">{row.conf}%</td>
                                            </tr>
                                        ))}
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
