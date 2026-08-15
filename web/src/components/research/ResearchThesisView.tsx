"use client";

import { useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { api, ResearchThesis, ResearchHistoryResponse } from "@/lib/api";
import { useResearchThesis, invalidateThesis } from "./useResearchThesis";
import SectionCard from "@/components/ui/SectionCard";
import SectionHeader from "@/components/ui/SectionHeader";
import { Prose, ProseLead, ProseList, ProseEmpty } from "@/components/ui/Prose";
import { ACCENTS, cx } from "@/components/ui/accents";
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
    Info,
    ArrowRight
} from "lucide-react";

/**
 * The horizon this whole view speaks to. The research thesis and the earnings
 * debate both produce a "Bull Case" in the same green; this is what separates
 * a 12–36 month structural view from a single-quarter call.
 */
const THESIS_HORIZON = "12–36 mo";

/**
 * Personalized-vs-baseline scope marker. Appears in the toolbar, the comparison
 * modal and the history drawer, so the accent mapping lives in one place:
 * personalized reads as `bull`, baseline as `teal` (previously raw emerald-500
 * and cyan-500, which sat one shade off the design tokens on the same screen).
 */
function ScopeBadge({
    scope,
    icon,
    label,
    className,
}: {
    scope: string;
    icon?: React.ReactNode;
    label?: string;
    className?: string;
}) {
    const a = ACCENTS[scope === "personalized" ? "bull" : "teal"];
    return (
        <span
            className={cx(
                "eyebrow px-2.5 py-1 rounded-full border inline-flex items-center gap-1.5 select-none",
                "[&>svg]:w-3.5 [&>svg]:h-3.5",
                a.chipBg,
                a.chipBorder,
                a.text,
                className
            )}
        >
            {icon}
            <span>{label ?? scope}</span>
        </span>
    );
}

/**
 * Evidence weight is an ordinal HIGH / MEDIUM / LOW, so it reads faster as
 * filled segments than as a word — and the filled count sorts visually when
 * scanning a stack of evidence entries.
 *
 * An unrecognised value still renders its own label with no segments filled,
 * rather than silently showing an empty meter.
 */
const WEIGHT_STEPS: Record<string, number> = { LOW: 1, MEDIUM: 2, MED: 2, HIGH: 3 };

function WeightMeter({ weight }: { weight?: string | null }) {
    const label = (weight ?? "").trim();
    const filled = WEIGHT_STEPS[label.toUpperCase()] ?? 0;
    const tone = filled >= 3 ? ACCENTS.research : filled === 2 ? ACCENTS.teal : ACCENTS.neutral;

    return (
        <span className="flex items-center gap-2 shrink-0" title={label ? `Weight: ${label}` : undefined}>
            <span className="eyebrow text-ink-dim">Weight</span>
            <span className="flex items-center gap-1" aria-hidden="true">
                {[0, 1, 2].map((i) => (
                    <span
                        key={i}
                        className={cx(
                            "w-4 h-1 rounded-full",
                            i < filled ? tone.dot : "bg-white/10"
                        )}
                    />
                ))}
            </span>
            <span className={cx("eyebrow", filled ? tone.text : "text-ink-dim")}>
                {label || "—"}
            </span>
        </span>
    );
}

export type ResearchThesisVariant = "full" | "summary";

