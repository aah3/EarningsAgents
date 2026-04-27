"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { api, PredictionMetrics } from "@/lib/api";

// ─── Tiny inline chart helpers (no external deps) ───────────────────────────

function BarChart({ data, labelKey, valueKey, colorFn, maxValue }: {
    data: Record<string, any>[];
    labelKey: string;
    valueKey: string;
    colorFn?: (row: Record<string, any>) => string;
    maxValue?: number;
}) {
    const max = maxValue ?? Math.max(...data.map((d) => d[valueKey]), 1);
    return (
        <div className="space-y-3">
            {data.map((row, i) => (
                <div key={i} className="flex items-center gap-4">
                    <div className="w-28 text-right text-[11px] font-bold text-gray-400 shrink-0 truncate">{row[labelKey]}</div>
                    <div className="flex-1 h-6 bg-white/5 rounded-full overflow-hidden">
                        <div
                            className="h-full rounded-full transition-all duration-700"
                            style={{
                                width: `${Math.max(2, (row[valueKey] / max) * 100)}%`,
                                background: colorFn ? colorFn(row) : "var(--accent-cyan)",
                            }}
                        />
                    </div>
                    <div className="w-14 text-right text-[11px] font-mono font-bold text-white shrink-0">
                        {typeof row[valueKey] === "number" && row[valueKey] < 1 && row[valueKey] > 0
                            ? `${(row[valueKey] * 100).toFixed(0)}%`
                            : row[valueKey]}
                    </div>
                </div>
            ))}
        </div>
    );
}

function BrierSparkline({ points }: { points: Array<{ date: string; brier: number; ticker: string }> }) {
    if (!points.length) return <div className="text-gray-600 text-xs text-center py-8">No scored predictions yet</div>;
    const max = Math.max(...points.map((p) => p.brier), 0.01);
    const H = 120;
    const W = 100;
    const xs = points.map((_, i) => (i / (points.length - 1 || 1)) * W);
    const ys = points.map((p) => H - (p.brier / max) * H * 0.9);
    const path = xs.map((x, i) => `${i === 0 ? "M" : "L"} ${x.toFixed(1)},${ys[i].toFixed(1)}`).join(" ");
    const fill = [...xs.map((x, i) => `${i === 0 ? "M" : "L"} ${x.toFixed(1)},${ys[i].toFixed(1)}`), `L ${xs[xs.length - 1].toFixed(1)},${H} L 0,${H} Z`].join(" ");

    return (
        <div className="relative">
            <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-28" preserveAspectRatio="none">
                <defs>
                    <linearGradient id="brierGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#2dd4bf" stopOpacity="0.3" />
                        <stop offset="100%" stopColor="#2dd4bf" stopOpacity="0" />
                    </linearGradient>
                </defs>
                <path d={fill} fill="url(#brierGrad)" />
                <path d={path} fill="none" stroke="#2dd4bf" strokeWidth="1.5" />
                {points.map((p, i) => (
                    <circle key={i} cx={xs[i]} cy={ys[i]} r="1.5" fill="#2dd4bf" />
                ))}
            </svg>
            <div className="flex justify-between text-[9px] font-mono text-gray-600 mt-1">
                <span>{points[0]?.date.slice(0, 10)}</span>
                <span>{points[points.length - 1]?.date.slice(0, 10)}</span>
            </div>
        </div>
    );
}

function CalibrationChart({ buckets }: { buckets: PredictionMetrics["confidence_buckets"] }) {
    if (!buckets.length) return <div className="text-gray-600 text-xs text-center py-8">No scored predictions yet</div>;
    const H = 140;
    const W = 100;
    const n = buckets.length;
    const barW = W / n - 1;

    return (
        <svg viewBox={`0 0 ${W} ${H + 20}`} className="w-full h-44" preserveAspectRatio="none">
            {/* Perfect calibration diagonal */}
            <line x1="0" y1={H} x2={W} y2="0" stroke="rgba(255,255,255,0.1)" strokeDasharray="2,2" strokeWidth="0.8" />
            {buckets.map((b, i) => {
                const x = (i / n) * W;
                const predH = (b.predicted / 100) * H;
                const actH = b.actual_win_rate * H;
                return (
                    <g key={i}>
                        <rect x={x} y={H - predH} width={barW} height={predH} fill="rgba(59,130,246,0.25)" />
                        <rect x={x + barW * 0.25} y={H - actH} width={barW * 0.5} height={actH} fill="rgba(45,212,191,0.7)" rx="1" />
                    </g>
                );
            })}
            <text x="1" y={H + 14} fill="#6b7280" fontSize="5" fontFamily="monospace">Low confidence</text>
            <text x={W - 24} y={H + 14} fill="#6b7280" fontSize="5" fontFamily="monospace">High confidence</text>
        </svg>
    );
}

