"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { api, Prediction } from "@/lib/api";
import AnalysisResult from "@/components/AnalysisResult";

function OutcomeCell({ 
    pred, 
    onVerify, 
    isVerifying 
}: { 
    pred: Prediction; 
    onVerify: (e: React.MouseEvent) => void; 
    isVerifying: boolean;
}) {
    if (!pred.actual_direction) {
        return (
            <div className="text-right">
                <button
                    onClick={onVerify}
                    disabled={isVerifying}
                    className={`px-3 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-widest transition-all duration-200 border ${
                        isVerifying 
                        ? "bg-white/5 border-white/10 text-gray-500 cursor-not-allowed" 
                        : "bg-accent/5 hover:bg-accent hover:text-black border-accent/20 hover:border-accent text-accent shadow-sm shadow-accent/5 hover:shadow-accent/20 cursor-pointer active:scale-95"
                    }`}
                >
                    {isVerifying ? (
                        <div className="flex items-center gap-1.5 justify-end">
                            <span className="w-2.5 h-2.5 border-2 border-gray-500 border-t-transparent rounded-full animate-spin" />
                            <span>Verifying...</span>
                        </div>
                    ) : (
                        "Verify Outcome"
                    )}
                </button>
            </div>
        );
    }

    const correct = pred.direction.toLowerCase() === pred.actual_direction.toLowerCase();

    return (
        <div className="text-right space-y-1">
            <div className="flex items-center justify-end gap-2">
                <span className={`text-[10px] font-black uppercase tracking-widest px-3 py-1.5 rounded-lg border ${correct
                    ? "text-bull bg-bull/10 border-bull/20"
                    : "text-bear bg-bear/10 border-bear/20"
                    }`}>
                    {correct ? "✓ Correct" : "✗ Wrong"}
                </span>
                <span className={`text-[10px] font-black uppercase tracking-widest px-2 py-1.5 rounded-lg bg-white/5 ${pred.actual_direction === "beat" ? "text-bull" :
                    pred.actual_direction === "miss" ? "text-bear" : "text-gray-400"
                    }`}>
                    {pred.actual_direction.toUpperCase()}
                </span>
            </div>
        </div>
    );
}

