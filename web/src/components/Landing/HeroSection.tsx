"use client";

export default function HeroSection() {
    return (
        <section className="relative section-padding px-8 overflow-hidden min-h-[90vh] flex items-center">
            <div className="absolute top-0 right-0 w-1/2 h-full bg-[var(--grad-hero)] -z-10" />

            <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-20 items-center w-full">
                <div className="space-y-10">
                    <div className="space-y-6">
                        <h1 className="text-5xl lg:text-7xl font-extrabold leading-[1.1] tracking-tight">
                            AI-Powered <br />
                            <span className="gradient-text">Earnings Predictions</span> <br />
                            Through Multi-Agent Debate
                        </h1>
                        <p className="text-lg lg:text-xl text-gray-400 max-w-lg leading-relaxed font-medium">
                            See how Bull, Bear, and Quant agents analyze earnings data to deliver
                            actionable predictions with high confidence scores.
                        </p>
                    </div>

                    <div className="flex flex-wrap gap-6">
                        <button className="px-10 py-4 bg-accent text-background rounded-full font-bold hover:shadow-[0_0_30px_rgba(45,212,191,0.3)] transition-all transform hover:-translate-y-1">
                            View Sample Demo
                        </button>
                        <button className="px-10 py-4 glass rounded-full font-bold hover:bg-white/5 transition-all transform hover:-translate-y-1">
                            Watch 2-min Demo
                        </button>
                    </div>
                </div>

                <div className="relative flex justify-center lg:justify-end">
                    <div className="relative w-full max-w-md aspect-square">
                        {/* Multi-agent Visualization */}
                        <div className="absolute inset-0 rounded-full border border-white/5 flex items-center justify-center">
                            <div className="absolute inset-0 animate-[spin_30s_linear_infinite] border border-dashed border-white/10 rounded-full" />

                            {/* Central Node */}
                            <div className="w-32 h-32 rounded-full glass border-white/10 flex items-center justify-center z-10 shadow-2xl">
                                <div className="text-center">
                                    <div className="text-[10px] text-gray-500 uppercase tracking-widest mb-1">Status</div>
                                    <div className="text-accent font-bold text-sm">ANALYZING...</div>
                                </div>
                            </div>

                            {/* Agent Nodes */}
                            <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 w-20 h-20 rounded-full glass border-bull/30 flex items-center justify-center shadow-[0_0_25px_rgba(34,197,94,0.15)] bg-[#0A1A10]">
                                <span className="text-bull font-bold text-xs uppercase">Bull</span>
                            </div>
                            <div className="absolute bottom-10 right-0 w-20 h-20 rounded-full glass border-bear/30 flex items-center justify-center shadow-[0_0_25px_rgba(239,68,68,0.15)] bg-[#1A0A0A]">
                                <span className="text-bear font-bold text-xs uppercase">Bear</span>
                            </div>
                            <div className="absolute bottom-10 left-0 w-20 h-20 rounded-full glass border-quant/30 flex items-center justify-center shadow-[0_0_25px_rgba(59,130,246,0.15)] bg-[#0A101A]">
                                <span className="text-quant font-bold text-xs uppercase">Quant</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </section>
    );
}