export default function ResearchThesisView({
    ticker,
    variant = "full",
    onOpenFull,
}: {
    ticker: string;
    /**
     * `full` is the standalone research tab: identity header, toolbar, pillars,
     * catalysts, risks and the evidence matrix.
     *
     * `summary` is the condensed block embedded in the prediction tab. It drops
     * the identity header and toolbar — the page above it already establishes
     * which company this is — and shows only the conviction and the pillars,
     * with a link through to the full view.
     */
    variant?: ResearchThesisVariant;
    /** Invoked by the summary variant's "Open full thesis" control. */
    onOpenFull?: () => void;
}) {
    const { getToken } = useAuth();
    const isSummary = variant === "summary";
    // Shared across both mounts, so switching tabs no longer refetches.
    const { thesis, setThesis, loading, error, refetch: fetchThesis } = useResearchThesis(ticker);

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

    const handleTriggerThesis = async (notes?: string) => {
        setSubmittingNotes(true);
        setToastMsg(null);
        try {
            const token = (await getToken()) || undefined;
            const res = await api.triggerResearch(ticker, notes, token);
            // A new thesis is being generated, so the cached one is now stale;
            // drop it so any later mount refetches instead of serving it.
            invalidateThesis(ticker);
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
            <SectionCard accent="research" className="flex flex-col items-center justify-center gap-4 min-h-[320px] text-center">
                <RefreshCw className="w-8 h-8 text-research animate-spin" />
                <p className="eyebrow text-ink-mute">Loading fundamental research thesis for {ticker}…</p>
            </SectionCard>
        );
    }

    if (error) {
        return (
            <SectionCard accent="bear" className="flex items-center justify-between gap-4 flex-wrap">
                <div className="flex items-center gap-3 text-bear">
                    <AlertTriangle className="w-5 h-5 shrink-0" />
                    <span className="prose-body">{error}</span>
                </div>
                <button
                    onClick={fetchThesis}
                    className="px-4 py-2 bg-bear/15 hover:bg-bear/25 text-bear border border-bear/30 rounded-xl eyebrow transition-all cursor-pointer"
                >
                    Retry
                </button>
            </SectionCard>
        );
    }

    if (!thesis) {
        return (
            <SectionCard accent="research" className="flex flex-col items-center justify-center gap-5 min-h-[360px] text-center">
                <span className="w-14 h-14 rounded-2xl bg-research/12 border border-research/28 flex items-center justify-center text-research">
                    <Sparkles className="w-7 h-7" />
                </span>
                <div className="max-w-md flex flex-col gap-2">
                    <h4 className="prose-lead text-ink">No research thesis yet</h4>
                    <p className="prose-body text-ink-mute">
                        No fundamental thesis has been generated for{" "}
                        <span className="font-mono text-research">{ticker}</span> yet. Generating one
                        runs the research agent over filings, market data and company profile.
                    </p>
                </div>
                <button
                    onClick={() => handleTriggerThesis()}
                    disabled={submittingNotes}
                    className="px-5 py-2.5 bg-research text-black rounded-xl eyebrow hover:bg-research/80 transition-all flex items-center gap-2 cursor-pointer disabled:opacity-50"
                >
                    {submittingNotes ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                    <span>Generate research thesis</span>
                </button>
            </SectionCard>
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

            {/* Identity header and toolbar. Suppressed in the summary variant —
                the prediction page above it already names the company, and
                repeating it put the ticker on screen three times. */}
            {!isSummary && (
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 p-6 rounded-2xl bg-[var(--color-panel-sunk)] border border-panel-line shadow-inner">
                <div className="flex flex-col gap-2">
                    <div className="flex items-center gap-3 flex-wrap">
                        <h3 className="text-3xl font-display font-semibold text-ink">{thesis.ticker}</h3>
                        <span className="prose-body text-ink-mute">{thesis.company_name}</span>
                        <ScopeBadge
                            scope={thesis.scope}
                            icon={thesis.scope === 'personalized' ? <UserCheck /> : <Globe />}
                            label={thesis.scope === 'personalized' ? 'Personalized Thesis' : 'Baseline Thesis'}
                        />
                    </div>
                    <p className="eyebrow text-ink-dim">
                        Generated {new Date(thesis.generated_at).toLocaleString()} · via {thesis.source_trigger}
                    </p>
                </div>

                {/* Quick Action Controls */}
                <div className="flex items-center gap-2 flex-wrap">
                    <button
                        onClick={() => setShowPersonalizeModal(true)}
                        className="px-3.5 py-2 bg-bull/10 text-bull border border-bull/30 hover:bg-bull/20 rounded-xl eyebrow transition-all flex items-center gap-1.5 cursor-pointer"
                    >
                        <Edit3 className="w-3.5 h-3.5" /> Personalize
                    </button>
                    {thesis.scope === 'personalized' && (
                        <button
                            onClick={handleFetchBaselineComparison}
                            className="px-3.5 py-2 bg-teal/10 text-teal border border-teal/30 hover:bg-teal/20 rounded-xl eyebrow transition-all flex items-center gap-1.5 cursor-pointer"
                        >
                            <GitCompare className="w-3.5 h-3.5" /> Compare Baseline
                        </button>
                    )}
                    <button
                        onClick={handleFetchHistory}
                        className="px-3.5 py-2 bg-[var(--color-panel-sunk)] text-ink-mute border border-panel-line hover:text-white hover:border-teal rounded-xl eyebrow transition-all flex items-center gap-1.5 cursor-pointer"
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
            )}

            {/* Headline Conviction */}
            <SectionCard accent="research">
                <SectionHeader
                    accent="research"
                    icon={<Sparkles />}
                    eyebrow="AI Fundamental Conviction"
                    horizon={THESIS_HORIZON}
                    as="h3"
                    actions={
                        <div className="flex items-center gap-2.5 flex-wrap">
                            {/* The summary variant has no toolbar, so scope rides here. */}
                            {isSummary && <ScopeBadge scope={thesis.scope} />}
                            <span className="eyebrow text-ink-dim">
                                Confidence {(thesis.confidence_level).toFixed(0)}%
                            </span>
                        </div>
                    }
                />
                <ProseLead className="mt-4">&ldquo;{thesis.headline_view}&rdquo;</ProseLead>
                {thesis.user_notes && (
                    <p className={cx("prose-list text-bull mt-4 pt-3 border-t flex items-start gap-2", ACCENTS.research.rule)}>
                        <Edit3 className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                        <span>User notes applied: &ldquo;{thesis.user_notes}&rdquo;</span>
                    </p>
                )}
            </SectionCard>

            {/* Fundamental Pillars — rank-3 sub-sections of the thesis */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {[
                    { icon: <Layers />, label: "Business Viability",
                      body: thesis.business_viability_summary, empty: "No viability summary available." },
                    { icon: <ShieldAlert />, label: "Competitive Moat",
                      body: thesis.competitive_landscape_summary, empty: "No competitive moat analysis available." },
                    { icon: <Globe />, label: "Macro Context",
                      body: thesis.macro_context_summary, empty: "No macro context summary available." },
                ].map((pillar) => (
                    <SectionCard key={pillar.label} accent="research" density="compact">
                        <SectionHeader accent="research" icon={pillar.icon} eyebrow={pillar.label} muted as="h4" />
                        {pillar.body
                            ? <Prose className="mt-3">{pillar.body}</Prose>
                            : <div className="mt-3"><ProseEmpty>{pillar.empty}</ProseEmpty></div>}
                    </SectionCard>
                ))}
            </div>

            {/* Everything below is the full view only. The summary stops at the
                conviction and the three pillars, then hands off to the research
                tab — which is what keeps the prediction page readable. */}
            {isSummary && (
                <div className="flex justify-end">
                    <button
                        type="button"
                        onClick={onOpenFull}
                        className="px-4 py-2 bg-research/10 text-research border border-research/30 hover:bg-research/20 rounded-xl eyebrow transition-all flex items-center gap-2 cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-research/40"
                    >
                        <span>Open full thesis</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                </div>
            )}

            {!isSummary && (
              <>
            {/* Bull vs. Bear structural case. Same accents as the earnings debate's
                own bull/bear cards, so the horizon chip is what tells them apart. */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <SectionCard accent="bull">
                    <SectionHeader
                        accent="bull"
                        icon={<TrendingUp />}
                        eyebrow="Bull Case"
                        horizon={THESIS_HORIZON}
                        as="h4"
                        divider
                    />
                    {thesis.bull_case
                        ? <Prose className="mt-4">{thesis.bull_case}</Prose>
                        : <div className="mt-4"><ProseEmpty>No bull case documented.</ProseEmpty></div>}
                </SectionCard>

                <SectionCard accent="bear">
                    <SectionHeader
                        accent="bear"
                        icon={<TrendingDown />}
                        eyebrow="Bear Case"
                        horizon={THESIS_HORIZON}
                        as="h4"
                        divider
                    />
                    {thesis.bear_case
                        ? <Prose className="mt-4">{thesis.bear_case}</Prose>
                        : <div className="mt-4"><ProseEmpty>No bear case documented.</ProseEmpty></div>}
                </SectionCard>
            </div>

            {/* Catalyst Calendar & Risk Register */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <SectionCard accent="neutral">
                    <SectionHeader accent="teal" icon={<Calendar />} eyebrow="Key Catalysts" muted as="h4" divider />
                    <ProseList
                        items={thesis.catalysts ?? []}
                        accent="teal"
                        empty="No catalysts documented."
                        className="mt-4"
                    />
                </SectionCard>

                <SectionCard accent="neutral">
                    <SectionHeader accent="bear" icon={<ShieldAlert />} eyebrow="Risk Register" muted as="h4" divider />
                    <ProseList
                        items={thesis.risks ?? []}
                        accent="bear"
                        empty="No risks documented."
                        className="mt-4"
                    />
                </SectionCard>
            </div>

            {/* Evidence Matrix Table */}
            {thesis.evidence_table && thesis.evidence_table.length > 0 && (
                <SectionCard accent="neutral">
                    <SectionHeader
                        accent="research"
                        icon={<Table />}
                        eyebrow="Multi-Source Evidence Matrix"
                        muted
                        as="h4"
                        divider
                    />
                    {/* Stacked rather than tabular. `evidence` and `implication` are
                        both full sentences from the model, so four columns squeezed
                        each to a few characters wide and forced the panel to scroll
                        sideways. Stacking gives every field the page's normal
                        measure and reading format. */}
                    <div className="mt-4 flex flex-col gap-3">
                        {thesis.evidence_table.map((item, idx) => (
                            <div
                                key={idx}
                                className="rounded-xl border border-panel-line bg-[var(--color-panel-sunk)] p-4 flex flex-col gap-3 hover:border-research/30 transition-colors"
                            >
                                {/* Source + weight share a line: both are short, and
                                    together they say where this came from and how
                                    much it counts. */}
                                <div className="flex items-center justify-between gap-3 flex-wrap">
                                    <div className="flex items-baseline gap-2.5 min-w-0">
                                        <span className="eyebrow text-ink-dim shrink-0">Source</span>
                                        <span className="font-mono text-[13px] text-teal truncate">{item.source}</span>
                                    </div>
                                    <WeightMeter weight={item.weight} />
                                </div>

                                <div>
                                    <span className="eyebrow text-ink-dim">Evidence</span>
                                    <p className="prose-body text-ink mt-1">{item.evidence}</p>
                                </div>

                                <div>
                                    <span className="eyebrow text-ink-dim">Implication</span>
                                    <p className="prose-body text-ink-mute mt-1">{item.implication}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </SectionCard>
            )}
              </>
            )}

            {/* Personalization Modal */}
            {showPersonalizeModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in duration-200">
                    <div className="bg-[#0e1524] border border-panel-line rounded-2xl w-full max-w-lg p-6 shadow-2xl space-y-6 text-white">
                        <div className="flex justify-between items-center border-b border-panel-line pb-4">
                            <h4 className="text-xl font-display font-semibold text-white flex items-center gap-2">
                                <Edit3 className="w-5 h-5 text-bull" /> Personalize Research Thesis
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
                                <label className="block eyebrow text-ink-dim mb-1">
                                    Custom Analyst Notes / Strategic Focus
                                </label>
                                <textarea
                                    rows={4}
                                    placeholder="e.g. Focus on Azure Blackwell GPU capacity constraints and sovereign AI demand in Q4..."
                                    value={userNotesInput}
                                    onChange={(e) => setUserNotesInput(e.target.value)}
                                    className="w-full px-4 py-3 bg-[var(--color-panel-sunk)] border border-panel-line rounded-xl text-white font-body text-sm focus:border-bull outline-none transition-colors custom-scrollbar"
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
                                    className="px-5 py-2 bg-bull text-black rounded-xl eyebrow hover:bg-bull/80 transition-all flex items-center gap-2 cursor-pointer disabled:opacity-50"
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
                                <GitCompare className="w-5 h-5 text-teal" /> Side-by-Side Thesis Comparison ({ticker})
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
                                <RefreshCw className="w-5 h-5 animate-spin text-teal" /> Loading baseline thesis...
                            </div>
                        ) : baselineThesis ? (
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                {[
                                    { key: "personalized", t: thesis, label: "Your Personalized Thesis", icon: <UserCheck /> },
                                    { key: "baseline", t: baselineThesis, label: "Shared Baseline Thesis", icon: <Globe /> },
                                ].map(({ key, t, label, icon }) => (
                                    <SectionCard
                                        key={key}
                                        accent={key === "personalized" ? "bull" : "teal"}
                                        density="compact"
                                    >
                                        <SectionHeader
                                            accent={key === "personalized" ? "bull" : "teal"}
                                            icon={icon}
                                            eyebrow={label}
                                            as="h5"
                                            divider
                                            actions={
                                                <span className="eyebrow text-ink-dim">
                                                    Confidence {(t.confidence_level).toFixed(0)}%
                                                </span>
                                            }
                                        />
                                        <p className="prose-body text-ink mt-3">&ldquo;{t.headline_view}&rdquo;</p>
                                        <dl className="mt-3 flex flex-col gap-2">
                                            <div>
                                                <dt className="eyebrow text-ink-dim">Viability</dt>
                                                <dd className="prose-list text-ink-mute mt-0.5">{t.business_viability_summary}</dd>
                                            </div>
                                            <div>
                                                <dt className="eyebrow text-ink-dim">Moat</dt>
                                                <dd className="prose-list text-ink-mute mt-0.5">{t.competitive_landscape_summary}</dd>
                                            </div>
                                        </dl>
                                    </SectionCard>
                                ))}
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
                                    <button
                                        key={item.id}
                                        type="button"
                                        onClick={() => { setThesis(item); setShowHistoryDrawer(false); }}
                                        className="w-full text-left p-4 rounded-xl bg-panel border border-panel-line hover:border-teal/50 focus-visible:border-teal outline-none transition-all cursor-pointer flex flex-col gap-2"
                                    >
                                        <div className="flex items-center justify-between gap-2">
                                            <ScopeBadge scope={item.scope} className="text-[10px]" />
                                            <span className="eyebrow text-[10px] text-ink-dim">
                                                {new Date(item.generated_at).toLocaleDateString()}
                                            </span>
                                        </div>
                                        <span className="prose-body text-ink line-clamp-2">
                                            &ldquo;{item.headline_view}&rdquo;
                                        </span>
                                    </button>
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