export default function HistoryPage() {
    const { getToken } = useAuth();
    const [history, setHistory] = useState<Prediction[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [selectedResult, setSelectedResult] = useState<Prediction | null>(null);
    const [filter, setFilter] = useState<"all" | "scored" | "pending">("all");
    const [sortBy, setSortBy] = useState<"date" | "confidence" | "brier">("date");
    const [verifyingIds, setVerifyingIds] = useState<Record<number, boolean>>({});

    const handleVerify = async (e: React.MouseEvent, pred: Prediction) => {
        e.stopPropagation();
        if (!pred.id) return;
        
        setVerifyingIds(prev => ({ ...prev, [pred.id!]: true }));
        try {
            const token = await getToken();
            const response = await api.verifyPrediction(pred.id, token || undefined);
            if (response.success && response.result) {
                setHistory(prev => prev.map(p => p.id === pred.id ? { ...p, ...response.result } : p));
            }
        } catch (err: any) {
            alert(`Verification failed: ${err.message || err}`);
        } finally {
            setVerifyingIds(prev => ({ ...prev, [pred.id!]: false }));
        }
    };

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

    const filtered = history
        .filter((p) => {
            if (filter === "scored") return !!p.actual_direction;
            if (filter === "pending") return !p.actual_direction;
            return true;
        })
        .sort((a, b) => {
            if (sortBy === "confidence") return b.confidence - a.confidence;
            if (sortBy === "brier") {
                const ba = a.accuracy_score ?? 999;
                const bb = b.accuracy_score ?? 999;
                return ba - bb;
            }
            return new Date(b.prediction_date).getTime() - new Date(a.prediction_date).getTime();
        });

    const scoredCount = history.filter((p) => !!p.actual_direction).length;
    const correctCount = history.filter((p) => p.actual_direction && p.direction.toLowerCase() === p.actual_direction.toLowerCase()).length;

    return (
        <div className="space-y-10 pb-20">
            <header className="flex justify-between items-end">
                <div>
                    <h1 className="text-4xl font-extrabold tracking-tight mb-2 font-outfit">Analysis History</h1>
                    <p className="text-gray-400 font-medium">
                        {history.length} predictions — {scoredCount} scored —&nbsp;
                        {scoredCount > 0 ? `${((correctCount / scoredCount) * 100).toFixed(0)}% win rate` : "awaiting outcomes"}
                    </p>
                </div>
                {selectedResult && (
                    <button onClick={() => setSelectedResult(null)}
                        className="text-xs font-bold text-accent hover:text-white uppercase tracking-widest transition-colors flex items-center gap-2 mb-2">
                        ← Back to History
                    </button>
                )}
            </header>

            {/* Filters */}
            {!selectedResult && !loading && history.length > 0 && (
                <div className="flex flex-wrap items-center gap-3">
                    <div className="flex items-center gap-1 bg-white/5 p-1 rounded-xl border border-white/10">
                        {(["all", "scored", "pending"] as const).map((f) => (
                            <button
                                key={f}
                                onClick={() => setFilter(f)}
                                className={`px-4 py-2 rounded-lg text-[10px] font-black uppercase tracking-widest transition-all ${filter === f ? "bg-accent text-black" : "text-gray-500 hover:text-white"}`}
                            >
                                {f}
                            </button>
                        ))}
                    </div>
                    <div className="flex items-center gap-1 bg-white/5 p-1 rounded-xl border border-white/10">
                        <span className="text-[9px] text-gray-600 uppercase font-bold px-2">Sort</span>
                        {(["date", "confidence", "brier"] as const).map((s) => (
                            <button
                                key={s}
                                onClick={() => setSortBy(s)}
                                className={`px-4 py-2 rounded-lg text-[10px] font-black uppercase tracking-widest transition-all ${sortBy === s ? "bg-white/10 text-white" : "text-gray-500 hover:text-white"}`}
                            >
                                {s}
                            </button>
                        ))}
                    </div>
                    <a href="/dashboard/performance"
                        className="ml-auto text-[10px] font-black uppercase tracking-widest text-accent hover:text-white border border-accent/30 hover:border-white/30 px-4 py-2.5 rounded-xl transition-all bg-accent/5 hover:bg-white/5">
                        View Performance Dashboard →
                    </a>
                </div>
            )}

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
                </div>
            ) : selectedResult ? (
                <AnalysisResult result={selectedResult} />
            ) : (
                <div className="glass rounded-3xl overflow-hidden border border-white/5 shadow-2xl">
                    <table className="w-full text-left">
                        <thead className="bg-white/5 border-b border-white/5">
                            <tr className="text-[10px] font-bold uppercase tracking-widest text-gray-500">
                                <th className="px-8 py-5">Ticker</th>
                                <th className="px-8 py-5">Analysis Date</th>
                                <th className="px-8 py-5">Prediction</th>
                                <th className="px-8 py-5">Confidence</th>
                                <th className="px-8 py-5">Actual EPS</th>
                                <th className="px-8 py-5">Post-Earnings Move</th>
                                <th className="px-8 py-5">Brier Score</th>
                                <th className="px-8 py-5 text-right">Outcome</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                            {filtered.map((row) => (
                                <tr
                                    key={(row.id ?? row.ticker) + row.prediction_date}
                                    onClick={() => setSelectedResult(row)}
                                    className="hover:bg-white/[0.02] transition-colors group cursor-pointer"
                                >
                                    <td className="px-8 py-6">
                                        <div className="font-black text-accent text-xl">{row.ticker}</div>
                                        <div className="text-[10px] text-gray-500 font-bold uppercase tracking-tighter">{row.company_name}</div>
                                    </td>
                                    <td className="px-8 py-6 text-sm text-gray-400 font-mono font-medium">
                                        {new Date(row.prediction_date).toLocaleDateString()}
                                    </td>
                                    <td className="px-8 py-6">
                                        <span className={`px-4 py-1.5 rounded-full text-[10px] font-black border ${row.direction === "BEAT"
                                            ? "bg-bull/10 text-bull border-bull/20"
                                            : row.direction === "MISS"
                                                ? "bg-bear/10 text-bear border-bear/20"
                                                : "bg-gray-800 text-gray-300 border-gray-700"
                                            }`}>
                                            {row.direction}
                                        </span>
                                    </td>
                                    <td className="px-8 py-6">
                                        <div className="flex items-center gap-3">
                                            <div className="w-16 h-1.5 bg-white/10 rounded-full overflow-hidden">
                                                <div className="h-full bg-accent rounded-full" style={{ width: `${row.confidence * 100}%` }} />
                                            </div>
                                            <span className="font-mono font-bold text-white text-sm">{(row.confidence * 100).toFixed(0)}%</span>
                                        </div>
                                    </td>
                                    <td className="px-8 py-6 font-mono text-sm text-white">
                                        {row.actual_eps !== undefined && row.actual_eps !== null
                                            ? `$${row.actual_eps.toFixed(2)}`
                                            : <span className="text-gray-600">—</span>}
                                    </td>
                                    <td className="px-8 py-6 font-mono text-sm">
                                        {row.actual_price_move_pct !== undefined && row.actual_price_move_pct !== null ? (
                                            (() => {
                                                const pct = row.actual_price_move_pct * 100;
                                                const sign = pct >= 0 ? "+" : "";
                                                const color = pct >= 0 ? "text-bull" : "text-bear";
                                                return <span className={color}>{sign}{pct.toFixed(2)}%</span>;
                                            })()
                                        ) : (
                                            <span className="text-gray-600">—</span>
                                        )}
                                    </td>
                                    <td className="px-8 py-6 font-mono text-sm text-gray-400">
                                        {row.accuracy_score !== undefined && row.accuracy_score !== null
                                            ? row.accuracy_score.toFixed(4)
                                            : <span className="text-gray-600">—</span>}
                                    </td>
                                    <td className="px-8 py-6">
                                        <OutcomeCell 
                                            pred={row} 
                                            onVerify={(e) => handleVerify(e, row)}
                                            isVerifying={row.id ? !!verifyingIds[row.id] : false}
                                        />
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                    {filtered.length === 0 && (
                        <div className="text-center py-12 text-gray-600 font-bold text-sm uppercase tracking-widest">
                            No predictions match this filter
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
