"use client";

const history = [
    { ticker: "GOOGL", date: "2024-04-25", direction: "BEAT", confidence: 87, result: "TBD" },
    { ticker: "TSLA", date: "2024-04-24", direction: "MISS", confidence: 62, result: "TBD" },
    { ticker: "NVDA", date: "2024-02-21", direction: "BEAT", confidence: 91, result: "MATCH" },
    { ticker: "MSFT", date: "2024-01-30", direction: "BEAT", confidence: 78, result: "MATCH" },
];

export default function HistoryPage() {
    return (
        <div className="space-y-12">
            <header>
                <h1 className="text-4xl font-extrabold tracking-tight mb-2 font-outfit">Analysis History</h1>
                <p className="text-gray-400 font-medium">Review and track the accuracy of your historical earnings predictions.</p>
            </header>

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
                            <tr key={`${row.ticker}-${row.date}`} className="hover:bg-white/[0.01] transition-colors group cursor-pointer">
                                <td className="px-8 py-6">
                                    <div className="font-black text-accent text-xl">{row.ticker}</div>
                                    <div className="text-[10px] text-gray-500 font-bold uppercase tracking-tighter">Earnings Report</div>
                                </td>
                                <td className="px-8 py-6 text-sm text-gray-400 font-mono font-medium">{row.date}</td>
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
                                    <span className={`text-[10px] font-black uppercase tracking-widest ${row.result === "MATCH" ? "text-bull" : "text-gray-600"
                                        }`}>
                                        {row.result}
                                    </span>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
