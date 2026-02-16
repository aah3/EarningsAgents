"use client";

const agents = [
    {
        name: "Bull Agent",
        role: "Identifies Growth Signals",
        color: "var(--bull-green)",
        icon: "↗",
        shadow: "rgba(34, 197, 94, 0.15)"
    },
    {
        name: "Bear Agent",
        role: "Flags Risk Factors",
        color: "var(--bear-red)",
        icon: "↘",
        shadow: "rgba(239, 68, 68, 0.15)"
    },
    {
        name: "Quant Agent",
        role: "Statistical Patterns",
        color: "var(--quant-blue)",
        icon: "⬡",
        shadow: "rgba(59, 130, 246, 0.15)"
    },
    {
        name: "Consensus Agent",
        role: "Synthesizes Final Call",
        color: "var(--consensus-purple)",
        icon: "⚖",
        shadow: "rgba(168, 85, 247, 0.15)"
    }
];

export default function AgentCommittee() {
    return (
        <section className="section-padding px-8 bg-black/20">
            <div className="max-w-7xl mx-auto">
                <div className="mb-16">
                    <h2 className="text-4xl font-bold mb-4 tracking-tight">Investment Committee in a Box</h2>
                    <div className="h-1 w-20 bg-accent rounded-full" />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
                    {agents.map((agent) => (
                        <div
                            key={agent.name}
                            className="group p-10 rounded-3xl border border-white/5 transition-all hover:bg-white/[0.02] hover:-translate-y-2 duration-500"
                            style={{
                                background: `linear-gradient(180deg, ${agent.shadow} 0%, transparent 100%)`,
                            }}
                        >
                            <div
                                className="w-14 h-14 rounded-2xl flex items-center justify-center text-3xl mb-8 shadow-xl"
                                style={{ backgroundColor: `${agent.color}20`, color: agent.color, border: `1px solid ${agent.color}40` }}
                            >
                                {agent.icon}
                            </div>
                            <h3 className="text-2xl font-bold mb-3">{agent.name}</h3>
                            <p className="text-gray-400 text-base leading-relaxed">
                                {agent.role}
                            </p>
                        </div>
                    ))}
                </div>

                <div className="mt-24 flex items-center justify-center gap-6 text-[10px] font-mono text-gray-600 uppercase tracking-[0.3em]">
                    <span>Data Flow</span>
                    <div className="h-px w-10 bg-gray-800" />
                    <span>Independent Analysis</span>
                    <div className="h-px w-10 bg-gray-800" />
                    <span>Debate</span>
                    <div className="h-px w-10 bg-accent/30" />
                    <span>Agent Votes</span>
                </div>
            </div>
        </section>
    );
}
