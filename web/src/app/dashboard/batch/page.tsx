"use client";

import { useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { api, Prediction } from "@/lib/api";
import AnalysisResult from "@/components/AnalysisResult";

interface BatchItem {
    ticker: string;
    report_date: string;
    user_analysis: string;
}

export default function BatchAnalysisPage() {
    const { getToken } = useAuth();
    const [companies, setCompanies] = useState<BatchItem[]>([{ ticker: "", report_date: "", user_analysis: "" }]);
    const [loading, setLoading] = useState(false);
    const [results, setResults] = useState<Prediction[] | null>(null);
    const [error, setError] = useState<string | null>(null);

    const handleAddRow = () => {
        setCompanies([...companies, { ticker: "", report_date: "", user_analysis: "" }]);
    };

    const handleRemoveRow = (index: number) => {
        const newCompanies = [...companies];
        newCompanies.splice(index, 1);
        setCompanies(newCompanies);
    };

    const handleChange = (index: number, field: keyof BatchItem, value: string) => {
        const newCompanies = [...companies];
        newCompanies[index] = { ...newCompanies[index], [field]: value };
        setCompanies(newCompanies);
    };

    const handleRunBatch = async () => {
        const validCompanies = companies.filter(c => c.ticker && c.report_date);
        if (validCompanies.length === 0) {
            setError("Please provide at least one ticker and report date.");
            return;
        }

        setLoading(true);
        setError(null);
        setResults(null);

        try {
            const token = await getToken();
            const tokenStr = token ?? undefined;
            const data = await api.predictBatch(validCompanies, undefined, tokenStr);
            setResults(data);
        } catch (err: any) {
            setError(err.message || "An error occurred during batch analysis.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="space-y-6 pb-20">
            <header className="flex justify-between items-end mb-[20px]">
                <div>
                    <h1 className="text-[clamp(1.9rem,3vw,2.3rem)] font-display font-semibold tracking-tight text-white mb-2 leading-none">
                        Batch Analysis
                    </h1>
                    <p className="text-sm text-ink-mute font-body">Predict multiple earnings simultaneously.</p>
                </div>
            </header>

            <div className="grid grid-cols-1 gap-10">
                {/* Form */}
                <div className="bg-panel border border-[#26334A] rounded-[16px] p-6 shadow-[0_20px_60px_rgba(0,0,0,0.35)] relative overflow-hidden">
                    {loading && (
                        <div className="absolute inset-0 bg-black/60 backdrop-blur-md rounded-[16px] z-10 flex flex-col items-center justify-center border border-teal/20">
                            <div className="w-12 h-12 border-4 border-teal border-t-transparent rounded-full animate-spin mb-4" />
                            <p className="text-teal font-mono font-bold animate-pulse text-xs tracking-[0.2em] uppercase">Running Batch Predictions...</p>
                        </div>
                    )}

                    <div className="space-y-6">
                        {companies.map((company, index) => (
                            <div key={index} className="flex flex-wrap lg:flex-nowrap gap-4 items-center border-b border-panel-line pb-4 last:border-b-0 last:pb-0">
                                <div className="w-full lg:w-1/4">
                                    <label className="text-[10px] font-mono font-bold uppercase tracking-wider text-ink-dim mb-2 block select-none">Ticker</label>
                                    <input
                                        type="text"
                                        value={company.ticker}
                                        onChange={(e) => handleChange(index, 'ticker', e.target.value)}
                                        placeholder="E.G. AAPL"
                                        className="w-full bg-[#05070a] border border-panel-line rounded-xl px-4 py-2.5 focus:border-teal focus:ring-2 focus:ring-teal/20 outline-none uppercase font-semibold text-xs tracking-wider text-white placeholder-white/20 transition-all font-body"
                                    />
                                </div>
                                <div className="w-full lg:w-1/4">
                                    <label className="text-[10px] font-mono font-bold uppercase tracking-wider text-ink-dim mb-2 block select-none">Report Date</label>
                                    <input
                                        type="date"
                                        value={company.report_date}
                                        onChange={(e) => handleChange(index, 'report_date', e.target.value)}
                                        className="w-full bg-[#05070a] border border-panel-line rounded-xl px-4 py-2.5 focus:border-teal focus:ring-2 focus:ring-teal/20 outline-none text-white relative [color-scheme:dark] text-xs font-mono transition-all"
                                    />
                                </div>
                                <div className="w-full lg:flex-1">
                                    <label className="text-[10px] font-mono font-bold uppercase tracking-wider text-ink-dim mb-2 block select-none">User Analysis (Optional)</label>
                                    <input
                                        type="text"
                                        value={company.user_analysis}
                                        onChange={(e) => handleChange(index, 'user_analysis', e.target.value)}
                                        placeholder="Optional Context..."
                                        className="w-full bg-[#05070a] border border-panel-line rounded-xl px-4 py-2.5 focus:border-teal focus:ring-2 focus:ring-teal/20 outline-none text-white text-xs placeholder-white/20 transition-all font-body"
                                    />
                                </div>
                                <div className="mt-6">
                                    <button 
                                        onClick={() => handleRemoveRow(index)}
                                        disabled={companies.length <= 1}
                                        className="text-red-500 bg-red-500/10 p-2.5 rounded-xl hover:bg-red-500/20 border border-red-500/20 transition-all cursor-pointer font-bold disabled:opacity-30 disabled:cursor-not-allowed"
                                    >
                                        ✗
                                    </button>
                                </div>
                            </div>
                        ))}

                        <div className="flex justify-between items-center mt-8 pt-4 border-t border-panel-line">
                            <button
                                onClick={handleAddRow}
                                className="text-xs font-mono font-bold text-teal hover:text-teal/80 uppercase tracking-widest px-4 py-2 bg-teal/10 rounded-lg border border-teal/20 transition-all cursor-pointer"
                            >
                                + Add Ticker
                            </button>

                            <button
                                onClick={handleRunBatch}
                                disabled={loading}
                                className="py-2.5 px-8 rounded-xl font-mono font-bold uppercase tracking-widest text-xs bg-gradient-to-br from-teal to-teal-deep text-[#04231F] hover:shadow-[0_0_15px_rgba(45,212,191,0.3)] transition-all cursor-pointer flex items-center justify-center"
                            >
                                {loading ? "Analyzing..." : "Run Batch Predictions"}
                            </button>
                        </div>

                        {error && (
                            <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-xs text-red-500 font-bold mt-4 select-none">
                                ⚠️ {error}
                            </div>
                        )}
                    </div>
                </div>

                {/* Results List */}
                {results && results.length > 0 && (
                    <div className="space-y-6">
                        <h2 className="text-xl font-display font-semibold text-white uppercase tracking-wider">Batch Results</h2>
                        {results.map((result, idx) => (
                            <div key={idx} className="rounded-[16px] border border-[#26334A] bg-panel overflow-hidden shadow-[0_20px_60px_rgba(0,0,0,0.35)] animate-in fade-in duration-300">
                                <AnalysisResult result={result} />
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
