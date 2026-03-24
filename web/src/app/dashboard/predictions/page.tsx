"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@clerk/nextjs";
import { api } from "@/lib/api";

export default function PredictionsPage() {
    const { getToken } = useAuth();
    const [loadingAnalysis, setLoadingAnalysis] = useState<string | null>(null);
    const [upcoming, setUpcoming] = useState<any[]>([]);
    const [loadingData, setLoadingData] = useState(true);

    useEffect(() => {
        const fetchUpcoming = async () => {
            try {
                setLoadingData(true);
                const token = await getToken();
                const data = await api.getCalendar(undefined, undefined, undefined, true, "Next Week", "S&P 500", token ?? undefined);
                setUpcoming(data || []);
            } catch (err) {
                console.error("Failed to load upcoming earnings", err);
            } finally {
                setLoadingData(false);
            }
        };

        fetchUpcoming();
    }, [getToken]);

    const runAnalysis = async (ticker: string, date: string) => {
        setLoadingAnalysis(ticker);
        try {
            const token = await getToken();
            if (!token) throw new Error("Not authenticated");

            await api.predictTicker(ticker, date, token);
            // In a real app, we'd navigate or update local list
            alert(`Analysis for ${ticker} complete! Check History.`);
        } catch (err: any) {
            alert(err.message);
        } finally {
            setLoadingAnalysis(null);
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
                {loadingData ? (
                    <div className="col-span-1 md:col-span-2 text-center py-20 text-accent animate-pulse font-bold tracking-widest uppercase text-sm">
                        Discovering Upcoming Earnings...
                    </div>
                ) : upcoming.length === 0 ? (
                    <div className="col-span-1 md:col-span-2 text-center py-20 text-gray-500 font-bold tracking-widest uppercase text-sm">
                        No upcoming earnings found for next week.
                    </div>
                ) : upcoming.map((stock, i) => (
                    <div key={`${stock.ticker}-${i}`} className="glass p-10 rounded-3xl border border-white/5 group hover:border-accent/40 transition-all shadow-xl">
                        <div className="flex justify-between items-start mb-8">
                            <div>
                                <h3 className="text-4xl font-black mb-1 group-hover:text-accent transition-colors">{stock.ticker}</h3>
                                <p className="text-sm font-bold text-gray-400 uppercase tracking-widest">{stock.sector || stock.industry || 'Unknown Sector'}</p>
                            </div>
                            <div className="text-right">
                                <div className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-1">Report Date</div>
                                <div className="text-lg font-mono font-bold text-white whitespace-pre-wrap">{stock.date_range || stock.report_date}</div>
                            </div>
                        </div>

                        <div className="grid grid-cols-2 gap-4 mb-8">
                            <div className="p-4 bg-white/[0.02] rounded-2xl border border-white/5">
                                <p className="text-[10px] font-bold text-gray-600 uppercase tracking-widest mb-1">Market Cap</p>
                                <p className="font-bold text-white">{stock.market_cap || "N/A"}</p>
                            </div>
                            <div className="p-4 bg-white/[0.02] rounded-2xl border border-white/5">
                                <p className="text-[10px] font-bold text-gray-600 uppercase tracking-widest mb-1">Volume</p>
                                <p className="font-bold text-white">{stock.volume || "N/A"}</p>
                            </div>
                        </div>

                        <button
                            onClick={() => runAnalysis(stock.ticker, stock.report_date)}
                            disabled={loadingAnalysis === stock.ticker}
                            className={`w-full py-4 rounded-2xl font-black uppercase tracking-widest text-xs transition-all ${loadingAnalysis === stock.ticker
                                ? "bg-gray-800 text-gray-500"
                                : "bg-white/[0.03] text-white hover:bg-accent hover:text-background border border-white/10"
                                }`}
                        >
                            {loadingAnalysis === stock.ticker ? "Agent Debate in Progress..." : "Run AI Analysis"}
                        </button>
                    </div>
                ))}
            </div>
        </div>
    );
}
