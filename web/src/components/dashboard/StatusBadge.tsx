import React from "react";
import { PredictionStatus } from "./predictions.types";

interface StatusBadgeProps {
  status: PredictionStatus;
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  const isValidated = status === "VALIDATED";

  return (
    <span className="flex items-center gap-2 text-xs font-mono font-bold tracking-widest text-ink-mute uppercase select-none">
      <span
        className={`w-1.5 h-1.5 rounded-full ${
          isValidated
            ? "bg-bull shadow-[0_0_8px_rgba(52,211,153,0.8)]"
            : "bg-human shadow-[0_0_8px_rgba(251,191,36,0.8)] animate-pulse"
        }`}
      />
      {status}
    </span>
  );
}
