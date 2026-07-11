"use client";

import { useState, useRef, useEffect } from "react";
import { useAuth } from "@clerk/nextjs";
import { api, Prediction } from "@/lib/api";
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
    Send
} from "lucide-react";

export default function AnalysisResult({ result }: { result: Prediction }) {
    const { getToken } = useAuth();
    const [chatMessages, setChatMessages] = useState<{ role: string, content: string }[]>([]);
    const [chatInput, setChatInput] = useState("");
    const [chatLoading, setChatLoading] = useState(false);
    const chatEndRef = useRef<HTMLDivElement>(null);
    const [downloading, setDownloading] = useState(false);

    const handleDownload = async (format: 'md' | 'pdf') => {
        if (!result.id) return;
        setDownloading(true);
        try {
            const token = await getToken() || undefined;
            await api.downloadReport(result.id, format, result.ticker, token);
        } catch (err: any) {
            alert(`Failed to download report: ${err.message}`);
        } finally {
            setDownloading(false);
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
            <div className="flex justify-between items-start mb-12 pb-8 border-b border-panel-line">
                <div>
                    <div className="flex items-center gap-4 mb-2.5">
                        <h3 className="text-4xl font-display font-semibold text-ink">{result.ticker}</h3>
                        <span className={`px-4 py-1.5 rounded-full label-caps
                            ${result.direction === 'BEAT' ? 'bg-bull/10 text-bull border border-bull/30' :
                                result.direction === 'MISS' ? 'bg-bear/10 text-bear border border-bear/30' :
                                    'bg-ink-dim/10 text-ink-mute border border-ink-dim/30'}
                        `}>
                            {result.direction}
                        </span>
                    </div>
                    <p className="text-ink-mute label-caps">{result.company_name}</p>
                </div>
                <div className="flex flex-col items-end gap-2.5 text-right">
                    <div className="label-caps text-ink-dim">AI Confidence</div>
                    <div className="text-5xl font-display font-semibold text-ink font-data">
                        {(result.confidence * 100).toFixed(0)}%
                    </div>
                    {result.id && (
                        <div className="flex gap-2 mt-2">
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

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
                <div className="p-6 bg-[var(--color-panel-sunk)] rounded-xl border border-panel-line flex flex-col items-center justify-center text-center shadow-inner">
                    <span className="label-caps text-ink-dim mb-1">Expected Price Move</span>
                    <span className="text-lg font-display font-semibold text-ink capitalize">{result.expected_price_move || "Pending"}</span>
                </div>
                <div className="p-6 bg-[var(--color-panel-sunk)] rounded-xl border border-panel-line flex flex-col items-center justify-center text-center shadow-inner">
                    <span className="label-caps text-ink-dim mb-1">Move vs Implied</span>
                    <span className="text-lg font-display font-semibold text-ink capitalize">{result.move_vs_implied || "Pending"}</span>
                </div>
                <div className="p-6 bg-[var(--color-panel-sunk)] rounded-xl border border-panel-line flex flex-col items-center justify-center text-center shadow-inner">
                    <span className="label-caps text-ink-dim mb-1">Guidance Expectation</span>
                    <span className="text-lg font-display font-semibold text-ink capitalize">{result.guidance_expectation || "Pending"}</span>
                </div>
            </div>

            {result.likely_guidance && (
                <div className="mb-12 p-8 rounded-2xl border border-panel-line bg-[var(--color-panel-sunk)] shadow-inner">
                    <div className="flex items-center gap-3.5 mb-4">
                        <div className="w-8 h-8 rounded-full bg-teal/10 flex items-center justify-center border border-teal/20">
                            <Eye className="w-4 h-4 text-teal" />
                        </div>
                        <p className="label-caps text-teal">Expected Guidance Outlook</p>
                    </div>
                    <p className="text-sm font-body font-normal text-ink-mute leading-[1.7]">
                        {result.likely_guidance}
                    </p>
                </div>
            )}

            {result.options_features && (
                <div className="mb-12 p-8 rounded-2xl border border-teal/20 bg-teal/5 shadow-inner">
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

            {/* Sequential Agent Case Cards */}
            <div className="flex flex-col gap-12 mb-12">
                {/* Bull Case */}
                <div className="p-8 bg-bull/[0.02] rounded-2xl border border-bull/15 hover:border-bull/25 hover:bg-bull/[0.04] transition-all duration-200 shadow-sm flex flex-col">
                    <div className="flex items-center gap-3 mb-5 select-none">
                        <div className="w-8 h-8 rounded-full bg-bull/10 flex items-center justify-center border border-bull/20">
                            <TrendingUp className="w-4 h-4 text-bull" />
                        </div>
                        <p className="label-caps text-bull">Bull Case</p>
                    </div>
                    {bullSummary && (
                        <p className="text-[15px] font-body font-normal text-ink-mute leading-[1.7] whitespace-pre-line mb-6 pb-6 border-b border-bull/10">
                            {bullSummary}
                        </p>
                    )}
                    <ul className="space-y-4">
                        {result.bull_factors && result.bull_factors.length > 0 ? (
                            result.bull_factors.map((f, i) => (
                                <li key={i} className="text-sm font-body font-normal text-ink-mute flex items-start gap-3 leading-[1.6]">
                                    <span className="text-bull mt-0.5 font-bold">✓</span> <span>{f}</span>
                                </li>
                            ))
                        ) : (
                            <li className="text-sm text-ink-dim italic flex items-center justify-center p-4">No significant bullish factors identified in this analysis.</li>
                        )}
                    </ul>
                </div>

                {/* Bear Case */}
                <div className="p-8 bg-bear/[0.02] rounded-2xl border border-bear/15 hover:border-bear/25 hover:bg-bear/[0.04] transition-all duration-200 shadow-sm flex flex-col">
                    <div className="flex items-center gap-3 mb-5 select-none">
                        <div className="w-8 h-8 rounded-full bg-bear/10 flex items-center justify-center border border-bear/20">
                            <TrendingDown className="w-4 h-4 text-bear" />
                        </div>
                        <p className="label-caps text-bear">Bear Case</p>
                    </div>
                    {bearSummary && (
                        <p className="text-[15px] font-body font-normal text-ink-mute leading-[1.7] whitespace-pre-line mb-6 pb-6 border-b border-bear/10">
                            {bearSummary}
                        </p>
                    )}
                    <ul className="space-y-4">
                        {result.bear_factors && result.bear_factors.length > 0 ? (
                            result.bear_factors.map((f, i) => (
                                <li key={i} className="text-sm font-body font-normal text-ink-mute flex items-start gap-3 leading-[1.6]">
                                    <span className="text-bear mt-0.5 font-bold">×</span> <span>{f}</span>
                                </li>
                            ))
                        ) : (
                            <li className="text-sm text-ink-dim italic flex items-center justify-center p-4">No significant bearish factors identified in this analysis.</li>
                        )}
                    </ul>
                </div>

                {/* Quant Case */}
                {quantSummary && (
                    <div className="p-8 bg-quant/[0.02] rounded-2xl border border-quant/15 hover:border-quant/25 hover:bg-quant/[0.04] transition-all duration-200 shadow-sm flex flex-col">
                        <div className="flex items-center gap-3 mb-5 select-none">
                            <div className="w-8 h-8 rounded-full bg-quant/10 flex items-center justify-center border border-quant/20">
                                <BarChart3 className="w-4 h-4 text-quant" />
                            </div>
                            <p className="label-caps text-quant">Quant Case</p>
                        </div>
                        <p className="text-[15px] font-body font-normal text-ink-mute leading-[1.7] whitespace-pre-line">{quantSummary}</p>
                    </div>
                )}

                {/* Analyst Case / Custom Research */}
                {userSummary && (
                    <div className="p-8 bg-human/[0.02] rounded-2xl border border-human/15 hover:border-human/25 hover:bg-human/[0.04] transition-all duration-200 shadow-sm flex flex-col">
                        <div className="flex items-center gap-3 mb-5 select-none">
                            <div className="w-8 h-8 rounded-full bg-human/10 flex items-center justify-center border border-human/20">
                                <User className="w-4 h-4 text-human" />
                            </div>
                            <p className="label-caps text-human">Analyst / User Insight</p>
                        </div>
                        <p className="text-[15px] font-body font-normal text-ink-mute leading-[1.7] whitespace-pre-line">{userSummary}</p>
                    </div>
                )}

                {/* Rebuttals / Cross-Examination */}
                {result.rebuttal_summary && (
                    <div className="p-8 bg-[#C68A4C]/[0.02] rounded-2xl border border-[#C68A4C]/15 hover:border-[#C68A4C]/25 hover:bg-[#C68A4C]/[0.04] transition-all duration-200 shadow-sm flex flex-col">
                        <div className="flex items-center gap-3 mb-5 select-none">
                            <div className="w-8 h-8 rounded-full bg-[#C68A4C]/10 flex items-center justify-center border border-[#C68A4C]/20">
                                <AlertTriangle className="w-4 h-4 text-[#C68A4C]" />
                            </div>
                            <p className="label-caps text-[#C68A4C]">Rebuttals & Cross-Examination</p>
                        </div>
                        <p className="text-[15px] font-body font-normal text-ink-mute leading-[1.7] whitespace-pre-line">{result.rebuttal_summary}</p>
                    </div>
                )}

                {/* Consensus Summary */}
                <div className="p-10 rounded-2xl border border-panel-line bg-[var(--color-panel-sunk)] relative overflow-hidden shadow-sm">
                    <div className="absolute top-0 left-0 w-1 h-full bg-teal"></div>
                    <p className="label-caps text-teal mb-5 flex items-center gap-2 select-none">
                        <Sparkles className="w-3.5 h-3.5 text-teal" />
                        Consensus Summary
                    </p>
                    <p className="text-[15px] font-body font-normal text-ink-mute leading-[1.7] whitespace-pre-line">
                        {result.reasoning_summary}
                    </p>
                </div>
            </div>

            {/* Interactive Consensus Chat */}
            <div className="mt-12 p-8 rounded-2xl border border-panel-line bg-[var(--color-panel-sunk)] shadow-inner flex flex-col flex-1 min-h-[500px]">
                <h4 className="label-caps text-teal mb-6 flex items-center gap-2 select-none">
                    <MessageSquare className="w-4 h-4 text-teal" /> Chat with Consensus Agent
                </h4>

                <div className="flex-1 overflow-y-auto mb-6 space-y-4 pr-2 custom-scrollbar min-h-[300px]">
                    {chatMessages.length === 0 ? (
                        <div className="flex flex-col items-center justify-center h-full opacity-50 py-10 select-none">
                            <Bot className="w-10 h-10 mb-4 text-ink-dim animate-bounce" style={{ animationDuration: '3s' }} />
                            <p className="label-caps text-ink-mute">No messages yet.</p>
                            <p className="text-xs text-ink-dim mt-2">Type your questions below to debate the analysis!</p>
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
                        placeholder="Have questions about this prediction? Ask the Consensus Analyst directly..."
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
        </div>
    );
}
