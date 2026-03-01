"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { api, Prediction } from "@/lib/api";

export default function HistoryPage() {
    const { getToken } = useAuth();
    const [history, setHistory] = useState<Prediction[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function loadHistory() {
            try {
                const token = await getToken();
                if (!token) throw new Error("Not authenticated");
                const data = await api.getPredictionHistory(token);
                setHistory(data);
            } catch (err: any) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        }
        loadHistory();
    }, [getToken]);

    return (
        <div className="space-y-12">
            <header>
                <h1 className="text-4xl font-extrabold tracking-tight mb-2 font-outfit">Analysis History</h1>
                <p className="text-gray-400 font-medium">Review and track the accuracy of your historical earnings predictions.</p>
            </header>

            {loading ? (
                <div className="glass p-20 rounded-3xl border border-white/5 flex flex-col items-center gap-4">
                    <div className="w-12 h-12 border-4 border-accent border-t-transparent rounded-full animate-spin" />
                    <p className="text-gray-500 font-bold uppercase tracking-widest text-xs">Fetching your history...</p>
                </div>
            ) : error ? (
                <div className="glass p-20 rounded-3xl border border-red-500/20 bg-red-500/5 text-center">
                    <p className="text-red-500 font-black mb-2">Error loading history</p>
                    <p className="text-gray-400 text-sm">{error}</p>
                </div>
            ) : history.length === 0 ? (
                <div className="glass p-20 rounded-3xl border border-white/5 text-center">
                    <p className="text-gray-500 font-black mb-2">No analyses yet</p>
                    <p className="text-gray-400 text-sm mb-8">Run your first analysis from the dashboard to see it here.</p>
                    <button className="px-8 py-4 bg-white/5 hover:bg-white/10 rounded-2xl font-bold text-sm transition-all border border-white/10">Compare Stocks</button>
                </div>
            ) : (
                <div className="glass rounded-3xl overflow-hidden border border-white/5 shadow-2xl">
                    <table className="w-full text-left">
                        <thead className="bg-white/5 border-b border-white/5">
                            <tr className="text-[10px] font-bold uppercase tracking-widest text-gray-500">
                                <th className="px-8 py-5">Ticker</th>
                                <th className="px-8 py-5">Analysis Date</th>
                                <th className="px-8 py-5">Prediction</th>
                                <th className="px-8 py-5">Confidence</th>
                                <th className="px-8 py-5 text-right">Actual Outcome</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                            {history.map((row) => (
                                <tr key={row.ticker + row.prediction_date} className="hover:bg-white/[0.01] transition-colors group cursor-pointer">
                                    <td className="px-8 py-6">
                                        <div className="font-black text-accent text-xl">{row.ticker}</div>
                                        <div className="text-[10px] text-gray-500 font-bold uppercase tracking-tighter">{row.company_name}</div>
                                    </td>
                                    <td className="px-8 py-6 text-sm text-gray-400 font-mono font-medium">
                                        {new Date(row.prediction_date).toLocaleDateString()}
                                    </td>
                                    <td className="px-8 py-6">
                                        <span
                                            className={`px-4 py-1.5 rounded-full text-[10px] font-black border ${row.direction === "BEAT"
                                                    ? "bg-bull/10 text-bull border-bull/20"
                                                    : "bg-bear/10 text-bear border-bear/20"
                                                }`}
                                        >
                                            {row.direction}
                                        </span>
                                    </td>
                                    <td className="px-8 py-6 font-mono font-bold text-lg text-white">{row.confidence}%</td>
                                    <td className="px-8 py-6 text-right">
                                        <span className="text-[10px] font-black uppercase tracking-widest text-gray-600">
                                            WAITING
                                        </span>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
