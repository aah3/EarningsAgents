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
        <div className="space-y-10 pb-20">
            <header className="mb-10">
                <h1 className="text-4xl lg:text-5xl font-extrabold tracking-tight mb-3 font-outfit text-white">Batch Analysis</h1>
                <p className="text-gray-400 font-medium text-lg">Predict multiple earnings simultaneously.</p>
            </header>

            <div className="grid grid-cols-1 gap-10">
                {/* Form */}
                <div className="glass p-8 rounded-3xl border border-white/10 bg-[#0c1017] shadow-2xl relative">
                    {loading && (
                        <div className="absolute inset-0 bg-black/60 backdrop-blur-md rounded-3xl z-10 flex flex-col items-center justify-center border border-accent/20">
                            <div className="relative w-16 h-16 mb-6">
                                <div className="absolute inset-0 rounded-full border-4 border-white/10"></div>
                                <div className="absolute inset-0 rounded-full border-4 border-transparent border-t-accent animate-spin"></div>
                                <div className="absolute inset-0 flex items-center justify-center text-accent">
                                    <span className="animate-pulse">⚡</span>
                                </div>
                            </div>
                            <p className="text-accent font-bold animate-pulse text-xs tracking-[0.2em] uppercase">Running Batch Predictions...</p>
                        </div>
                    )}

                    <div className="space-y-6">
                        {companies.map((company, index) => (
                            <div key={index} className="flex flex-wrap lg:flex-nowrap gap-4 items-center">
                                <div className="w-full lg:w-1/4">
                                    <label className="text-[10px] font-bold uppercase tracking-[0.15em] text-gray-400 mb-2 block">Ticker</label>
                                    <input
                                        type="text"
                                        value={company.ticker}
                                        onChange={(e) => handleChange(index, 'ticker', e.target.value)}
                                        placeholder="E.G. AAPL"
                                        className="w-full bg-[#080b11] border border-white/10 rounded-2xl px-5 py-3 focus:border-accent focus:ring-1 focus:ring-accent/50 outline-none uppercase font-black text-white"
                                    />
                                </div>
                                <div className="w-full lg:w-1/4">
                                    <label className="text-[10px] font-bold uppercase tracking-[0.15em] text-gray-400 mb-2 block">Report Date</label>
                                    <input
                                        type="date"
                                        value={company.report_date}
                                        onChange={(e) => handleChange(index, 'report_date', e.target.value)}
                                        className="w-full bg-[#080b11] border border-white/10 rounded-2xl px-5 py-3 focus:border-accent focus:ring-1 focus:ring-accent/50 outline-none text-white relative [color-scheme:dark]"
                                    />
                                </div>
                                <div className="w-full lg:flex-1">
                                    <label className="text-[10px] font-bold uppercase tracking-[0.15em] text-gray-400 mb-2 block">User Analysis (Optional)</label>
                                    <input
                                        type="text"
                                        value={company.user_analysis}
                                        onChange={(e) => handleChange(index, 'user_analysis', e.target.value)}
                                        placeholder="Optional Context..."
                                        className="w-full bg-[#080b11] border border-white/10 rounded-2xl px-5 py-3 focus:border-accent outline-none text-white"
                                    />
                                </div>
                                <div className="mt-6">
                                    <button 
                                        onClick={() => handleRemoveRow(index)}
                                        className="text-red-500 bg-red-500/10 p-3 rounded-2xl hover:bg-red-500/20"
                                    >
                                        ✗
                                    </button>
                                </div>
                            </div>
                        ))}

                        <div className="flex justify-between items-center mt-8">
                            <button
                                onClick={handleAddRow}
                                className="text-xs font-bold text-accent uppercase tracking-widest px-4 py-2 bg-accent/10 rounded-lg hover:bg-accent/20"
                            >
                                + Add Ticker
                            </button>

                            <button
                                onClick={handleRunBatch}
                                disabled={loading}
                                className="w-1/3 py-4 rounded-2xl font-black uppercase tracking-[0.15em] text-xs bg-accent text-background hover:bg-accent/90"
                            >
                                {loading ? "Analyzing..." : "Run Batch Predictions"}
                            </button>
                        </div>

                        {error && (
                            <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-xs text-red-500 font-bold mt-4">
                                ⚠️ {error}
                            </div>
                        )}
                    </div>
                </div>

                {/* Results List */}
                {results && results.length > 0 && (
                    <div className="space-y-10">
                        <h2 className="text-2xl font-bold font-outfit text-white">Batch Results</h2>
                        {results.map((result, idx) => (
                            <div key={idx} className="bg-[#0c1017] border border-white/10 rounded-[40px] overflow-hidden">
                                <AnalysisResult result={result} />
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
