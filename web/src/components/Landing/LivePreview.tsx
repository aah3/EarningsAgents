"use client";

const predictions = [
    { ticker: "GOOGL", company: "Alphabet Inc.", date: "2024-04-25", direction: "BEAT", confidence: 87, color: "var(--bull-green)" },
    { ticker: "TSLA", company: "Tesla, Inc.", date: "2024-04-24", direction: "MISS", confidence: 62, color: "var(--bear-red)" },
    { ticker: "NVDA", company: "NVIDIA Corp.", date: "2024-05-22", direction: "BEAT", confidence: 94, color: "var(--bull-green)" },
    { ticker: "MSFT", company: "Microsoft Corp.", date: "2024-04-25", direction: "BEAT", confidence: 78, color: "var(--bull-green)" },
];

export default function LivePreview() {
    return (
        <section className="section-padding px-8 border-t border-white/5">
            <div className="max-w-7xl mx-auto">
                <div className="mb-16">
                    <h2 className="text-4xl font-bold mb-4 tracking-tight">Live Predictions Dashboard Preview</h2>
                    <div className="h-1 w-20 bg-accent rounded-full" />
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-12 gap-16">
                    <div className="lg:col-span-8">
                        <div className="glass rounded-[2rem] overflow-hidden border border-white/5 shadow-3xl">
                            <div className="p-8 border-b border-white/5 flex justify-between items-center bg-white/[0.01]">
                                <span className="font-bold text-gray-300">This Week&apos;s Top Predictions</span>
                                <div className="flex gap-2.5">
                                    <div className="w-3 h-3 rounded-full bg-red-500/20 border border-red-500/40" />
                                    <div className="w-3 h-3 rounded-full bg-yellow-500/20 border border-yellow-500/40" />
                                    <div className="w-3 h-3 rounded-full bg-green-500/20 border border-green-500/40" />
                                </div>
                            </div>
                            <div className="overflow-x-auto">
                                <table className="w-full text-left text-sm">
                                    <thead>
                                        <tr className="text-gray-500 uppercase text-[10px] font-bold tracking-[0.15em] border-b border-white/5 bg-black/10">
                                            <th className="px-8 py-6">Ticker</th>
                                            <th className="px-8 py-6">Company</th>
                                            <th className="px-8 py-6">Report Date</th>
                                            <th className="px-8 py-6 text-center">Prediction</th>
                                            <th className="px-8 py-6 text-right">Confidence</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-white/5">
                                        {predictions.map((p) => (
                                            <tr key={p.ticker} className="hover:bg-white/[0.02] transition-colors group">
                                                <td className="px-8 py-7 font-extrabold text-blue-400 text-base">{p.ticker}</td>
                                                <td className="px-8 py-7 text-gray-300 font-medium">{p.company}</td>
                                                <td className="px-8 py-7 text-gray-500 font-mono">{p.date}</td>
                                                <td className="px-8 py-7">
                                                    <div
                                                        className="mx-auto px-4 py-1.5 rounded-full text-[10px] font-black text-center tracking-wider"
                                                        style={{ backgroundColor: `${p.color}15`, color: p.color, border: `1px solid ${p.color}30` }}
                                                    >
                                                        {p.direction}
                                                    </div>
                                                </td>
                                                <td className="px-8 py-7 text-right">
                                                    <span className="font-mono text-white text-lg font-bold">{p.confidence}%</span>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>

                    <div className="lg:col-span-4 flex flex-col gap-8 justify-center">
                        <div className="glass p-10 rounded-3xl border-l-4 border-l-accent/40 bg-white/[0.01]">
                            <h3 className="text-2xl font-bold mb-4 flex items-center gap-4">
                                <span className="text-accent">📄</span> Explainable AI
                            </h3>
                            <p className="text-base text-gray-400 leading-relaxed">
                                Detailed breakdowns of bull and bear cases, synthesized from thousands of data points.
                            </p>
                        </div>
                        <div className="glass p-10 rounded-3xl border-l-4 border-l-blue-500/40 bg-white/[0.01]">
                            <h3 className="text-2xl font-bold mb-4 flex items-center gap-4">
                                <span className="text-blue-400">🎯</span> High Accuracy
                            </h3>
                            <p className="text-base text-gray-400 leading-relaxed">
                                Multi-agent system rigorously testing every hypothesis for superior results.
                            </p>
                        </div>
                        <div className="glass p-10 rounded-3xl border-l-4 border-l-purple-500/40 bg-white/[0.01]">
                            <h3 className="text-2xl font-bold mb-4 flex items-center gap-4">
                                <span className="text-purple-400">📈</span> Nuanced Scoring
                            </h3>
                            <p className="text-base text-gray-400 leading-relaxed">
                                Confidence ratings derived from data quality and agent cross-verification.
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </section>
    );
}
