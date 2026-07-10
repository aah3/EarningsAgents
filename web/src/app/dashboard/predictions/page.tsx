"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@clerk/nextjs";
import { api } from "@/lib/api";
import { XCircle } from "lucide-react";

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
        <div className="space-y-6">
            <header className="flex justify-between items-end mb-[20px]">
                <div>
                    <h1 className="text-[clamp(1.9rem,3vw,2.3rem)] font-display font-semibold tracking-tight text-white mb-2 leading-none">
                        Upcoming Earnings
                    </h1>
                    <p className="text-sm text-ink-mute font-body">Analyze next week&apos;s most anticipated earnings reports.</p>
                </div>
                <div className="flex gap-4">
                    <button className="px-4 py-2 rounded-lg text-xs font-mono font-bold text-teal hover:bg-teal/10 border border-teal/20 transition-all uppercase tracking-widest cursor-pointer">
                        Filter by Sector
                    </button>
                    <button className="px-4 py-2 rounded-lg text-xs font-mono font-bold bg-gradient-to-br from-teal to-teal-deep text-[#04231F] hover:shadow-[0_0_15px_rgba(45,212,191,0.3)] transition-all uppercase tracking-widest cursor-pointer">
                        Bulk Analysis
                    </button>
                </div>
            </header>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {loadingData ? (
                    <div className="col-span-1 md:col-span-2 bg-panel border border-[#26334A] rounded-[16px] p-20 flex flex-col items-center gap-4 shadow-[0_20px_60px_rgba(0,0,0,0.35)] animate-pulse">
                        <div className="w-12 h-12 border-4 border-teal border-t-transparent rounded-full animate-spin" />
                        <p className="text-gray-500 font-bold uppercase tracking-widest text-xs">
                            Discovering Upcoming Earnings...
                        </p>
                    </div>
                ) : upcoming.length === 0 ? (
                    <div className="col-span-1 md:col-span-2 flex flex-col items-center justify-center py-20 text-center select-none bg-panel border border-[#26334A] rounded-[16px] shadow-[0_20px_60px_rgba(0,0,0,0.35)]">
                        <XCircle className="w-12 h-12 text-ink-dim mb-3" />
                        <p className="text-gray-500 font-bold uppercase tracking-widest text-xs">
                            DATA UNAVAILABLE: No upcoming earnings found for next week
                        </p>
                    </div>
                ) : upcoming.map((stock, i) => (
                    <div key={`${stock.ticker}-${i}`} className="bg-panel border border-[#26334A] p-6 rounded-2xl group hover:border-teal/40 transition-all hover:bg-white/[0.01] shadow-[0_20px_60px_rgba(0,0,0,0.25)] flex flex-col justify-between">
                        <div>
                            <div className="flex justify-between items-start mb-6">
                                <div>
                                    <h3 className="text-2xl font-display font-semibold text-white group-hover:text-teal transition-colors mb-1">{stock.ticker}</h3>
                                    <p className="text-[10px] font-bold text-ink-mute uppercase tracking-widest label-caps select-none">{stock.sector || stock.industry || 'Unknown Sector'}</p>
                                </div>
                                <div className="text-right">
                                    <div className="text-[10px] font-bold text-ink-dim uppercase tracking-widest label-caps mb-1 select-none">Report Date</div>
                                    <div className="text-sm font-data font-bold text-white whitespace-pre-wrap">{stock.date_range || stock.report_date}</div>
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-4 mb-6">
                                <div className="p-4 bg-[var(--color-panel-sunk)] rounded-xl border border-panel-line">
                                    <p className="text-[10px] font-bold text-ink-dim uppercase tracking-widest label-caps mb-1 select-none">Market Cap</p>
                                    <p className="font-semibold text-white font-data">{stock.market_cap || "N/A"}</p>
                                </div>
                                <div className="p-4 bg-[var(--color-panel-sunk)] rounded-xl border border-panel-line">
                                    <p className="text-[10px] font-bold text-ink-dim uppercase tracking-widest label-caps mb-1 select-none">Volume</p>
                                    <p className="font-semibold text-white font-data">{stock.volume || "N/A"}</p>
                                </div>
                            </div>
                        </div>

                        <button
                            onClick={() => runAnalysis(stock.ticker, stock.report_date)}
                            disabled={loadingAnalysis === stock.ticker}
                            className={`w-full py-3 rounded-xl font-mono font-bold uppercase tracking-widest text-xs transition-all ${loadingAnalysis === stock.ticker
                                ? "bg-white/5 border border-white/10 text-gray-500 cursor-not-allowed"
                                : "bg-teal/5 hover:bg-teal hover:text-black border border-teal/20 hover:border-teal text-teal cursor-pointer"
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
