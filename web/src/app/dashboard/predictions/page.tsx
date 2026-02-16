"use client";

import { useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { api, Prediction } from "@/lib/api";

const upcoming = [
    { ticker: "NVDA", date: "2024-05-22", sector: "Technology", mkt_cap: "2.3T" },
    { ticker: "MSFT", date: "2024-04-25", sector: "Technology", mkt_cap: "3.1T" },
    { ticker: "AMZN", date: "2024-04-30", sector: "Consumer", mkt_cap: "1.8T" },
    { ticker: "META", date: "2024-04-24", sector: "Technology", mkt_cap: "1.2T" },
];

export default function PredictionsPage() {
    const { getToken } = useAuth();
    const [loading, setLoading] = useState<string | null>(null);

    const runAnalysis = async (ticker: string, date: string) => {
        setLoading(ticker);
        try {
            const token = await getToken();
            if (!token) throw new Error("Not authenticated");

            await api.predictTicker(ticker, date, token);
            // In a real app, we'd navigate or update local list
            alert(`Analysis for ${ticker} complete! Check History.`);
        } catch (err: any) {
            alert(err.message);
        } finally {
            setLoading(null);
        }
    };

    return (
        <div className="space-y-12">
            <header className="flex justify-between items-end">
                <div>
                    <h1 className="text-4xl font-extrabold tracking-tight mb-2 font-outfit">Upcoming Earnings</h1>
                    <p className="text-gray-400 font-medium">Analyze next week&apos;s most anticipated earnings reports.</p>
                </div>
                <div className="flex gap-4">
                    <button className="px-6 py-3 glass rounded-xl font-bold text-sm border-white/5 hover:bg-white/5 transition-all">Filter by Sector</button>
                    <button className="px-6 py-3 bg-accent text-background rounded-xl font-bold text-sm hover:shadow-[0_0_20px_rgba(45,212,191,0.3)] transition-all">Bulk Analysis</button>
                </div>
            </header>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {upcoming.map((stock) => (
                    <div key={stock.ticker} className="glass p-10 rounded-3xl border border-white/5 group hover:border-accent/40 transition-all shadow-xl">
                        <div className="flex justify-between items-start mb-8">
                            <div>
                                <h3 className="text-4xl font-black mb-1 group-hover:text-accent transition-colors">{stock.ticker}</h3>
                                <p className="text-sm font-bold text-gray-400 uppercase tracking-widest">{stock.sector}</p>
                            </div>
                            <div className="text-right">
                                <div className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-1">Report Date</div>
                                <div className="text-xl font-mono font-bold text-white">{stock.date}</div>
                            </div>
                        </div>

                        <div className="grid grid-cols-2 gap-4 mb-8">
                            <div className="p-4 bg-white/[0.02] rounded-2xl border border-white/5">
                                <p className="text-[10px] font-bold text-gray-600 uppercase tracking-widest mb-1">Market Cap</p>
                                <p className="font-bold">{stock.mkt_cap}</p>
                            </div>
                            <div className="p-4 bg-white/[0.02] rounded-2xl border border-white/5">
                                <p className="text-[10px] font-bold text-gray-600 uppercase tracking-widest mb-1">Volume</p>
                                <p className="font-bold">High</p>
                            </div>
                        </div>

                        <button
                            onClick={() => runAnalysis(stock.ticker, stock.date)}
                            disabled={loading === stock.ticker}
                            className={`w-full py-4 rounded-2xl font-black uppercase tracking-widest text-xs transition-all ${loading === stock.ticker
                                ? "bg-gray-800 text-gray-500"
                                : "bg-white/[0.03] text-white hover:bg-accent hover:text-background border border-white/10"
                                }`}
                        >
                            {loading === stock.ticker ? "Agent Debate in Progress..." : "Run AI Analysis"}
                        </button>
                    </div>
                ))}
            </div>
        </div>
    );
}
