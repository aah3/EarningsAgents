"use client";

import { useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { api, Prediction } from "@/lib/api";

const stats = [
    { label: "Total Analyses", value: "1,284", icon: "🔍", color: "var(--accent-cyan)" },
    { label: "Success Rate", value: "78.4%", icon: "🎯", color: "var(--bull-green)" },
    { label: "Active Monitors", value: "12", icon: "🔔", color: "var(--quant-blue)" },
    { label: "Avg Confidence", value: "84%", icon: "📊", color: "var(--consensus-purple)" },
];

export default function DashboardPage() {
    const { getToken } = useAuth();
    const [ticker, setTicker] = useState("");
    const [reportDate, setReportDate] = useState("");
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<Prediction | null>(null);
    const [error, setError] = useState<string | null>(null);

    const handleRunAnalysis = async () => {
        if (!ticker || !reportDate) {
            setError("Please provide both ticker and report date.");
            return;
        }

        setLoading(true);
        setError(null);
        setResult(null);

        try {
            const token = await getToken();
            if (!token) throw new Error("Not authenticated");

            const data = await api.predictTicker(ticker, reportDate, token);
            setResult(data);
        } catch (err: any) {
            setError(err.message || "An error occurred during analysis.");
        } finally {
            setLoading(false);
        }
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
                        <h2 className="text-2xl font-bold font-outfit">Recent Predictions</h2>
                        <button className="text-sm font-bold text-accent hover:underline">View All</button>
                    </div>

                    {result ? (
                        <div className="glass p-10 rounded-3xl border border-accent/20 bg-accent/[0.02] animate-in fade-in slide-in-from-bottom-4 duration-1000">
                            <div className="flex justify-between items-start mb-8">
                                <div>
                                    <h3 className="text-3xl font-black text-accent mb-1">{result.ticker}</h3>
                                    <p className="text-gray-400 font-bold">{result.company_name}</p>
                                </div>
                                <div className="text-right">
                                    <div className="text-[10px] font-bold uppercase tracking-widest text-gray-500 mb-1">Confidence</div>
                                    <div className="text-4xl font-black text-white">{result.confidence}%</div>
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
                                <p className="text-sm text-gray-300 leading-relaxed font-medium">
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
                    <div className="glass p-10 rounded-3xl border border-white/5 space-y-8 shadow-2xl">
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
                                className="w-full bg-black/40 border border-white/10 rounded-2xl px-5 py-4 focus:border-accent outline-none transition-all text-sm font-bold text-white"
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
                            {loading ? "Analyzing Market Data..." : "Run AI Debate"}
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
