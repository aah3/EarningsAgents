"use client";

import { useState } from "react";
import { usePathname } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import { MessageSquarePlus, X, Send, Check } from "lucide-react";
import { api } from "@/lib/api";

const CATEGORIES = [
    { value: "bug", label: "Bug" },
    { value: "accuracy", label: "Prediction Accuracy" },
    { value: "idea", label: "Feature Idea" },
    { value: "other", label: "Other" },
];

export default function FeedbackWidget() {
    const { getToken } = useAuth();
    const pathname = usePathname();
    const [open, setOpen] = useState(false);
    const [category, setCategory] = useState("bug");
    const [message, setMessage] = useState("");
    const [submitting, setSubmitting] = useState(false);
    const [sent, setSent] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = async () => {
        if (!message.trim()) return;
        setSubmitting(true);
        setError(null);
        try {
            const token = await getToken() || undefined;
            await api.submitFeedback(category, message.trim(), pathname, token);
            setSent(true);
            setMessage("");
            setTimeout(() => {
                setOpen(false);
                setSent(false);
            }, 1500);
        } catch (err: any) {
            setError(err instanceof Error ? err.message : "Failed to send feedback.");
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <>
            <button
                onClick={() => setOpen(true)}
                className="fixed bottom-6 right-6 z-30 flex items-center gap-2 px-4 py-3 rounded-full bg-teal text-[var(--color-bg)] shadow-lg hover:bg-teal-deep transition-all cursor-pointer select-none label-caps outline-none focus-visible:ring-2 focus-visible:ring-teal"
            >
                <MessageSquarePlus className="w-4 h-4" />
                <span className="max-[640px]:hidden">Feedback</span>
            </button>

            {open && (
                <div className="fixed inset-0 z-40 flex items-end justify-end p-6 bg-black/40" onClick={() => setOpen(false)}>
                    <div
                        className="w-full max-w-sm bg-panel border border-panel-line rounded-2xl shadow-2xl p-6 flex flex-col gap-4 animate-in fade-in slide-in-from-bottom-4 duration-200"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div className="flex items-center justify-between">
                            <h3 className="label-caps text-teal">Send Feedback</h3>
                            <button
                                onClick={() => setOpen(false)}
                                className="text-ink-dim hover:text-ink cursor-pointer outline-none"
                            >
                                <X className="w-4 h-4" />
                            </button>
                        </div>

                        {sent ? (
                            <div className="flex flex-col items-center gap-2 py-6 text-bull select-none">
                                <Check className="w-8 h-8" />
                                <p className="text-sm font-body">Thanks — feedback received.</p>
                            </div>
                        ) : (
                            <>
                                <div className="flex flex-wrap gap-2">
                                    {CATEGORIES.map((c) => (
                                        <button
                                            key={c.value}
                                            onClick={() => setCategory(c.value)}
                                            className={`px-3 py-1.5 rounded-full text-[11px] font-mono font-bold uppercase tracking-widest transition-all cursor-pointer outline-none ${
                                                category === c.value
                                                    ? "bg-teal text-[var(--color-bg)]"
                                                    : "bg-[var(--color-panel-sunk)] text-ink-mute border border-panel-line hover:border-teal/50"
                                            }`}
                                        >
                                            {c.label}
                                        </button>
                                    ))}
                                </div>

                                <textarea
                                    value={message}
                                    onChange={(e) => setMessage(e.target.value)}
                                    placeholder="What's on your mind?"
                                    rows={4}
                                    className="w-full bg-[var(--color-panel-sunk)] border border-panel-line focus:border-teal/50 focus:ring-1 focus:ring-teal/20 rounded-xl outline-none text-sm font-body text-ink placeholder-ink-dim/40 resize-none p-3 custom-scrollbar"
                                />

                                {error && <p className="text-xs text-bear">{error}</p>}

                                <button
                                    onClick={handleSubmit}
                                    disabled={submitting || !message.trim()}
                                    className="w-full h-11 rounded-lg label-caps bg-teal text-[var(--color-bg)] hover:bg-teal-deep disabled:opacity-30 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2 cursor-pointer"
                                >
                                    <span>{submitting ? "Sending..." : "Send"}</span>
                                    <Send className="w-3.5 h-3.5" />
                                </button>
                            </>
                        )}
                    </div>
                </div>
            )}
        </>
    );
}
