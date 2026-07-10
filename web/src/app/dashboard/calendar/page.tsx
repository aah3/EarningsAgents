"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@clerk/nextjs";
import { api } from "@/lib/api";
import { XCircle } from "lucide-react";

interface EarningsEvent {
    ticker: string;
    report_date: string;
    report_time: string;
    consensus_eps?: number;
    consensus_revenue?: number;
}

const SessionBadge = ({ timing }: { timing: string }) => {
  if (timing === "before_market_open" || timing === "BMO") {
    return (
      <span className="px-1.5 py-0.5 bg-human/10 text-human border border-human/20 rounded text-[9px] font-mono font-bold tracking-wider shadow-[0_0_10px_rgba(251,191,36,0.1)] inline-block ml-2 select-none">
        BMO
      </span>
    );
  }
  if (timing === "after_market_close" || timing === "AMC") {
    return (
      <span className="px-1.5 py-0.5 bg-quant/10 text-quant border border-quant/20 rounded text-[9px] font-mono font-bold tracking-wider shadow-[0_0_10px_rgba(96,165,250,0.1)] inline-block ml-2 select-none">
        AMC
      </span>
    );
  }
  return <span className="text-ink-dim/40 font-mono text-xs ml-2 select-none">—</span>;
};

export default function CalendarPage() {
    const { getToken } = useAuth();
    
    // Default to this week
    const getDatesForTimeframe = (tf: string) => {
        const today = new Date();
        let start = new Date();
        let end = new Date();

        if (tf === "Today") {
            start = today;
            end = today;
        } else if (tf === "Tomorrow") {
            const tomorrow = new Date();
            tomorrow.setDate(today.getDate() + 1);
            start = tomorrow;
            end = tomorrow;
        } else if (tf === "This Week") {
            const day = today.getDay();
            const diff = today.getDate() - day + (day === 0 ? -6 : 1);
            const monday = new Date(today.setDate(diff));
            start = monday;
            end = new Date(monday);
            end.setDate(monday.getDate() + 4);
        } else if (tf === "Next Week") {
            const day = today.getDay();
            const diff = today.getDate() - day + (day === 0 ? -6 : 1) + 7;
            const nextMonday = new Date(today.setDate(diff));
            start = nextMonday;
            end = new Date(nextMonday);
            end.setDate(nextMonday.getDate() + 4);
        } else if (tf === "This Month") {
            start = new Date(today.getFullYear(), today.getMonth(), 1);
            end = new Date(today.getFullYear(), today.getMonth() + 1, 0);
        }
        
        return {
            start: start.toISOString().split("T")[0],
            end: end.toISOString().split("T")[0]
        };
    };

    const initialDates = getDatesForTimeframe("This Week");

    const [startDate, setStartDate] = useState(initialDates.start);
    const [endDate, setEndDate] = useState(initialDates.end);
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
            setEvents(data || []);
        } catch (err: any) {
            setError(err.message || "Failed to fetch calendar.");
        } finally {
            setLoading(false);
        }
    };

    // Auto-fetch when filters/inputs change
    useEffect(() => {
        handleFetchCalendar();
    }, [useFinviz, indexName, timeframe, startDate, endDate, tickers]);

    const handleTimeframeChange = (tf: string) => {
        setTimeframe(tf);
        const { start, end } = getDatesForTimeframe(tf);
        setStartDate(start);
        setEndDate(end);
    };

    return (
        <div className="space-y-6 pb-20">
            <header className="flex justify-between items-end mb-[20px]">
                <div>
                    <h1 className="text-[clamp(1.9rem,3vw,2.3rem)] font-display font-semibold tracking-tight text-white mb-2 leading-none">
                        Earnings Calendar
                    </h1>
                    <p className="text-sm text-ink-mute font-body">Upcoming reports powered by data aggregators.</p>
                </div>
            </header>

            <div className="flex gap-1.5 p-1 bg-[var(--color-panel-sunk)] border border-panel-line rounded-[10px] select-none w-fit">
                <button
                    onClick={() => setUseFinviz(true)}
                    className={`px-3 py-1.5 rounded-md font-mono text-[11px] uppercase transition-all select-none cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-teal
                        ${useFinviz 
                            ? "bg-teal/14 text-teal border border-teal/20" 
                            : "text-ink-mute hover:text-white border border-transparent"}`}
                >
                    Discover (Finviz)
                </button>
                <button
                    onClick={() => setUseFinviz(false)}
                    className={`px-3 py-1.5 rounded-md font-mono text-[11px] uppercase transition-all select-none cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-teal
                        ${!useFinviz 
                            ? "bg-teal/14 text-teal border border-teal/20" 
                            : "text-ink-mute hover:text-white border border-transparent"}`}
                >
                    Search Watchlist (Yahoo)
                </button>
            </div>

            {useFinviz ? (
                <div className="bg-panel border border-[#26334A] rounded-[16px] p-6 shadow-[0_20px_60px_rgba(0,0,0,0.35)] flex flex-wrap lg:flex-nowrap gap-6 items-end">
                    <div className="w-full lg:w-1/3">
                        <label className="text-[10px] font-mono font-bold uppercase tracking-wider text-ink-dim mb-2 block select-none">Index</label>
                        <select
                            value={indexName}
                            onChange={(e) => setIndexName(e.target.value)}
                            className="w-full bg-[#05070a] border border-panel-line rounded-xl px-4 py-2.5 focus:border-teal focus:ring-2 focus:ring-teal/20 text-white uppercase font-semibold text-xs tracking-wider outline-none font-body transition-all"
                        >
                            <option value="S&P 500">S&P 500</option>
                            <option value="DJIA">Dow Jones (DJIA)</option>
                            <option value="NASDAQ 100">NASDAQ 100</option>
                            <option value="RUSSELL 2000">Russell 2000</option>
                            <option value="Any">Any</option>
                        </select>
                    </div>
                    <div className="w-full lg:w-1/3">
                        <label className="text-[10px] font-mono font-bold uppercase tracking-wider text-ink-dim mb-2 block select-none">Timeframe</label>
                        <select
                            value={timeframe}
                            onChange={(e) => handleTimeframeChange(e.target.value)}
                            className="w-full bg-[#05070a] border border-panel-line rounded-xl px-4 py-2.5 focus:border-teal focus:ring-2 focus:ring-teal/20 text-white uppercase font-semibold text-xs tracking-wider outline-none font-body transition-all"
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
                            className="w-full py-2.5 rounded-xl font-mono font-bold uppercase tracking-widest text-xs bg-gradient-to-br from-teal to-teal-deep text-[#04231F] hover:shadow-[0_0_15px_rgba(45,212,191,0.3)] transition-all cursor-pointer flex items-center justify-center gap-2"
                        >
                            {loading ? "Discovering..." : "Find Upcoming Catalysts"}
                        </button>
                    </div>
                </div>
            ) : (
                <div className="bg-panel border border-[#26334A] rounded-[16px] p-6 shadow-[0_20px_60px_rgba(0,0,0,0.35)] flex flex-wrap lg:flex-nowrap gap-6 items-end">
                    <div className="w-full lg:w-1/4">
                        <label className="text-[10px] font-mono font-bold uppercase tracking-wider text-ink-dim mb-2 block select-none">Start Date</label>
                        <input
                            type="date"
                            value={startDate}
                            onChange={(e) => setStartDate(e.target.value)}
                            className="w-full bg-[#05070a] border border-panel-line rounded-xl px-4 py-2.5 focus:border-teal focus:ring-2 focus:ring-teal/20 text-white relative [color-scheme:dark] outline-none text-xs font-mono transition-all"
                        />
                    </div>
                    <div className="w-full lg:w-1/4">
                        <label className="text-[10px] font-mono font-bold uppercase tracking-wider text-ink-dim mb-2 block select-none">End Date</label>
                        <input
                            type="date"
                            value={endDate}
                            onChange={(e) => setEndDate(e.target.value)}
                            className="w-full bg-[#05070a] border border-panel-line rounded-xl px-4 py-2.5 focus:border-teal focus:ring-2 focus:ring-teal/20 text-white relative [color-scheme:dark] outline-none text-xs font-mono transition-all"
                        />
                    </div>
                    <div className="w-full lg:flex-1">
                        <label className="text-[10px] font-mono font-bold uppercase tracking-wider text-ink-dim mb-2 block select-none">Tickers (Optional CSV)</label>
                        <input
                            type="text"
                            value={tickers}
                            onChange={(e) => setTickers(e.target.value)}
                            placeholder="E.G. AAPL, MSFT, GOOGL"
                            className="w-full bg-[#05070a] border border-panel-line rounded-xl px-4 py-2.5 focus:border-teal focus:ring-2 focus:ring-teal/20 text-white uppercase font-semibold text-xs tracking-wider outline-none font-body placeholder-white/20 transition-all"
                        />
                    </div>
                    <div>
                        <button
                            onClick={handleFetchCalendar}
                            disabled={loading}
                            className="px-8 py-2.5 rounded-xl font-mono font-bold uppercase tracking-widest text-xs bg-gradient-to-br from-teal to-teal-deep text-[#04231F] hover:shadow-[0_0_15px_rgba(45,212,191,0.3)] transition-all cursor-pointer flex items-center justify-center gap-2"
                        >
                            {loading ? "Searching..." : "Filter Watchlist"}
                        </button>
                    </div>
                </div>
            )}

            {error && (
                <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-xs text-red-500 font-bold select-none">
                    ⚠️ {error}
                </div>
            )}

            {loading && events.length === 0 ? (
                <div className="bg-panel border border-[#26334A] rounded-[16px] p-20 flex flex-col items-center gap-4 shadow-[0_20px_60px_rgba(0,0,0,0.35)] animate-pulse">
                    <div className="w-12 h-12 border-4 border-teal border-t-transparent rounded-full animate-spin" />
                    <p className="text-gray-500 font-bold uppercase tracking-widest text-xs">
                        Fetching calendar data...
                    </p>
                </div>
            ) : events.length > 0 ? (
                <div className="rounded-[16px] border border-[#26334A] bg-panel overflow-hidden flex flex-col shadow-[0_20px_60px_rgba(0,0,0,0.35)] animate-in fade-in duration-300">
                    <div className="overflow-x-auto">
                        <table className="w-full text-left whitespace-nowrap border-collapse">
                            <thead className="bg-[#05070a] border-b border-panel-line text-ink-dim select-none">
                                <tr>
                                    <th className="px-8 py-4 label-caps">Ticker</th>
                                    <th className="px-8 py-4 label-caps">Date</th>
                                    <th className="px-8 py-4 label-caps hidden sm:table-cell">Time</th>
                                    <th className="px-8 py-4 label-caps hidden sm:table-cell">EPS Est</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-white/5 font-body">
                                {events.map((ev, i) => (
                                    <tr key={i} className="hover:bg-white/[0.02] transition-colors group">
                                        <td className="px-8 py-4 font-display font-semibold text-white group-hover:text-teal transition-all text-base">
                                            {ev.ticker}
                                        </td>
                                        <td className="px-8 py-4 text-sm text-ink-mute font-data">
                                            {ev.report_date}
                                        </td>
                                        <td className="px-8 py-4 text-sm text-ink-mute hidden sm:table-cell">
                                            <SessionBadge timing={ev.report_time} />
                                        </td>
                                        <td className="px-8 py-4 text-sm text-white font-data hidden sm:table-cell">
                                            {ev.consensus_eps ? `$${ev.consensus_eps.toFixed(2)}` : <span className="text-ink-dim/40">—</span>}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            ) : (
                <div className="flex flex-col items-center justify-center py-16 text-center select-none bg-panel border border-[#26334A] rounded-[16px] shadow-[0_20px_60px_rgba(0,0,0,0.35)] animate-in fade-in duration-300">
                    <XCircle className="w-12 h-12 text-ink-dim mb-3" />
                    <p className="text-gray-500 font-bold uppercase tracking-widest text-xs mb-4">
                        DATA UNAVAILABLE: No upcoming earnings found
                    </p>
                </div>
            )}
        </div>
    );
}