// ─── Stat card ───────────────────────────────────────────────────────────────

function StatCard({ label, value, sub, color, icon }: {
    label: string; value: string; sub?: string; color: string; icon: string;
}) {
    return (
        <div className="glass p-6 rounded-2xl border border-white/10 bg-[#0c1017] flex items-center gap-5 hover:bg-[#11161d] transition-colors">
            <div className="w-12 h-12 rounded-xl flex items-center justify-center text-2xl shrink-0" style={{ background: `${color}20`, border: `1px solid ${color}30` }}>
                {icon}
            </div>
            <div>
                <p className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-1">{label}</p>
                <p className="text-2xl font-black text-white tracking-tight">{value}</p>
                {sub && <p className="text-[10px] font-bold mt-0.5" style={{ color }}>{sub}</p>}
            </div>
        </div>
    );
}

// ─── Page ────────────────────────────────────────────────────────────────────

export default function PerformancePage() {
    const { getToken } = useAuth();
    const [metrics, setMetrics] = useState<PredictionMetrics | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function loadMetrics() {
            try {
                const token = await getToken();
                if (!token) throw new Error("Not authenticated");
                const data = await api.getMetrics(token);
                setMetrics(data);
            } catch (err: any) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        }
        loadMetrics();
    }, [getToken]);

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[60vh] gap-6">
                <div className="w-16 h-16 border-4 border-accent border-t-transparent rounded-full animate-spin" />
                <p className="text-gray-500 font-bold uppercase tracking-widest text-xs">Loading performance data...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="glass p-16 rounded-3xl border border-red-500/20 bg-red-500/5 text-center">
                <p className="text-red-400 font-black text-lg mb-2">Failed to load metrics</p>
                <p className="text-gray-500 text-sm">{error}</p>
            </div>
        );
    }

    const m = metrics!;
    const winPct = m.scored_predictions > 0 ? (m.win_rate * 100).toFixed(1) : "—";
    const brierLabel = m.avg_brier_score < 0.15 ? "Excellent" : m.avg_brier_score < 0.25 ? "Good" : "Needs work";

    // Agent vote table rows
    const agents = Object.keys(m.agent_vote_breakdown);

    return (
        <div className="space-y-10 pb-20">
            <header>
                <h1 className="text-4xl font-extrabold tracking-tight mb-2 font-outfit">Performance Dashboard</h1>
                <p className="text-gray-400 font-medium">
                    Live evaluation metrics across {m.total_predictions} prediction{m.total_predictions !== 1 ? "s" : ""} —&nbsp;
                    {m.scored_predictions} scored.
                </p>
            </header>

            {/* KPI Strip */}
            <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
                <StatCard label="Win Rate" value={m.scored_predictions > 0 ? `${winPct}%` : "—"} sub={m.scored_predictions > 0 ? `${m.scored_predictions} scored` : "No scored predictions yet"} color="var(--bull-green)" icon="🎯" />
                <StatCard label="Avg Confidence" value={`${(m.avg_confidence * 100).toFixed(0)}%`} sub="All predictions" color="var(--accent-cyan)" icon="📊" />
                <StatCard label="Avg Brier Score" value={m.scored_predictions > 0 ? m.avg_brier_score.toFixed(4) : "—"} sub={m.scored_predictions > 0 ? brierLabel : "Lower is better"} color="var(--consensus-purple)" icon="📐" />
                <StatCard label="Total Predictions" value={String(m.total_predictions)} sub={`${m.beat_predictions} BEAT · ${m.miss_predictions} MISS`} color="var(--quant-blue)" icon="🔍" />
            </div>

            {/* Main grid */}
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">

                {/* Brier Score Over Time */}
                <div className="xl:col-span-2 glass p-6 rounded-3xl border border-white/10 bg-[#0c1017]">
                    <div className="flex items-center justify-between mb-5">
                        <h2 className="font-black uppercase tracking-widest text-sm text-white">Brier Score Over Time</h2>
                        <span className="text-[10px] text-gray-500 font-bold uppercase tracking-widest bg-white/5 px-3 py-1.5 rounded-lg">Lower = More Accurate</span>
                    </div>
                    <BrierSparkline points={m.brier_over_time} />
                    {m.brier_over_time.length > 0 && (
                        <div className="mt-4 pt-4 border-t border-white/5 grid grid-cols-3 gap-4 text-center">
                            <div>
                                <p className="text-[10px] text-gray-600 uppercase tracking-widest font-bold">Best</p>
                                <p className="font-mono font-black text-bull text-sm">{Math.min(...m.brier_over_time.map(p => p.brier)).toFixed(4)}</p>
                            </div>
                            <div>
                                <p className="text-[10px] text-gray-600 uppercase tracking-widest font-bold">Average</p>
                                <p className="font-mono font-black text-accent text-sm">{m.avg_brier_score.toFixed(4)}</p>
                            </div>
                            <div>
                                <p className="text-[10px] text-gray-600 uppercase tracking-widest font-bold">Worst</p>
                                <p className="font-mono font-black text-bear text-sm">{Math.max(...m.brier_over_time.map(p => p.brier)).toFixed(4)}</p>
                            </div>
                        </div>
                    )}
                </div>

                {/* Direction Breakdown */}
                <div className="glass p-6 rounded-3xl border border-white/10 bg-[#0c1017]">
                    <h2 className="font-black uppercase tracking-widest text-sm text-white mb-5">Direction Breakdown</h2>
                    {Object.keys(m.direction_breakdown).length > 0 ? (
                        <BarChart
                            data={Object.entries(m.direction_breakdown).map(([dir, cnt]) => ({ dir, cnt }))}
                            labelKey="dir"
                            valueKey="cnt"
                            colorFn={(r) => r.dir === "BEAT" ? "var(--bull-green)" : r.dir === "MISS" ? "var(--bear-red)" : "var(--quant-blue)"}
                        />
                    ) : (
                        <p className="text-gray-600 text-xs text-center py-8">No predictions yet</p>
                    )}

                    {m.scored_predictions > 0 && (
                        <div className="mt-6 pt-5 border-t border-white/5 grid grid-cols-2 gap-3">
                            <div className="p-3 rounded-xl bg-bull/10 border border-bull/20 text-center">
                                <p className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">BEAT Correct</p>
                                <p className="font-black text-bull text-xl">{m.beat_correct}<span className="text-gray-600 text-sm font-bold">/{m.beat_predictions}</span></p>
                            </div>
                            <div className="p-3 rounded-xl bg-bear/10 border border-bear/20 text-center">
                                <p className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">MISS Correct</p>
                                <p className="font-black text-bear text-xl">{m.miss_correct}<span className="text-gray-600 text-sm font-bold">/{m.miss_predictions}</span></p>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Calibration + Agent Vote grid */}
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                {/* Confidence Calibration */}
                <div className="glass p-6 rounded-3xl border border-white/10 bg-[#0c1017]">
                    <div className="flex items-center justify-between mb-5">
                        <h2 className="font-black uppercase tracking-widest text-sm text-white">Confidence Calibration</h2>
                        <div className="flex items-center gap-3 text-[10px] font-bold uppercase tracking-widest">
                            <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded bg-blue-500/50 inline-block" />Predicted</span>
                            <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded bg-accent/70 inline-block" />Actual</span>
                        </div>
                    </div>
                    <CalibrationChart buckets={m.confidence_buckets} />
                    <p className="text-[10px] text-gray-600 text-center mt-2 font-medium">
                        Perfect calibration = bars of equal height in each bucket
                    </p>
                </div>

                {/* Agent Vote Breakdown */}
                <div className="glass p-6 rounded-3xl border border-white/10 bg-[#0c1017]">
                    <h2 className="font-black uppercase tracking-widest text-sm text-white mb-5">Agent Vote Breakdown</h2>
                    {agents.length > 0 ? (
                        <div className="space-y-5">
                            {agents.map((agent) => {
                                const votes = m.agent_vote_breakdown[agent];
                                const total = Object.values(votes).reduce((a, b) => a + b, 0);
                                const agentColor: Record<string, string> = {
                                    bull: "var(--bull-green)", bear: "var(--bear-red)",
                                    quant: "var(--quant-blue)", consensus: "var(--consensus-purple)",
                                };
                                const c = agentColor[agent.toLowerCase()] || "var(--accent-cyan)";
                                return (
                                    <div key={agent}>
                                        <div className="flex items-center justify-between mb-2">
                                            <span className="text-xs font-black uppercase tracking-widest" style={{ color: c }}>{agent}</span>
                                            <span className="text-[10px] text-gray-600 font-bold">{total} vote{total !== 1 ? "s" : ""}</span>
                                        </div>
                                        <div className="flex h-5 rounded-full overflow-hidden gap-px">
                                            {Object.entries(votes).map(([dir, cnt]) => (
                                                <div
                                                    key={dir}
                                                    title={`${dir}: ${cnt}`}
                                                    style={{
                                                        width: `${(cnt / total) * 100}%`,
                                                        background: dir === "BEAT" ? "var(--bull-green)" : dir === "MISS" ? "var(--bear-red)" : "var(--quant-blue)",
                                                        opacity: 0.8,
                                                    }}
                                                />
                                            ))}
                                        </div>
                                        <div className="flex gap-3 mt-1.5">
                                            {Object.entries(votes).map(([dir, cnt]) => (
                                                <span key={dir} className="text-[9px] font-bold text-gray-500 uppercase tracking-widest">
                                                    {dir} {((cnt / total) * 100).toFixed(0)}%
                                                </span>
                                            ))}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    ) : (
                        <p className="text-gray-600 text-xs text-center py-8">No agent vote data available yet</p>
                    )}
                </div>
            </div>

            {/* Recent scored predictions table */}
            {m.brier_over_time.length > 0 && (
                <div className="glass rounded-3xl overflow-hidden border border-white/10 bg-[#0c1017]">
                    <div className="px-8 py-5 border-b border-white/5">
                        <h2 className="font-black uppercase tracking-widest text-sm text-white">Recent Scored Predictions</h2>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="w-full text-left">
                            <thead className="bg-white/5 border-b border-white/5">
                                <tr className="text-[10px] font-bold uppercase tracking-widest text-gray-500">
                                    <th className="px-8 py-4">Ticker</th>
                                    <th className="px-8 py-4">Date</th>
                                    <th className="px-8 py-4">Brier Score</th>
                                    <th className="px-8 py-4 text-right">Quality</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-white/5">
                                {[...m.brier_over_time].reverse().slice(0, 10).map((row, i) => {
                                    const quality = row.brier < 0.1 ? { label: "Excellent", color: "text-bull" } :
                                        row.brier < 0.2 ? { label: "Good", color: "text-accent" } :
                                            row.brier < 0.35 ? { label: "Fair", color: "text-yellow-400" } :
                                                { label: "Poor", color: "text-bear" };
                                    return (
                                        <tr key={i} className="hover:bg-white/[0.02] transition-colors">
                                            <td className="px-8 py-4 font-black text-accent text-lg">{row.ticker}</td>
                                            <td className="px-8 py-4 text-sm text-gray-400 font-mono">{row.date.slice(0, 10)}</td>
                                            <td className="px-8 py-4 font-mono font-bold text-white">{row.brier.toFixed(4)}</td>
                                            <td className={`px-8 py-4 text-right font-black text-sm uppercase tracking-widest ${quality.color}`}>{quality.label}</td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
        </div>
    );
}
