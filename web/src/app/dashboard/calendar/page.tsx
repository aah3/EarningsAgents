"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@clerk/nextjs";
import { api } from "@/lib/api";

interface EarningsEvent {
    ticker: string;
    report_date: string;
    report_time: string;
    consensus_eps?: number;
    consensus_revenue?: number;
}

export default function CalendarPage() {
    const { getToken } = useAuth();
    
    // Default to this week
    const getNextMonday = () => {
        const d = new Date();
        const diff = d.getDate() - d.getDay() + (d.getDay() === 0 ? -6 : 1); 
        return new Date(d.setDate(diff));
    };
    
    const getFriday = (monday: Date) => {
        const d = new Date(monday);
        d.setDate(d.getDate() + 4);
        return d;
    };

    const initialStart = getNextMonday().toISOString().split('T')[0];
    const initialEnd = getFriday(getNextMonday()).toISOString().split('T')[0];

    const [startDate, setStartDate] = useState(initialStart);
    const [endDate, setEndDate] = useState(initialEnd);
    const [tickers, setTickers] = useState("");
    
    // Finviz states
    const [useFinviz, setUseFinviz] = useState(true);
    const [timeframe, setTimeframe] = useState("This Week");
    const [indexName, setIndexName] = useState("S&P 500");
    
    const [loading, setLoading] = useState(false);
    const [events, setEvents] = useState<EarningsEvent[]>([]);
    const [error, setError] = useState<string | null>(null);

    const handleFetchCalendar = async () => {
        setLoading(true);
        setError(null);
        try {
            const token = await getToken();
            const tokenStr = token ?? undefined;
            const data = await api.getCalendar(startDate, endDate, tickers, useFinviz, timeframe, indexName, tokenStr);
            setEvents(data);
        } catch (err: any) {
            setError(err.message || "Failed to fetch calendar.");
        } finally {
            setLoading(false);
        }
    };

    // Load initial on mount
    useEffect(() => {
        handleFetchCalendar();
    }, []);

    return (
        <div className="space-y-10 pb-20">
            <header className="mb-10">
                <h1 className="text-4xl lg:text-5xl font-extrabold tracking-tight mb-3 font-outfit text-white">Earnings Calendar</h1>
                <p className="text-gray-400 font-medium text-lg">Upcoming reports powered by data aggregators.</p>
            </header>

            <div className="flex items-center gap-4 mb-4">
                <button
                    onClick={() => setUseFinviz(true)}
                    className={`px-4 py-2 text-xs font-bold uppercase tracking-widest rounded-lg transition-colors border ${useFinviz ? "bg-accent text-background border-accent shadow-[0_0_15px_rgba(45,212,191,0.3)]" : "bg-[#080b11] text-gray-400 border-white/10 hover:text-white hover:border-white/20"}`}
                >
                    Discover (Finviz)
                </button>
                <button
                    onClick={() => setUseFinviz(false)}
                    className={`px-4 py-2 text-xs font-bold uppercase tracking-widest rounded-lg transition-colors border ${!useFinviz ? "bg-accent text-background border-accent shadow-[0_0_15px_rgba(45,212,191,0.3)]" : "bg-[#080b11] text-gray-400 border-white/10 hover:text-white hover:border-white/20"}`}
                >
                    Search Watchlist (Yahoo)
                </button>
            </div>

            {useFinviz ? (
                <div className="flex flex-wrap lg:flex-nowrap gap-6 items-end glass p-8 rounded-3xl border border-white/10 bg-[#0c1017] shadow-xl">
                    <div className="w-full lg:w-1/3">
                        <label className="text-[10px] font-bold uppercase tracking-[0.15em] text-gray-400 mb-2 block">Index</label>
                        <select
                            value={indexName}
                            onChange={(e) => setIndexName(e.target.value)}
                            className="w-full bg-[#080b11] border border-white/10 rounded-2xl px-5 py-3 focus:border-accent text-white uppercase font-black tracking-wider outline-none"
                        >
                            <option value="S&P 500">S&P 500</option>
                            <option value="DJIA">Dow Jones (DJIA)</option>
                            <option value="NDX">NASDAQ 100</option>
                            <option value="">Any</option>
                        </select>
                    </div>
                    <div className="w-full lg:w-1/3">
                        <label className="text-[10px] font-bold uppercase tracking-[0.15em] text-gray-400 mb-2 block">Timeframe</label>
                        <select
                            value={timeframe}
                            onChange={(e) => setTimeframe(e.target.value)}
                            className="w-full bg-[#080b11] border border-white/10 rounded-2xl px-5 py-3 focus:border-accent text-white uppercase font-black tracking-wider outline-none"
                        >
                            <option value="Today">Today</option>
                            <option value="Tomorrow">Tomorrow</option>
                            <option value="This Week">This Week</option>
                            <option value="Next Week">Next Week</option>
                            <option value="This Month">This Month</option>
                        </select>
                    </div>
                    <div className="w-full lg:flex-1">
                        <button
                            onClick={handleFetchCalendar}
                            disabled={loading}
                            className="w-full py-4 rounded-2xl font-black uppercase tracking-[0.15em] text-xs shadow-xl flex items-center justify-center gap-2 bg-accent text-background hover:bg-accent/90"
                        >
                            {loading ? "Discovering..." : "Find Upcoming Catalysts"}
                        </button>
                    </div>
                </div>
            ) : (
                <div className="flex flex-wrap lg:flex-nowrap gap-6 items-end glass p-8 rounded-3xl border border-white/10 bg-[#0c1017] shadow-xl">
                    <div className="w-full lg:w-1/4">
                        <label className="text-[10px] font-bold uppercase tracking-[0.15em] text-gray-400 mb-2 block">Start Date</label>
                        <input
                            type="date"
                            value={startDate}
                            onChange={(e) => setStartDate(e.target.value)}
                            className="w-full bg-[#080b11] border border-white/10 rounded-2xl px-5 py-3 focus:border-accent text-white relative [color-scheme:dark]"
                        />
                    </div>
                    <div className="w-full lg:w-1/4">
                        <label className="text-[10px] font-bold uppercase tracking-[0.15em] text-gray-400 mb-2 block">End Date</label>
                        <input
                            type="date"
                            value={endDate}
                            onChange={(e) => setEndDate(e.target.value)}
                            className="w-full bg-[#080b11] border border-white/10 rounded-2xl px-5 py-3 focus:border-accent text-white relative [color-scheme:dark]"
                        />
                    </div>
                    <div className="w-full lg:flex-1">
                        <label className="text-[10px] font-bold uppercase tracking-[0.15em] text-gray-400 mb-2 block">Tickers (Optional CSV)</label>
                        <input
                            type="text"
                            value={tickers}
                            onChange={(e) => setTickers(e.target.value)}
                            placeholder="E.G. AAPL, MSFT, GOOGL"
                            className="w-full bg-[#080b11] border border-white/10 rounded-2xl px-5 py-3 focus:border-accent text-white uppercase font-black tracking-wider outline-none"
                        />
                    </div>
                    <div>
                        <button
                            onClick={handleFetchCalendar}
                            disabled={loading}
                            className="px-8 py-4 rounded-2xl font-black uppercase tracking-[0.15em] text-xs shadow-xl flex items-center justify-center gap-2 bg-accent text-background hover:bg-accent/90"
                        >
                            {loading ? "Searching..." : "Filter Watchlist"}
                        </button>
                    </div>
                </div>
            )}

            {error && (
                <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-xs text-red-500 font-bold">
                    ⚠️ {error}
                </div>
            )}

            <div className="glass rounded-3xl overflow-hidden border border-white/5 bg-[#0c1017]">
                <table className="w-full text-left">
                    <thead className="bg-[#080b11] border-b border-white/10">
                        <tr className="text-[10px] font-bold uppercase tracking-[0.15em] text-gray-400">
                            <th className="px-8 py-6">Ticker</th>
                            <th className="px-8 py-6">Date</th>
                            <th className="px-8 py-6 hidden sm:table-cell">Time</th>
                            <th className="px-8 py-6 hidden sm:table-cell">EPS Est</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                        {loading && events.length === 0 ? (
                            <tr>
                                <td colSpan={4} className="px-8 py-10 text-center text-accent animate-pulse font-bold tracking-widest uppercase text-xs">
                                    Fetching calendar data...
                                </td>
                            </tr>
                        ) : events.length > 0 ? (
                            events.map((ev, i) => (
                                <tr key={i} className="hover:bg-white/[0.02] transition-colors group">
                                    <td className="px-8 py-5 font-black text-white group-hover:pl-10 group-hover:text-accent transition-all text-lg">{ev.ticker}</td>
                                    <td className="px-8 py-5 text-gray-300 font-medium">{ev.report_date}</td>
                                    <td className="px-8 py-5 text-gray-400 text-sm hidden sm:table-cell">
                                        {ev.report_time === "before_market_open" ? "Pre-Market" :
                                         ev.report_time === "after_market_close" ? "After Hours" :
                                         "Unknown"}
                                    </td>
                                    <td className="px-8 py-5 text-gray-400 font-mono hidden sm:table-cell">{ev.consensus_eps ? "$" + ev.consensus_eps?.toFixed(2) : "N/A"}</td>
                                </tr>
                            ))
                        ) : (
                            <tr>
                                <td colSpan={4} className="px-8 py-10 text-center text-gray-500 font-bold tracking-widest uppercase text-xs">
                                    No events found for this filter.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
