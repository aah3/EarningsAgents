import React from "react";

interface StatCardProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  context: string;
  tone?: "bull" | "bear" | "quant" | "teal";
}

export default function StatCard({ icon, label, value, context, tone }: StatCardProps) {
  const getToneClass = () => {
    switch (tone) {
      case "bull":
        return "text-bull";
      case "bear":
        return "text-bear";
      case "quant":
        return "text-quant";
      case "teal":
        return "text-teal";
      default:
        return "text-ink";
    }
  };

  return (
    <div className="p-[22px_24px] rounded-[16px] border border-[#26334A] bg-panel flex items-center gap-4 hover:bg-white/[0.02] transition-colors duration-150 shadow-[0_20px_60px_rgba(0,0,0,0.35)]">
      <div className="text-3xl text-ink-mute flex-shrink-0 select-none">
        {icon}
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-[11px] font-mono font-bold text-ink-dim uppercase tracking-wider mb-1 select-none">
          {label}
        </p>
        <div className="flex items-baseline gap-2 flex-wrap">
          <span className={`text-2xl font-display font-semibold tracking-tight ${getToneClass()}`}>
            {value}
          </span>
          <span className="text-[11px] font-body text-ink-mute">
            {context}
          </span>
        </div>
      </div>
    </div>
  );
}
