"use client";

import { useState, useRef, useEffect } from "react";
import { useAuth } from "@clerk/nextjs";
import { api, Prediction } from "@/lib/api";
import ResearchThesisView from "@/components/research/ResearchThesisView";
import SectionCard from "@/components/ui/SectionCard";
import SectionHeader from "@/components/ui/SectionHeader";
import { Prose, ProseList } from "@/components/ui/Prose";
import { ACCENTS } from "@/components/ui/accents";
import { 
    FileText, 
    FileDown, 
    Zap, 
    TrendingUp, 
    TrendingDown, 
    BarChart3, 
    User, 
    Sparkles, 
    Eye, 
    MessageSquare, 
    Bot, 
    AlertTriangle,
    Send,
    RefreshCw,
    Edit3,
    CheckCircle2,
    X,
    Layers
} from "lucide-react";

export default function AnalysisResult({ result }: { result: Prediction }) {
    const { getToken } = useAuth();
    const [currentResult, setCurrentResult] = useState<Prediction>(result);
    const [activeTab, setActiveTab] = useState<'prediction' | 'research' | 'chat'>('prediction');
    useEffect(() => {
        setCurrentResult(result);
    }, [result]);

    const [chatMessages, setChatMessages] = useState<{ role: string, content: string }[]>([]);
    const [chatInput, setChatInput] = useState("");
    const [chatLoading, setChatLoading] = useState(false);
    const chatEndRef = useRef<HTMLDivElement>(null);
    const [downloading, setDownloading] = useState(false);
    const [verifying, setVerifying] = useState(false);
    const [showEditModal, setShowEditModal] = useState(false);
    const [savingOverride, setSavingOverride] = useState(false);
    const [toastMsg, setToastMsg] = useState<{ text: string; type: "success" | "error" } | null>(null);

    // Form state for manual override modal
    const [expEpsInput, setExpEpsInput] = useState<string>("");
    const [actEpsInput, setActEpsInput] = useState<string>("");
    const [actMoveInput, setActMoveInput] = useState<string>("");
    const [actDirInput, setActDirInput] = useState<string>("BEAT");
    const [actGuidanceInput, setActGuidanceInput] = useState<string>("REAFFIRMED");

    const handleDownload = async (format: 'md' | 'pdf') => {
        if (!currentResult.id) return;
        setDownloading(true);
        try {
            const token = await getToken() || undefined;
            await api.downloadReport(currentResult.id, format, currentResult.ticker, token);
        } catch (err: any) {
            alert(`Failed to download report: ${err.message}`);
        } finally {
            setDownloading(false);
        }
    };

    const handleReverify = async () => {
        if (!currentResult.id) return;
        setVerifying(true);
        setToastMsg(null);
        try {
            const token = (await getToken()) || undefined;
            const res = await api.verifyPrediction(currentResult.id, token, true);
            if (res && res.prediction) {
                setCurrentResult(res.prediction);
            } else if (res && res.result) {
                setCurrentResult(prev => ({
                    ...prev,
                    expected_eps: res.result.expected_eps ?? prev.expected_eps,
                    actual_direction: res.result.actual_direction ?? prev.actual_direction,
                    actual_eps: res.result.actual_eps ?? prev.actual_eps,
                    actual_price_move_pct: res.result.actual_price_move_pct ?? prev.actual_price_move_pct,
                    accuracy_score: res.result.accuracy_score ?? prev.accuracy_score,
                    composite_accuracy_score: res.result.composite_accuracy_score ?? prev.composite_accuracy_score
                }));
            }
            setToastMsg({ text: "Outcome successfully verified & updated!", type: "success" });
        } catch (err: any) {
            setToastMsg({ text: `Re-verification failed: ${err.message}`, type: "error" });
        } finally {
            setVerifying(false);
        }
    };

    const handleOpenEditModal = () => {
        setExpEpsInput(currentResult.expected_eps != null ? String(currentResult.expected_eps) : "");
        setActEpsInput(currentResult.actual_eps != null ? String(currentResult.actual_eps) : "");
        setActMoveInput(currentResult.actual_price_move_pct != null ? String((currentResult.actual_price_move_pct * 100).toFixed(2)) : "");
        setActDirInput(currentResult.actual_direction ? currentResult.actual_direction.toUpperCase() : "BEAT");
        setActGuidanceInput(currentResult.actual_guidance_stance || "REAFFIRMED");
        setShowEditModal(true);
    };

    const handleSaveOverride = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!currentResult.id) return;
        setSavingOverride(true);
        setToastMsg(null);
        try {
            const token = (await getToken()) || undefined;
            const payload: any = {};
            if (expEpsInput.trim() !== "") payload.expected_eps = parseFloat(expEpsInput);
            if (actEpsInput.trim() !== "") payload.actual_eps = parseFloat(actEpsInput);
            if (actMoveInput.trim() !== "") payload.actual_price_move_pct = parseFloat(actMoveInput) / 100.0;
            if (actDirInput.trim() !== "") payload.actual_direction = actDirInput.trim().toUpperCase();
            if (actGuidanceInput.trim() !== "") payload.actual_guidance_stance = actGuidanceInput.trim().toUpperCase();

            const res = await api.overridePredictionActuals(currentResult.id, payload, token);
            if (res && res.prediction) {
                setCurrentResult(res.prediction);
            }
            setToastMsg({ text: "Actual numbers updated successfully!", type: "success" });
            setShowEditModal(false);
        } catch (err: any) {
            setToastMsg({ text: `Failed to update actuals: ${err.message}`, type: "error" });
        } finally {
            setSavingOverride(false);
        }
    };


    const parseDebate = (summary?: string) => {
        if (!summary) return { bull: null, bear: null, quant: null, user: null };
        const parts = summary.split(/\n(?=(?:BULL |BEAR |QUANT |ANALYST \(USER\):|CONSENSUS ))/);
        let bull = null, bear = null, quant = null, user = null;
        for (let p of parts) {
            p = p.trim();
            if (p.startsWith("BULL (")) {
                const idx = p.indexOf('):\n');
                if (idx !== -1) bull = p.substring(idx + 3).trim();
            } else if (p.startsWith("BEAR (")) {
                const idx = p.indexOf('):\n');
                if (idx !== -1) bear = p.substring(idx + 3).trim();
            } else if (p.startsWith("QUANT (")) {
                const idx = p.indexOf('):\n');
                if (idx !== -1) quant = p.substring(idx + 3).trim();
            } else if (p.startsWith("ANALYST (USER):")) {
                const idx = p.indexOf(':\n');
                if (idx !== -1) user = p.substring(idx + 2).trim();
            }
        }
        return { bull, bear, quant, user };
    };

    const { bull: bullSummary, bear: bearSummary, quant: quantSummary, user: userSummary } = parseDebate(result.debate_summary);

    useEffect(() => {
        if (chatMessages.length > 0) {
            chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
        }
    }, [chatMessages]);

    const handleSendChatMessage = async () => {
        if (!chatInput.trim() || !result) return;

        const currentMessages = [...chatMessages];
        const userText = chatInput.trim();
        const newUserMsg = { role: "user", content: userText };

        setChatMessages([...currentMessages, newUserMsg]);
        setChatInput("");
        setChatLoading(true);

        try {
            const token = await getToken() || undefined;

            // Send the entire context on the first message
            let messagesToSend = [...currentMessages, newUserMsg];
            if (currentMessages.length === 0) {
                messagesToSend = [{
                    role: "user",
                    content: `Context: We are discussing your recent earnings prediction for ${result.ticker} (${result.company_name}).
Your Prediction: ${result.direction} (Confidence: ${(result.confidence * 100).toFixed(0)}%)
Reasoning: ${result.reasoning_summary}
Debate Summary: ${result.debate_summary}

User Question:
${userText}`
                }];
            }

            const chatRes = await api.chatWithConsensus(result.ticker, messagesToSend, undefined, token);

            if (chatRes && chatRes.response) {
                setChatMessages([...currentMessages, newUserMsg, { role: "model", content: chatRes.response }]);
            } else {
                setChatMessages([...currentMessages, newUserMsg, { role: "model", content: "⚠️ No response received from Consensus Agent." }]);
            }

        } catch (err: any) {
            setChatMessages([...currentMessages, newUserMsg, { role: "model", content: "⚠️ Error contacting Consensus Agent: " + err.message }]);
        } finally {
            setChatLoading(false);
        }
    };

    return (
        <div className="flex-1 bg-panel p-6 md:p-12 rounded-[16px] border border-panel-line shadow-[0_20px_60px_rgba(0,0,0,0.35)] animate-in fade-in slide-in-from-bottom-4 duration-700">
            <div className="flex justify-between items-start mb-8 pb-8 border-b border-panel-line">
                <div>
                    <div className="flex items-center gap-4 mb-2.5">
                        <h3 className="text-4xl font-display font-semibold text-ink">{currentResult.ticker}</h3>
                        <span className={`px-4 py-1.5 rounded-full label-caps
                            ${currentResult.direction === 'BEAT' ? 'bg-bull/10 text-bull border border-bull/30' :
                                currentResult.direction === 'MISS' ? 'bg-bear/10 text-bear border border-bear/30' :
                                    'bg-ink-dim/10 text-ink-mute border border-ink-dim/30'}
                        `}>
                            {currentResult.direction}
                        </span>
                    </div>
                    <p className="text-ink-mute label-caps">{currentResult.company_name}</p>
                </div>
                <div className="flex flex-col items-end gap-2.5 text-right">
                    <div className="label-caps text-ink-dim">AI Confidence</div>
                    <div className="text-5xl font-display font-semibold text-ink font-data">
                        {(currentResult.confidence * 100).toFixed(0)}%
                    </div>
                    {currentResult.id && (
                        <div className="flex flex-wrap gap-2 mt-2 justify-end">
                            <button
                                onClick={handleReverify}
                                disabled={verifying}
                                title="Re-verify outcome data against financial data providers"
                                className="px-3.5 py-2 bg-teal/10 text-teal border border-teal/30 hover:bg-teal/20 rounded-lg label-caps transition-all disabled:opacity-50 flex items-center gap-1.5 cursor-pointer outline-none"
                            >
                                <RefreshCw className={`w-3.5 h-3.5 ${verifying ? "animate-spin" : ""}`} /> Re-verify
                            </button>
                            <button
                                onClick={handleOpenEditModal}
                                title="Manually input or override actual numbers in the DB"
                                className="px-3.5 py-2 bg-research/10 text-research border border-research/30 hover:bg-research/20 rounded-lg eyebrow transition-all flex items-center gap-1.5 cursor-pointer outline-none"
                            >
                                <Edit3 className="w-3.5 h-3.5" /> Edit Actuals
                            </button>
                            <button
                                onClick={() => handleDownload('md')}
                                disabled={downloading}
                                className="px-3.5 py-2 bg-[var(--color-panel-sunk)] border border-panel-line rounded-lg label-caps text-ink-mute hover:text-teal hover:border-teal hover:bg-panel-line transition-all disabled:opacity-50 flex items-center gap-1.5 cursor-pointer outline-none"
                            >
                                <FileText className="w-3.5 h-3.5" /> MD
                            </button>
                            <button
                                onClick={() => handleDownload('pdf')}
                                disabled={downloading}
                                className="px-3.5 py-2 bg-[var(--color-panel-sunk)] border border-panel-line rounded-lg label-caps text-ink-mute hover:text-teal hover:border-teal hover:bg-panel-line transition-all disabled:opacity-50 flex items-center gap-1.5 cursor-pointer outline-none"
                            >
                                <FileDown className="w-3.5 h-3.5" /> PDF
                            </button>
                        </div>
                    )}
                </div>
            </div>

            {/* Multi-Tab Navigation Bar */}
            <div className="flex items-center gap-3 mb-8 border-b border-panel-line pb-4 overflow-x-auto custom-scrollbar select-none">
                <button
                    onClick={() => setActiveTab('prediction')}
                    className={`px-5 py-2.5 rounded-xl label-caps text-xs font-semibold transition-all flex items-center gap-2 cursor-pointer ${
                        activeTab === 'prediction'
                            ? 'bg-teal text-black shadow-lg font-bold'
                            : 'bg-[var(--color-panel-sunk)] text-ink-mute hover:text-white border border-panel-line'
                    }`}
                >
                    <Zap className="w-4 h-4" /> Earnings Prediction &amp; Debate
                </button>

                <button
                    onClick={() => setActiveTab('research')}
                    className={`px-5 py-2.5 rounded-xl label-caps text-xs font-semibold transition-all flex items-center gap-2 cursor-pointer ${
                        activeTab === 'research'
                            ? 'bg-teal text-black shadow-lg font-bold'
                            : 'bg-[var(--color-panel-sunk)] text-ink-mute hover:text-white border border-panel-line'
                    }`}
                >
                    <Sparkles className="w-4 h-4" /> Fundamental Research Thesis
                </button>

                <button
                    onClick={() => setActiveTab('chat')}
                    className={`px-5 py-2.5 rounded-xl label-caps text-xs font-semibold transition-all flex items-center gap-2 cursor-pointer ${
                        activeTab === 'chat'
                            ? 'bg-teal text-black shadow-lg font-bold'
                            : 'bg-[var(--color-panel-sunk)] text-ink-mute hover:text-white border border-panel-line'
                    }`}
                >
                    <MessageSquare className="w-4 h-4" /> Interactive AI Research Chat
                </button>
            </div>

            {toastMsg && (
                <div className={`mb-6 p-4 rounded-xl border flex items-center justify-between transition-all ${
                    toastMsg.type === 'success' 
                        ? 'bg-bull/10 border-bull/30 text-bull' 
                        : 'bg-bear/10 border-bear/30 text-bear'
                }`}>
                    <span className="text-sm font-medium flex items-center gap-2">
                        {toastMsg.type === 'success' ? <CheckCircle2 className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
                        {toastMsg.text}
                    </span>
                    <button onClick={() => setToastMsg(null)} className="opacity-70 hover:opacity-100 p-1">
                        <X className="w-4 h-4" />
                    </button>
                </div>
            )}

            {/* TAB 1: PREDICTION & DEBATE */}
            {activeTab === 'prediction' && (
                <div className="space-y-12 animate-in fade-in duration-300">
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-4">
                        <div className="p-5 bg-[var(--color-panel-sunk)] rounded-xl border border-panel-line flex flex-col items-center justify-center text-center shadow-inner">
                            <span className="label-caps text-ink-dim mb-1">Expected EPS</span>
                            <span className="text-lg font-display font-semibold text-ink font-data">
                                {currentResult.expected_eps !== undefined && currentResult.expected_eps !== null ? `$${currentResult.expected_eps.toFixed(2)}` : "—"}
                            </span>
                        </div>
                        <div className="p-5 bg-[var(--color-panel-sunk)] rounded-xl border border-panel-line flex flex-col items-center justify-center text-center shadow-inner">
                            <span className="label-caps text-ink-dim mb-1">Actual EPS</span>
                            <span className="text-lg font-display font-semibold text-ink font-data">
                                {currentResult.actual_eps !== undefined && currentResult.actual_eps !== null ? `$${currentResult.actual_eps.toFixed(2)}` : "—"}
                            </span>
                        </div>
                        <div className="p-5 bg-[var(--color-panel-sunk)] rounded-xl border border-panel-line flex flex-col items-center justify-center text-center shadow-inner">
                            <span className="label-caps text-ink-dim mb-1">Expected Move</span>
                            <span className="text-lg font-display font-semibold text-ink capitalize">{currentResult.expected_price_move || "Pending"}</span>
                        </div>
                        <div className="p-5 bg-[var(--color-panel-sunk)] rounded-xl border border-panel-line flex flex-col items-center justify-center text-center shadow-inner">
                            <span className="label-caps text-ink-dim mb-1">Actual Move</span>
                            <span className={`text-lg font-display font-semibold font-data ${currentResult.actual_price_move_pct !== undefined && currentResult.actual_price_move_pct !== null ? (currentResult.actual_price_move_pct >= 0 ? "text-bull" : "text-bear") : "text-ink"}`}>
                                {currentResult.actual_price_move_pct !== undefined && currentResult.actual_price_move_pct !== null
                                    ? `${currentResult.actual_price_move_pct >= 0 ? "+" : ""}${(currentResult.actual_price_move_pct * 100).toFixed(2)}%`
                                    : "—"}
                            </span>
                        </div>
                        <div className="p-5 bg-[var(--color-panel-sunk)] rounded-xl border border-panel-line flex flex-col items-center justify-center text-center shadow-inner">
                            <span className="label-caps text-ink-dim mb-1">Move vs Implied</span>
                            <span className="text-lg font-display font-semibold text-ink capitalize">{currentResult.move_vs_implied || "Pending"}</span>
                        </div>
                        <div className="p-5 bg-[var(--color-panel-sunk)] rounded-xl border border-panel-line flex flex-col items-center justify-center text-center shadow-inner">
                            <span className="label-caps text-ink-dim mb-1">Guidance</span>
                            <span className="text-lg font-display font-semibold text-ink capitalize">{currentResult.guidance_expectation || "Pending"}</span>
                        </div>
                    </div>

                    {result.likely_guidance && (
                        <div className="p-8 rounded-2xl border border-panel-line bg-[var(--color-panel-sunk)] shadow-inner">
                            <div className="flex items-center gap-3.5 mb-4">
                                <div className="w-8 h-8 rounded-full bg-teal/10 flex items-center justify-center border border-teal/20">
                                    <Eye className="w-4 h-4 text-teal" />
                                </div>
                                <p className="label-caps text-teal">Expected Guidance Outlook</p>
                            </div>
                            <p className="prose-body text-ink-mute">
                                {result.likely_guidance}
                            </p>
                        </div>
                    )}

                    {result.options_features && (
                        <div className="p-8 rounded-2xl border border-teal/20 bg-teal/5 shadow-inner">
                            <div className="flex items-center gap-3.5 mb-5">
                                <div className="w-8 h-8 rounded-full bg-teal/20 flex items-center justify-center border border-teal/30">
                                    <Zap className="w-4 h-4 text-teal" />
                                </div>
                                <p className="label-caps text-teal">Options Market Signals</p>
                            </div>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                                <div className="p-6 bg-[var(--color-panel-sunk)] rounded-xl border border-panel-line flex flex-col justify-center text-center">
                                    <span className="label-caps text-ink-dim mb-1.5">Implied Move</span>
                                    <span className="text-lg font-display font-semibold text-ink font-data">
                                        {result.options_features.implied_move_pct != null
                                            ? `${(result.options_features.implied_move_pct * 100).toFixed(1)}%` 
                                            : "—"}
                                    </span>
                                </div>
                                <div className="p-6 bg-[var(--color-panel-sunk)] rounded-xl border border-panel-line flex flex-col justify-center text-center">
                                    <span className="label-caps text-ink-dim mb-1.5">Put/Call Vol Ratio</span>
                                    <span className="text-lg font-display font-semibold text-ink font-data">
                                        {result.options_features.put_call_volume_ratio != null
                                            ? result.options_features.put_call_volume_ratio.toFixed(2) 
                                            : "—"}
                                    </span>
                                </div>
                                <div className="p-6 bg-[var(--color-panel-sunk)] rounded-xl border border-panel-line flex flex-col justify-center text-center">
                                    <span className="label-caps text-ink-dim mb-1.5">Implied Vol (ATM IV)</span>
                                    <span className="text-lg font-display font-semibold text-ink font-data">
                                        {result.options_features.atm_iv_call != null
                                            ? `${(result.options_features.atm_iv_call * 100).toFixed(1)}%` 
                                            : "—"}
                                    </span>
                                </div>
                                <div className="p-6 bg-[var(--color-panel-sunk)] rounded-xl border border-panel-line flex flex-col justify-center text-center">
                                    <span className="label-caps text-ink-dim mb-1.5">IV Skew (Puts - Calls)</span>
                                    <span className="text-lg font-display font-semibold text-ink font-data">
                                        {result.options_features.iv_skew != null
                                            ? `${(result.options_features.iv_skew * 100).toFixed(1)}%` 
                                            : "—"}
                                    </span>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Sequential Agent Case Cards — the near-term debate */}
                    <div className="flex flex-col gap-8">
                        {/* Bull Case */}
                        <SectionCard accent="bull" interactive>
                            <SectionHeader
                                accent="bull"
                                icon={<TrendingUp />}
                                eyebrow="Bull Case"
                                horizon="This quarter"
                                divider={!!bullSummary}
                            />
                            {bullSummary && (
                                <Prose className={`mt-4 pb-5 mb-5 border-b ${ACCENTS.bull.rule}`}>
                                    {bullSummary}
                                </Prose>
                            )}
                            <ProseList
                                items={result.bull_factors ?? []}
                                accent="bull"
                                marker="check"
                                empty="No significant bullish factors identified in this analysis."
                                className={bullSummary ? undefined : "mt-4"}
                            />
                        </SectionCard>

                        {/* Bear Case */}
                        <SectionCard accent="bear" interactive>
                            <SectionHeader
                                accent="bear"
                                icon={<TrendingDown />}
                                eyebrow="Bear Case"
                                horizon="This quarter"
                                divider={!!bearSummary}
                            />
                            {bearSummary && (
                                <Prose className={`mt-4 pb-5 mb-5 border-b ${ACCENTS.bear.rule}`}>
                                    {bearSummary}
                                </Prose>
                            )}
                            <ProseList
                                items={result.bear_factors ?? []}
                                accent="bear"
                                marker="cross"
                                empty="No significant bearish factors identified in this analysis."
                                className={bearSummary ? undefined : "mt-4"}
                            />
                        </SectionCard>

                        {/* Quant Case */}
                        {quantSummary && (
                            <SectionCard accent="quant" interactive>
                                <SectionHeader
                                    accent="quant"
                                    icon={<BarChart3 />}
                                    eyebrow="Quant Case"
                                    horizon="This quarter"
                                />
                                <Prose className="mt-4">{quantSummary}</Prose>
                            </SectionCard>
                        )}

                        {/* Analyst Case / Custom Research */}
                        {userSummary && (
                            <SectionCard accent="human" interactive>
                                <SectionHeader
                                    accent="human"
                                    icon={<User />}
                                    eyebrow="Analyst / User Insight"
                                />
                                <Prose className="mt-4">{userSummary}</Prose>
                            </SectionCard>
                        )}

                        {/* Rebuttals / Cross-Examination */}
                        {result.rebuttal_summary && (
                            <SectionCard accent="rebuttal" interactive>
                                <SectionHeader
                                    accent="rebuttal"
                                    icon={<AlertTriangle />}
                                    eyebrow="Rebuttals & Cross-Examination"
                                />
                                <Prose className="mt-4">{result.rebuttal_summary}</Prose>
                            </SectionCard>
                        )}

                        {/* Consensus Summary */}
                        <SectionCard accent="neutral" className="relative overflow-hidden">
                            <div className="absolute top-0 left-0 w-1 h-full bg-teal" aria-hidden="true" />
                            <SectionHeader
                                accent="teal"
                                icon={<Sparkles />}
                                eyebrow="Consensus Summary"
                                as="h3"
                            />
                            <Prose className="mt-4">{result.reasoning_summary}</Prose>
                        </SectionCard>
                    </div>

                    {/* Structural view. Sits after the near-term debate rather than
                        interrupting it: the page answers "what happens at this print?"
                        before "is this a good business?". Condensed, with a handoff to
                        the full thesis tab. */}
                    <div id="research-thesis-section" className="flex flex-col gap-4">
                        <SectionHeader
                            accent="research"
                            icon={<Sparkles />}
                            eyebrow="Structural View"
                            subtitle="Fundamental research thesis · business viability, moat, evidence"
                            as="h3"
                        />
                        <ResearchThesisView
                            ticker={currentResult.ticker}
                            variant="summary"
                            onOpenFull={() => setActiveTab('research')}
                        />
                    </div>
                </div>
            )}

            {/* TAB 2: FUNDAMENTAL RESEARCH THESIS */}
            {activeTab === 'research' && (
                <div className="animate-in fade-in duration-300">
                    <ResearchThesisView ticker={currentResult.ticker} />
                </div>
            )}

            {/* TAB 3: INTERACTIVE AI RESEARCH CHAT */}
            {activeTab === 'chat' && (
                <div className="p-8 rounded-2xl border border-panel-line bg-[var(--color-panel-sunk)] shadow-inner flex flex-col flex-1 min-h-[550px] animate-in fade-in duration-300">
                    <div className="flex justify-between items-center mb-6">
                        <h4 className="label-caps text-teal flex items-center gap-2 select-none text-base">
                            <MessageSquare className="w-4 h-4 text-teal" /> Interactive AI Analyst Chat ({currentResult.ticker})
                        </h4>
                        <span className="text-xs font-mono text-ink-dim">Powered by Consensus &amp; Research Thesis Context</span>
                    </div>

                    {/* Suggested Prompt Chips */}
                    <div className="flex items-center gap-2 mb-6 flex-wrap select-none">
                        <span className="text-xs font-mono text-ink-dim uppercase mr-1">Suggested:</span>
                        <button
                            onClick={() => setChatInput("What are the primary competitive risks to this company's moat over the next 2-3 years?")}
                            className="px-3 py-1.5 bg-panel border border-panel-line hover:border-teal/50 rounded-lg text-xs font-body text-ink-mute hover:text-teal transition-all cursor-pointer"
                        >
                            Primary Competitive Moat Risks?
                        </button>
                        <button
                            onClick={() => setChatInput("How does the Research Agent weigh the Bull case against high CapEx spending?")}
                            className="px-3 py-1.5 bg-panel border border-panel-line hover:border-teal/50 rounded-lg text-xs font-body text-ink-mute hover:text-teal transition-all cursor-pointer"
                        >
                            Bull Case vs CapEx Spending?
                        </button>
                        <button
                            onClick={() => setChatInput("Summarize upcoming catalysts and timing from the fundamental research thesis.")}
                            className="px-3 py-1.5 bg-panel border border-panel-line hover:border-teal/50 rounded-lg text-xs font-body text-ink-mute hover:text-teal transition-all cursor-pointer"
                        >
                            Upcoming Catalysts &amp; Timing?
                        </button>
                    </div>

                    <div className="flex-1 overflow-y-auto mb-6 space-y-4 pr-2 custom-scrollbar min-h-[300px]">
                        {chatMessages.length === 0 ? (
                            <div className="flex flex-col items-center justify-center h-full opacity-50 py-12 select-none">
                                <Bot className="w-12 h-12 mb-4 text-teal animate-bounce" style={{ animationDuration: '3s' }} />
                                <p className="label-caps text-ink-mute text-sm">No chat messages yet.</p>
                                <p className="text-xs text-ink-dim mt-2 text-center max-w-sm">
                                    Ask questions about short-term earnings expectations or fundamental research thesis moats for {currentResult.ticker}.
                                </p>
                            </div>
                        ) : (
                            chatMessages.map((msg, idx) => (
                                <div key={idx} className={`p-5 rounded-xl text-sm ${msg.role === 'user' ? 'bg-panel text-ink ml-8 border border-panel-line' : 'bg-teal/10 text-ink mr-8 border border-teal/20'}`}>
                                    <div className={`label-caps mb-2 select-none ${msg.role === 'user' ? 'text-ink-dim' : 'text-teal'}`}>
                                        {msg.role === 'user' ? 'You' : 'Consensus Analyst'}
                                    </div>
                                    <div className="whitespace-pre-wrap font-body font-normal leading-[1.6]">{msg.content}</div>
                                </div>
                            ))
                        )}
                        {chatLoading && (
                            <div className="p-4 rounded-xl bg-teal/10 text-teal mr-8 border border-teal/20 flex items-center gap-3 w-fit select-none">
                                <span className="animate-pulse w-2 h-2 bg-teal rounded-full"></span>
                                <span className="animate-pulse label-caps">Thinking...</span>
                            </div>
                        )}
                        <div ref={chatEndRef} />
                    </div>

                    <div className="relative flex items-end bg-panel border border-panel-line focus-within:border-teal/50 focus-within:ring-1 focus-within:ring-teal/20 rounded-xl transition-all p-2 gap-2 mt-auto">
                        <textarea
                            placeholder={`Ask questions about ${currentResult.ticker} prediction or research thesis...`}
                            value={chatInput}
                            onChange={(e) => setChatInput(e.target.value)}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter' && !e.shiftKey) {
                                    e.preventDefault();
                                    handleSendChatMessage();
                                }
                            }}
                            className="flex-1 bg-transparent border-0 outline-none focus:ring-0 text-sm font-body font-normal text-ink placeholder-ink-dim/40 resize-none min-h-[48px] max-h-[160px] py-3 px-3 custom-scrollbar"
                            disabled={chatLoading}
                        />
                        <button
                            onClick={handleSendChatMessage}
                            disabled={chatLoading || !chatInput.trim()}
                            className="h-11 px-5 rounded-lg label-caps transition-all bg-teal text-[var(--color-bg)] hover:bg-teal-deep disabled:opacity-30 disabled:cursor-not-allowed flex items-center gap-2 cursor-pointer shadow-md select-none shrink-0"
                        >
                            <span>Send</span>
                            <Send className="w-3.5 h-3.5" />
                        </button>
                    </div>
                </div>
            )}

            {/* Edit Actuals Modal */}
            {showEditModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in duration-200">
                    <div className="bg-[#0e1524] border border-panel-line rounded-2xl w-full max-w-lg p-6 shadow-2xl space-y-6 text-white">
                        <div className="flex justify-between items-center border-b border-panel-line pb-4">
                            <h4 className="text-xl font-display font-semibold text-white flex items-center gap-2">
                                <Edit3 className="w-5 h-5 text-teal" /> Edit Actual Outcome Data
                            </h4>
                            <button
                                onClick={() => setShowEditModal(false)}
                                className="text-ink-mute hover:text-white p-1 rounded-lg hover:bg-white/5 transition-colors cursor-pointer"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        <form onSubmit={handleSaveOverride} className="space-y-4">
                            <div>
                                <label className="block eyebrow text-ink-dim mb-1">
                                    Expected Consensus EPS ($)
                                </label>
                                <input
                                    type="number"
                                    step="0.01"
                                    placeholder="e.g. 1.25"
                                    value={expEpsInput}
                                    onChange={(e) => setExpEpsInput(e.target.value)}
                                    className="w-full px-4 py-2.5 bg-[var(--color-panel-sunk)] border border-panel-line rounded-xl text-white font-mono text-sm focus:border-teal outline-none transition-colors"
                                />
                            </div>

                            <div>
                                <label className="block eyebrow text-ink-dim mb-1">
                                    Actual Reported EPS ($)
                                </label>
                                <input
                                    type="number"
                                    step="0.01"
                                    placeholder="e.g. 1.50"
                                    value={actEpsInput}
                                    onChange={(e) => setActEpsInput(e.target.value)}
                                    className="w-full px-4 py-2.5 bg-[var(--color-panel-sunk)] border border-panel-line rounded-xl text-white font-mono text-sm focus:border-teal outline-none transition-colors"
                                />
                            </div>

                            <div>
                                <label className="block eyebrow text-ink-dim mb-1">
                                    Post-Earnings Price Move (%)
                                </label>
                                <input
                                    type="number"
                                    step="0.01"
                                    placeholder="e.g. 5.2 (for +5.2%)"
                                    value={actMoveInput}
                                    onChange={(e) => setActMoveInput(e.target.value)}
                                    className="w-full px-4 py-2.5 bg-[var(--color-panel-sunk)] border border-panel-line rounded-xl text-white font-mono text-sm focus:border-teal outline-none transition-colors"
                                />
                            </div>

                            <div>
                                <label className="block eyebrow text-ink-dim mb-1">
                                    Actual Direction
                                </label>
                                <select
                                    value={actDirInput}
                                    onChange={(e) => setActDirInput(e.target.value)}
                                    className="w-full px-4 py-2.5 bg-[var(--color-panel-sunk)] border border-panel-line rounded-xl text-white font-mono text-sm focus:border-teal outline-none transition-colors"
                                >
                                    <option value="BEAT">BEAT (Reported &gt; Estimate)</option>
                                    <option value="MISS">MISS (Reported &lt; Estimate)</option>
                                    <option value="MEET">MEET (In-line with Estimate)</option>
                                </select>
                            </div>

                            <div>
                                <label className="block eyebrow text-ink-dim mb-1">
                                    Actual Guidance Stance
                                </label>
                                <select
                                    value={actGuidanceInput}
                                    onChange={(e) => setActGuidanceInput(e.target.value)}
                                    className="w-full px-4 py-2.5 bg-[var(--color-panel-sunk)] border border-panel-line rounded-xl text-white font-mono text-sm focus:border-teal outline-none transition-colors"
                                >
                                    <option value="RAISED">RAISED (Strong / Upward guidance)</option>
                                    <option value="LOWERED">LOWERED (Cut / Downward guidance)</option>
                                    <option value="REAFFIRMED">REAFFIRMED (Maintained / In-line guidance)</option>
                                </select>
                            </div>

                            <div className="flex justify-end gap-3 pt-4 border-t border-panel-line">
                                <button
                                    type="button"
                                    onClick={() => setShowEditModal(false)}
                                    className="px-4 py-2 bg-[var(--color-panel-sunk)] border border-panel-line rounded-xl label-caps text-ink-mute hover:text-white transition-all cursor-pointer"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    disabled={savingOverride}
                                    className="px-5 py-2 bg-teal text-black font-bold rounded-xl label-caps hover:bg-teal/80 transition-all flex items-center gap-2 cursor-pointer disabled:opacity-50"
                                >
                                    {savingOverride && <RefreshCw className="w-4 h-4 animate-spin" />}
                                    Save Actuals &amp; Update DB
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
