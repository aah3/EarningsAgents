"use client";

import { useState, useRef, useEffect } from "react";
import { useAuth } from "@clerk/nextjs";
import { api, Prediction } from "@/lib/api";

export default function AnalysisResult({ result }: { result: Prediction }) {
    const { getToken } = useAuth();
    const [chatMessages, setChatMessages] = useState<{role: string, content: string}[]>([]);
    const [chatInput, setChatInput] = useState("");
    const [chatLoading, setChatLoading] = useState(false);
    const chatEndRef = useRef<HTMLDivElement>(null);

    const parseDebate = (summary?: string) => {
        if (!summary) return { quant: null, user: null };
        const parts = summary.split(/\n(?=(?:BULL |BEAR |QUANT |ANALYST \(USER\):|CONSENSUS ))/);
        let quant = null, user = null;
        for (const p of parts) {
            if (p.startsWith("QUANT")) {
                const idx = p.indexOf(':\n');
                if (idx !== -1) quant = p.substring(idx + 2).trim();
            } else if (p.startsWith("ANALYST (USER):")) {
                const idx = p.indexOf(':\n');
                if (idx !== -1) user = p.substring(idx + 2).trim();
            }
        }
        return { quant, user };
    };

    const { quant: quantSummary, user: userSummary } = parseDebate(result.debate_summary);

    useEffect(() => {
        if (chatMessages.length > 0) {
            chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
        }
    }, [chatMessages]);

    const handleSendChatMessage = async () => {
        if (!chatInput.trim() || !result) return;
        
        const currentMessages = [...chatMessages];
        const newUserMsg = { role: "user", content: chatInput.trim() };
        
        setChatMessages([...currentMessages, newUserMsg]);
        setChatInput("");
        setChatLoading(true);
        
        try {
            const token = await getToken();
            if (!token) throw new Error("Not authenticated");
            
            // Send the entire context
            const chatRes = await api.chatWithConsensus(result.ticker, [...currentMessages, newUserMsg], undefined, token);
            
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
        <div className="flex-1 glass p-10 rounded-3xl border border-accent/20 bg-gradient-to-b from-[#0c1017] to-[#080b11] shadow-2xl animate-in fade-in slide-in-from-bottom-4 duration-700">
            <div className="flex justify-between items-start mb-10 pb-6 border-b border-white/5">
                <div>
                    <div className="flex items-center gap-4 mb-2">
                        <h3 className="text-4xl font-black text-white">{result.ticker}</h3>
                        <span className={`px-4 py-1.5 rounded-full text-xs font-black uppercase tracking-widest
                            ${result.direction === 'BEAT' ? 'bg-bull/10 text-bull border border-bull/30' :
                                result.direction === 'MISS' ? 'bg-bear/10 text-bear border border-bear/30' :
                                    'bg-gray-500/10 text-gray-400 border border-gray-500/30'}
                        `}>
                            {result.direction}
                        </span>
                    </div>
                    <p className="text-gray-400 font-bold tracking-wide uppercase text-xs">{result.company_name}</p>
                </div>
                <div className="text-right">
                    <div className="text-[10px] font-bold uppercase tracking-widest text-gray-500 mb-2">AI Confidence</div>
                    <div className="text-5xl font-black text-transparent bg-clip-text bg-gradient-to-r from-white to-gray-500">
                        {(result.confidence * 100).toFixed(0)}%
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-10">
                <div className="p-4 bg-white/5 rounded-xl border border-white/10 flex flex-col items-center justify-center text-center shadow-inner">
                    <span className="text-[10px] font-bold uppercase tracking-widest text-gray-500 mb-1">Expected Price Move</span>
                    <span className="text-lg font-black text-white capitalize">{result.expected_price_move || "Pending"}</span>
                </div>
                <div className="p-4 bg-white/5 rounded-xl border border-white/10 flex flex-col items-center justify-center text-center shadow-inner">
                    <span className="text-[10px] font-bold uppercase tracking-widest text-gray-500 mb-1">Move vs Implied</span>
                    <span className="text-lg font-black text-white capitalize">{result.move_vs_implied || "Pending"}</span>
                </div>
                <div className="p-4 bg-white/5 rounded-xl border border-white/10 flex flex-col items-center justify-center text-center shadow-inner">
                    <span className="text-[10px] font-bold uppercase tracking-widest text-gray-500 mb-1">Guidance Expectation</span>
                    <span className="text-lg font-black text-white capitalize">{result.guidance_expectation || "Pending"}</span>
                </div>
            </div>

            <div className="flex flex-col gap-8 mb-10">
                <div className="p-6 bg-[#0a1a10] rounded-2xl border border-bull/20 shadow-inner">
                    <div className="flex items-center gap-3 mb-5">
                        <div className="w-8 h-8 rounded-full bg-bull/20 flex items-center justify-center border border-bull/30">
                            <span className="text-bull font-black text-lg">↗</span>
                        </div>
                        <p className="text-xs font-black text-bull uppercase tracking-[0.2em]">Bull Case</p>
                    </div>
                    <ul className="space-y-4">
                        {result.bull_factors?.map((f, i) => (
                            <li key={i} className="text-sm text-gray-300 flex items-start gap-3 leading-relaxed">
                                <span className="text-bull mt-1 font-bold">✓</span> {f}
                            </li>
                        ))}
                    </ul>
                </div>
                
                <div className="p-6 bg-[#1a0a0a] rounded-2xl border border-bear/20 shadow-inner">
                    <div className="flex items-center gap-3 mb-5">
                        <div className="w-8 h-8 rounded-full bg-bear/20 flex items-center justify-center border border-bear/30">
                            <span className="text-bear font-black text-lg">↘</span>
                        </div>
                        <p className="text-xs font-black text-bear uppercase tracking-[0.2em]">Bear Case</p>
                    </div>
                    <ul className="space-y-4">
                        {result.bear_factors?.map((f, i) => (
                            <li key={i} className="text-sm text-gray-300 flex items-start gap-3 leading-relaxed">
                                <span className="text-bear mt-1 font-bold">×</span> {f}
                            </li>
                        ))}
                    </ul>
                </div>

                {quantSummary && (
                    <div className="p-6 bg-blue-900/10 rounded-2xl border border-blue-500/20 shadow-inner">
                        <div className="flex items-center gap-3 mb-5">
                            <div className="w-8 h-8 rounded-full bg-blue-500/20 flex items-center justify-center border border-blue-500/30">
                                <span className="text-blue-400 font-black text-lg">📊</span>
                            </div>
                            <p className="text-xs font-black text-blue-400 uppercase tracking-[0.2em]">Quant Case</p>
                        </div>
                        <p className="text-[15px] text-gray-300 leading-relaxed font-medium whitespace-pre-line">{quantSummary}</p>
                    </div>
                )}
                
                {userSummary && (
                    <div className="p-6 bg-white/5 rounded-2xl border border-white/10 shadow-inner">
                        <div className="flex items-center gap-3 mb-5">
                            <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center border border-white/20">
                                <span className="text-gray-300 font-black text-lg">👤</span>
                            </div>
                            <p className="text-xs font-black text-gray-300 uppercase tracking-[0.2em]">Analyst / User Insight</p>
                        </div>
                        <p className="text-[15px] text-gray-300 leading-relaxed font-medium whitespace-pre-line">{userSummary}</p>
                    </div>
                )}
            </div>

            <div className="p-8 rounded-2xl border border-white/5 bg-black/40 relative overflow-hidden">
                <div className="absolute top-0 left-0 w-1 h-full bg-consensus"></div>
                <p className="text-xs font-black text-consensus uppercase tracking-[0.2em] mb-4 flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-consensus animate-pulse"></span>
                    Consensus Summary
                </p>
                <p className="text-[15px] text-gray-300 leading-relaxed font-medium whitespace-pre-line">
                    {result.reasoning_summary}
                </p>
            </div>

            {/* Interactive Consensus Chat */}
            <div className="mt-8 p-6 rounded-2xl border border-white/5 bg-[#080b11] shadow-inner flex flex-col flex-1 min-h-[500px]">
                <h4 className="text-xs font-black text-consensus uppercase tracking-[0.2em] mb-4 flex items-center gap-2">
                    <span className="text-lg">💬</span> Chat with Consensus Agent
                </h4>
                
                <div className="flex-1 overflow-y-auto mb-4 space-y-4 pr-2 custom-scrollbar min-h-[400px]">
                    {chatMessages.length === 0 ? (
                        <p className="text-sm text-gray-500 italic">Have questions about this prediction? Ask the Consensus Analyst directly.</p>
                    ) : (
                        chatMessages.map((msg, idx) => (
                            <div key={idx} className={`p-4 rounded-xl text-sm ${msg.role === 'user' ? 'bg-white/5 text-gray-200 ml-4 border border-white/10' : 'bg-consensus/10 text-gray-300 mr-4 border border-consensus/30'}`}>
                                <div className={`text-[10px] font-bold uppercase tracking-widest mb-2 ${msg.role === 'user' ? 'text-gray-400' : 'text-consensus'}`}>
                                    {msg.role === 'user' ? 'You' : 'Consensus Analyst'}
                                </div>
                                <div className="whitespace-pre-wrap leading-relaxed">{msg.content}</div>
                            </div>
                        ))
                    )}
                    {chatLoading && (
                        <div className="p-4 rounded-xl bg-consensus/10 text-consensus mr-4 border border-consensus/30 flex items-center gap-3 w-fit">
                            <span className="animate-pulse w-2 h-2 bg-consensus rounded-full"></span>
                            <span className="animate-pulse text-xs font-bold uppercase tracking-widest">Thinking...</span>
                        </div>
                    )}
                    <div ref={chatEndRef} />
                </div>
                
                <div className="flex gap-3 relative mt-auto">
                    <input
                        type="text"
                        placeholder="E.g. What about the macroeconomic risks?"
                        value={chatInput}
                        onChange={(e) => setChatInput(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleSendChatMessage()}
                        className="flex-1 bg-black/50 border border-white/10 rounded-xl px-4 py-4 focus:border-consensus focus:ring-1 focus:ring-consensus/50 outline-none transition-all text-sm font-medium text-white placeholder-white/20"
                        disabled={chatLoading}
                    />
                    <button
                        onClick={handleSendChatMessage}
                        disabled={chatLoading || !chatInput.trim()}
                        className="px-8 rounded-xl font-bold uppercase tracking-widest text-sm transition-colors bg-consensus text-background hover:bg-consensus/90 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        Send
                    </button>
                </div>
            </div>
        </div>
    );
}
