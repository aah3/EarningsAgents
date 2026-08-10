"use client";

import { useState, useEffect, useCallback } from "react";
import { useAuth } from "@clerk/nextjs";
import { api, ResearchThesis, ResearchHistoryResponse } from "@/lib/api";
import {
    Sparkles,
    UserCheck,
    Globe,
    TrendingUp,
    TrendingDown,
    ShieldAlert,
    Calendar,
    Table,
    History,
    GitCompare,
    RefreshCw,
    Edit3,
    CheckCircle2,
    AlertTriangle,
    X,
    Layers,
    Info
} from "lucide-react";

export default function ResearchThesisView({ ticker }: { ticker: string }) {
    const { getToken } = useAuth();
    const [thesis, setThesis] = useState<ResearchThesis | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Modal & Drawer states
    const [showPersonalizeModal, setShowPersonalizeModal] = useState(false);
    const [userNotesInput, setUserNotesInput] = useState("");
    const [submittingNotes, setSubmittingNotes] = useState(false);

    const [showBaselineModal, setShowBaselineModal] = useState(false);
    const [baselineThesis, setBaselineThesis] = useState<ResearchThesis | null>(null);
    const [loadingBaseline, setLoadingBaseline] = useState(false);

    const [showHistoryDrawer, setShowHistoryDrawer] = useState(false);
    const [historyData, setHistoryData] = useState<ResearchHistoryResponse | null>(null);
    const [loadingHistory, setLoadingHistory] = useState(false);

    const [toastMsg, setToastMsg] = useState<{ text: string; type: "success" | "error" | "info" } | null>(null);

    const fetchThesis = useCallback(async () => {
        if (!ticker) return;
        setLoading(true);
        setError(null);
        try {
            const token = (await getToken()) || undefined;
            const res = await api.getResearchThesis(ticker, token);
            setThesis(res);
        } catch (err: any) {
            if (err.message && err.message.includes("404")) {
                setThesis(null);
            } else {
                setError(err.message || "Failed to load research thesis.");
            }
        } finally {
            setLoading(false);
        }
    }, [ticker, getToken]);

    useEffect(() => {
        fetchThesis();
    }, [fetchThesis]);

    const handleTriggerThesis = async (notes?: string) => {
        setSubmittingNotes(true);
        setToastMsg(null);
        try {
            const token = (await getToken()) || undefined;
            const res = await api.triggerResearch(ticker, notes, token);
            setShowPersonalizeModal(false);
            setUserNotesInput("");
            setToastMsg({
                text: `Research thesis generation task enqueued! (Task ID: ${res.task_id.substring(0, 8)}...)`,
                type: "info"
            });
            // Polling after short delay
            setTimeout(() => {
                fetchThesis();
            }, 4000);
        } catch (err: any) {
            setToastMsg({ text: `Failed to trigger research: ${err.message}`, type: "error" });
        } finally {
            setSubmittingNotes(false);
        }
    };

    const handleFetchBaselineComparison = async () => {
        setShowBaselineModal(true);
        setLoadingBaseline(true);
        try {
            const token = (await getToken()) || undefined;
            const res = await api.getResearchBaseline(ticker, token);
            setBaselineThesis(res);
        } catch (err: any) {
            setToastMsg({ text: `Failed to fetch baseline thesis: ${err.message}`, type: "error" });
            setShowBaselineModal(false);
        } finally {
            setLoadingBaseline(false);
        }
    };

    const handleFetchHistory = async () => {
        setShowHistoryDrawer(true);
        setLoadingHistory(true);
        try {
            const token = (await getToken()) || undefined;
            const res = await api.getResearchHistory(ticker, token);
            setHistoryData(res);
        } catch (err: any) {
            setToastMsg({ text: `Failed to fetch thesis history: ${err.message}`, type: "error" });
            setShowHistoryDrawer(false);
        } finally {
            setLoadingHistory(false);
        }
    };

    if (loading) {
        return (
            <div className="p-12 text-center rounded-2xl bg-panel border border-panel-line animate-pulse flex flex-col items-center justify-center min-h-[320px]">
                <RefreshCw className="w-8 h-8 text-teal animate-spin mb-4" />
                <p className="text-ink-mute label-caps">Loading Fundamental Research Thesis for {ticker}...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-8 rounded-2xl bg-bear/10 border border-bear/30 text-bear flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <AlertTriangle className="w-6 h-6 shrink-0" />
                    <span>{error}</span>
                </div>
                <button
                    onClick={fetchThesis}
                    className="px-4 py-2 bg-bear/20 hover:bg-bear/30 rounded-xl label-caps transition-all cursor-pointer"
                >
                    Retry
                </button>
            </div>
        );
    }

    if (!thesis) {
        return (
            <div className="p-12 text-center rounded-2xl bg-panel border border-panel-line flex flex-col items-center justify-center min-h-[360px] space-y-6">
                <div className="w-16 h-16 rounded-2xl bg-teal/10 border border-teal/30 flex items-center justify-center text-teal">
                    <Sparkles className="w-8 h-8" />
                </div>
                <div className="max-w-md space-y-2">
                    <h4 className="text-xl font-display font-semibold text-ink">No Research Thesis Available Yet</h4>
                    <p className="text-sm text-ink-mute">
                        A fundamental investment thesis for <span className="font-mono text-teal font-semibold">{ticker}</span> has not been generated yet. Click below to trigger the ReAct Research Agent.
                    </p>
                </div>
                <button
                    onClick={() => handleTriggerThesis()}
                    disabled={submittingNotes}
                    className="px-6 py-3 bg-teal text-black font-bold rounded-xl label-caps hover:bg-teal/80 transition-all flex items-center gap-2 cursor-pointer shadow-lg disabled:opacity-50"
                >
                    {submittingNotes ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                    <span>Generate Fundamental Research Thesis</span>
                </button>
            </div>
        );
    }

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            {toastMsg && (
                <div className={`p-4 rounded-xl border flex items-center justify-between transition-all ${
                    toastMsg.type === 'success' ? 'bg-bull/10 border-bull/30 text-bull' :
                    toastMsg.type === 'error' ? 'bg-bear/10 border-bear/30 text-bear' :
                    'bg-teal/10 border-teal/30 text-teal'
                }`}>
                    <span className="text-sm font-medium flex items-center gap-2">
                        {toastMsg.type === 'success' ? <CheckCircle2 className="w-4 h-4" /> :
                         toastMsg.type === 'error' ? <AlertTriangle className="w-4 h-4" /> :
                         <Info className="w-4 h-4" />}
                        {toastMsg.text}
                    </span>
                    <button onClick={() => setToastMsg(null)} className="opacity-70 hover:opacity-100 p-1">
                        <X className="w-4 h-4" />
                    </button>
                </div>
            )}

            {/* Header Toolbar */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 p-6 rounded-2xl bg-[var(--color-panel-sunk)] border border-panel-line shadow-inner">
                <div className="space-y-2">
                    <div className="flex items-center gap-3 flex-wrap">
                        <h3 className="text-3xl font-display font-bold text-ink">{thesis.ticker}</h3>
                        <span className="text-ink-mute text-lg font-medium">| {thesis.company_name}</span>
                        {/* Scope Badge */}
                        <span className={`px-3 py-1 rounded-full text-xs font-bold font-mono uppercase flex items-center gap-1.5 border ${
                            thesis.scope === 'personalized'
                                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                                : 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30'
                        }`}>
                            {thesis.scope === 'personalized' ? <UserCheck className="w-3.5 h-3.5" /> : <Globe className="w-3.5 h-3.5" />}
                            <span>{thesis.scope === 'personalized' ? 'Personalized Thesis' : 'Baseline Thesis'}</span>
                        </span>
                    </div>
                    <p className="text-xs text-ink-dim font-mono">
                        Generated: {new Date(thesis.generated_at).toLocaleString()} | Trigger: {thesis.source_trigger}
                    </p>
                </div>

                {/* Quick Action Controls */}
                <div className="flex items-center gap-2 flex-wrap">
                    <button
                        onClick={() => setShowPersonalizeModal(true)}
                        className="px-3.5 py-2 bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/20 rounded-xl label-caps transition-all flex items-center gap-1.5 text-xs font-semibold cursor-pointer"
                    >
                        <Edit3 className="w-3.5 h-3.5" /> Personalize
                    </button>
                    {thesis.scope === 'personalized' && (
                        <button
                            onClick={handleFetchBaselineComparison}
                            className="px-3.5 py-2 bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 hover:bg-cyan-500/20 rounded-xl label-caps transition-all flex items-center gap-1.5 text-xs font-semibold cursor-pointer"
                        >
                            <GitCompare className="w-3.5 h-3.5" /> Compare Baseline
                        </button>
                    )}
                    <button
                        onClick={handleFetchHistory}
                        className="px-3.5 py-2 bg-[var(--color-panel-sunk)] text-ink-mute border border-panel-line hover:text-white hover:border-teal rounded-xl label-caps transition-all flex items-center gap-1.5 text-xs font-semibold cursor-pointer"
                    >
                        <History className="w-3.5 h-3.5" /> History
                    </button>
                    <button
                        onClick={() => handleTriggerThesis()}
                        disabled={submittingNotes}
                        title="Re-run research agent for baseline refresh"
                        className="px-3 py-2 bg-teal/10 text-teal border border-teal/30 hover:bg-teal/20 rounded-xl transition-all disabled:opacity-50 cursor-pointer"
                    >
                        <RefreshCw className={`w-3.5 h-3.5 ${submittingNotes ? "animate-spin" : ""}`} />
                    </button>
                </div>
            </div>

            {/* Headline Conviction Banner */}
            <div className="p-6 rounded-2xl bg-gradient-to-r from-teal/15 via-teal/5 to-transparent border border-teal/30 relative overflow-hidden shadow-lg">
                <div className="flex items-start gap-4">
                    <div className="w-12 h-12 rounded-xl bg-teal/20 border border-teal/40 flex items-center justify-center text-teal shrink-0 mt-0.5">
                        <Sparkles className="w-6 h-6" />
                    </div>
                    <div className="space-y-1.5">
                        <div className="flex items-center gap-3">
                            <span className="text-xs font-mono font-bold uppercase text-teal tracking-wider">AI Fundamental Conviction</span>
                            <span className="text-xs font-mono text-ink-dim">Confidence: {(thesis.confidence_level).toFixed(0)}%</span>
                        </div>
                        <h4 className="text-xl md:text-2xl font-display font-semibold text-ink leading-snug">
                            &ldquo;{thesis.headline_view}&rdquo;
                        </h4>
                        {thesis.user_notes && (
                            <p className="text-xs font-mono text-emerald-400 pt-2 border-t border-teal/20 flex items-center gap-1.5">
                                <Edit3 className="w-3.5 h-3.5 shrink-0" /> User Notes Applied: &ldquo;{thesis.user_notes}&rdquo;
                            </p>
                        )}
                    </div>
                </div>
            </div>

            {/* Fundamental Pillars Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Pillar 1: Business Viability */}
                <div className="p-6 rounded-2xl bg-panel border border-panel-line space-y-3 shadow-md">
                    <div className="flex items-center gap-2 text-teal">
                        <Layers className="w-4 h-4" />
                        <h5 className="text-xs font-mono font-bold uppercase tracking-wider text-ink-dim">Business Viability</h5>
                    </div>
                    <p className="text-sm font-body text-ink leading-relaxed">
                        {thesis.business_viability_summary || "No viability summary available."}
                    </p>
                </div>

                {/* Pillar 2: Competitive Moat */}
                <div className="p-6 rounded-2xl bg-panel border border-panel-line space-y-3 shadow-md">
                    <div className="flex items-center gap-2 text-teal">
                        <ShieldAlert className="w-4 h-4" />
                        <h5 className="text-xs font-mono font-bold uppercase tracking-wider text-ink-dim">Competitive Moat</h5>
                    </div>
                    <p className="text-sm font-body text-ink leading-relaxed">
                        {thesis.competitive_landscape_summary || "No competitive moat analysis available."}
                    </p>
                </div>

                {/* Pillar 3: Macro Context */}
                <div className="p-6 rounded-2xl bg-panel border border-panel-line space-y-3 shadow-md">
                    <div className="flex items-center gap-2 text-teal">
                        <Globe className="w-4 h-4" />
                        <h5 className="text-xs font-mono font-bold uppercase tracking-wider text-ink-dim">Macro Context</h5>
                    </div>
                    <p className="text-sm font-body text-ink leading-relaxed">
                        {thesis.macro_context_summary || "No macro context summary available."}
                    </p>
                </div>
            </div>

            {/* Bull vs. Bear Investment Case Comparison */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Bull Investment Case */}
                <div className="p-6 rounded-2xl bg-bull/5 border border-bull/30 space-y-4 shadow-lg">
                    <div className="flex items-center gap-2.5 text-bull border-b border-bull/20 pb-3">
                        <TrendingUp className="w-5 h-5" />
                        <h4 className="text-lg font-display font-semibold">Fundamental Bull Case</h4>
                    </div>
                    <p className="text-sm font-body text-ink leading-relaxed whitespace-pre-line">
                        {thesis.bull_case || "No bull case documented."}
                    </p>
                </div>

                {/* Bear Investment Case */}
                <div className="p-6 rounded-2xl bg-bear/5 border border-bear/30 space-y-4 shadow-lg">
                    <div className="flex items-center gap-2.5 text-bear border-b border-bear/20 pb-3">
                        <TrendingDown className="w-5 h-5" />
                        <h4 className="text-lg font-display font-semibold">Fundamental Bear Case</h4>
                    </div>
                    <p className="text-sm font-body text-ink leading-relaxed whitespace-pre-line">
                        {thesis.bear_case || "No bear case documented."}
                    </p>
                </div>
            </div>

            {/* Catalyst Calendar & Risk Register */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Catalyst Calendar */}
                <div className="p-6 rounded-2xl bg-panel border border-panel-line space-y-4 shadow-md">
                    <div className="flex items-center gap-2 text-teal border-b border-panel-line pb-3">
                        <Calendar className="w-4 h-4" />
                        <h5 className="text-xs font-mono font-bold uppercase tracking-wider text-ink-dim">Key Catalysts</h5>
                    </div>
                    {thesis.catalysts && thesis.catalysts.length > 0 ? (
                        <ul className="space-y-2">
                            {thesis.catalysts.map((cat, idx) => (
                                <li key={idx} className="flex items-start gap-2.5 text-sm text-ink font-body">
                                    <span className="w-1.5 h-1.5 rounded-full bg-teal shrink-0 mt-2" />
                                    <span>{cat}</span>
                                </li>
                            ))}
                        </ul>
                    ) : (
                        <p className="text-xs text-ink-dim italic">No catalysts documented.</p>
                    )}
                </div>

                {/* Risk Register */}
                <div className="p-6 rounded-2xl bg-panel border border-panel-line space-y-4 shadow-md">
                    <div className="flex items-center gap-2 text-bear border-b border-panel-line pb-3">
                        <ShieldAlert className="w-4 h-4" />
                        <h5 className="text-xs font-mono font-bold uppercase tracking-wider text-ink-dim">Risk Register</h5>
                    </div>
                    {thesis.risks && thesis.risks.length > 0 ? (
                        <ul className="space-y-2">
                            {thesis.risks.map((risk, idx) => (
                                <li key={idx} className="flex items-start gap-2.5 text-sm text-ink font-body">
                                    <span className="w-1.5 h-1.5 rounded-full bg-bear shrink-0 mt-2" />
                                    <span>{risk}</span>
                                </li>
                            ))}
                        </ul>
                    ) : (
                        <p className="text-xs text-ink-dim italic">No risks documented.</p>
                    )}
                </div>
            </div>

            {/* Evidence Matrix Table */}
            {thesis.evidence_table && thesis.evidence_table.length > 0 && (
                <div className="p-6 rounded-2xl bg-panel border border-panel-line space-y-4 shadow-lg overflow-hidden">
                    <div className="flex items-center gap-2 text-teal border-b border-panel-line pb-3">
                        <Table className="w-4 h-4" />
                        <h5 className="text-xs font-mono font-bold uppercase tracking-wider text-ink-dim">Multi-Source Evidence Matrix</h5>
                    </div>
                    <div className="overflow-x-auto custom-scrollbar">
                        <table className="w-full text-left text-xs font-body">
                            <thead>
                                <tr className="border-b border-panel-line text-ink-dim font-mono uppercase font-bold">
                                    <th className="py-2.5 px-3">Evidence Item</th>
                                    <th className="py-2.5 px-3">Source Data</th>
                                    <th className="py-2.5 px-3">Implication</th>
                                    <th className="py-2.5 px-3">Weight</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-panel-line">
                                {thesis.evidence_table.map((item, idx) => (
                                    <tr key={idx} className="hover:bg-white/5 transition-colors">
                                        <td className="py-3 px-3 text-ink font-medium">{item.evidence}</td>
                                        <td className="py-3 px-3 font-mono text-teal">{item.source}</td>
                                        <td className="py-3 px-3">
                                            <span className={`px-2 py-0.5 rounded font-mono font-bold text-[10px] uppercase ${
                                                item.implication === 'Positive' ? 'bg-bull/10 text-bull border border-bull/20' :
                                                item.implication === 'Negative' ? 'bg-bear/10 text-bear border border-bear/20' :
                                                'bg-ink-dim/10 text-ink-mute'
                                            }`}>
                                                {item.implication}
                                            </span>
                                        </td>
                                        <td className="py-3 px-3 font-mono text-ink-dim uppercase">{item.weight}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* Personalization Modal */}
            {showPersonalizeModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in duration-200">
                    <div className="bg-[#0e1524] border border-panel-line rounded-2xl w-full max-w-lg p-6 shadow-2xl space-y-6 text-white">
                        <div className="flex justify-between items-center border-b border-panel-line pb-4">
                            <h4 className="text-xl font-display font-semibold text-white flex items-center gap-2">
                                <Edit3 className="w-5 h-5 text-emerald-400" /> Personalize Research Thesis
                            </h4>
                            <button
                                onClick={() => setShowPersonalizeModal(false)}
                                className="text-ink-mute hover:text-white p-1 rounded-lg hover:bg-white/5 transition-colors cursor-pointer"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        <form onSubmit={(e) => { e.preventDefault(); handleTriggerThesis(userNotesInput); }} className="space-y-4">
                            <div>
                                <label className="block text-xs font-mono font-bold uppercase text-ink-dim mb-1">
                                    Custom Analyst Notes / Strategic Focus
                                </label>
                                <textarea
                                    rows={4}
                                    placeholder="e.g. Focus on Azure Blackwell GPU capacity constraints and sovereign AI demand in Q4..."
                                    value={userNotesInput}
                                    onChange={(e) => setUserNotesInput(e.target.value)}
                                    className="w-full px-4 py-3 bg-[var(--color-panel-sunk)] border border-panel-line rounded-xl text-white font-body text-sm focus:border-emerald-400 outline-none transition-colors custom-scrollbar"
                                />
                            </div>

                            <div className="flex justify-end gap-3 pt-4 border-t border-panel-line">
                                <button
                                    type="button"
                                    onClick={() => setShowPersonalizeModal(false)}
                                    className="px-4 py-2 bg-[var(--color-panel-sunk)] border border-panel-line rounded-xl label-caps text-ink-mute hover:text-white transition-all cursor-pointer"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    disabled={submittingNotes || !userNotesInput.trim()}
                                    className="px-5 py-2 bg-emerald-500 text-black font-bold rounded-xl label-caps hover:bg-emerald-400 transition-all flex items-center gap-2 cursor-pointer disabled:opacity-50"
                                >
                                    {submittingNotes && <RefreshCw className="w-4 h-4 animate-spin" />}
                                    Generate Personalized Thesis
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Compare Baseline Modal */}
            {showBaselineModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 animate-in fade-in duration-200">
                    <div className="bg-[#0e1524] border border-panel-line rounded-2xl w-full max-w-4xl max-h-[90vh] p-6 shadow-2xl space-y-6 text-white overflow-y-auto custom-scrollbar">
                        <div className="flex justify-between items-center border-b border-panel-line pb-4">
                            <h4 className="text-xl font-display font-semibold text-white flex items-center gap-2">
                                <GitCompare className="w-5 h-5 text-cyan-400" /> Side-by-Side Thesis Comparison ({ticker})
                            </h4>
                            <button
                                onClick={() => setShowBaselineModal(false)}
                                className="text-ink-mute hover:text-white p-1 rounded-lg hover:bg-white/5 transition-colors cursor-pointer"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        {loadingBaseline ? (
                            <div className="p-12 text-center text-ink-mute flex items-center justify-center gap-2">
                                <RefreshCw className="w-5 h-5 animate-spin text-cyan-400" /> Loading baseline thesis...
                            </div>
                        ) : baselineThesis ? (
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm">
                                {/* Left: User Personalized */}
                                <div className="p-4 rounded-xl bg-emerald-500/5 border border-emerald-500/30 space-y-3">
                                    <div className="flex items-center justify-between border-b border-emerald-500/20 pb-2">
                                        <span className="font-mono font-bold text-xs text-emerald-400 uppercase">Your Personalized Thesis</span>
                                        <span className="text-[10px] font-mono text-ink-dim">Confidence: {(thesis.confidence_level).toFixed(0)}%</span>
                                    </div>
                                    <h5 className="font-display font-semibold text-ink text-base">&ldquo;{thesis.headline_view}&rdquo;</h5>
                                    <p className="text-xs text-ink-mute"><strong>Viability:</strong> {thesis.business_viability_summary}</p>
                                    <p className="text-xs text-ink-mute"><strong>Moat:</strong> {thesis.competitive_landscape_summary}</p>
                                </div>

                                {/* Right: Shared Baseline */}
                                <div className="p-4 rounded-xl bg-cyan-500/5 border border-cyan-500/30 space-y-3">
                                    <div className="flex items-center justify-between border-b border-cyan-500/20 pb-2">
                                        <span className="font-mono font-bold text-xs text-cyan-400 uppercase">Shared Baseline Thesis</span>
                                        <span className="text-[10px] font-mono text-ink-dim">Confidence: {(baselineThesis.confidence_level).toFixed(0)}%</span>
                                    </div>
                                    <h5 className="font-display font-semibold text-ink text-base">&ldquo;{baselineThesis.headline_view}&rdquo;</h5>
                                    <p className="text-xs text-ink-mute"><strong>Viability:</strong> {baselineThesis.business_viability_summary}</p>
                                    <p className="text-xs text-ink-mute"><strong>Moat:</strong> {baselineThesis.competitive_landscape_summary}</p>
                                </div>
                            </div>
                        ) : (
                            <p className="text-sm text-ink-mute">No baseline thesis found for comparison.</p>
                        )}
                    </div>
                </div>
            )}

            {/* History Drawer */}
            {showHistoryDrawer && (
                <div className="fixed inset-0 z-50 flex items-center justify-end bg-black/75 backdrop-blur-sm p-4 animate-in fade-in duration-200">
                    <div className="bg-[#0e1524] border-l border-panel-line rounded-2xl w-full max-w-md h-full p-6 shadow-2xl space-y-6 text-white overflow-y-auto custom-scrollbar flex flex-col">
                        <div className="flex justify-between items-center border-b border-panel-line pb-4">
                            <h4 className="text-xl font-display font-semibold text-white flex items-center gap-2">
                                <History className="w-5 h-5 text-teal" /> Research Thesis History
                            </h4>
                            <button
                                onClick={() => setShowHistoryDrawer(false)}
                                className="text-ink-mute hover:text-white p-1 rounded-lg hover:bg-white/5 transition-colors cursor-pointer"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        {loadingHistory ? (
                            <div className="p-12 text-center text-ink-mute flex items-center justify-center gap-2">
                                <RefreshCw className="w-5 h-5 animate-spin text-teal" /> Loading history...
                            </div>
                        ) : historyData && historyData.history.length > 0 ? (
                            <div className="space-y-4 flex-1">
                                {historyData.history.map((item) => (
                                    <div
                                        key={item.id}
                                        onClick={() => { setThesis(item); setShowHistoryDrawer(false); }}
                                        className="p-4 rounded-xl bg-panel border border-panel-line hover:border-teal/50 transition-all cursor-pointer space-y-2"
                                    >
                                        <div className="flex items-center justify-between">
                                            <span className={`px-2 py-0.5 rounded font-mono text-[10px] uppercase border ${
                                                item.scope === 'personalized' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' : 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30'
                                            }`}>
                                                {item.scope}
                                            </span>
                                            <span className="text-[10px] font-mono text-ink-dim">
                                                {new Date(item.generated_at).toLocaleDateString()}
                                            </span>
                                        </div>
                                        <h5 className="font-display font-semibold text-ink text-sm leading-snug line-clamp-2">
                                            &ldquo;{item.headline_view}&rdquo;
                                        </h5>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <p className="text-sm text-ink-mute">No thesis history available.</p>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
