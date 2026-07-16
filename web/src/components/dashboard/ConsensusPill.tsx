import React from "react";
import { Consensus } from "./predictions.types";

interface ConsensusPillProps {
  consensus: Consensus;
}

export default function ConsensusPill({ consensus }: ConsensusPillProps) {
  const getStyles = () => {
    switch (consensus) {
      case "BEAT":
        return "bg-bull/10 text-bull border-bull/20 shadow-[0_0_15px_rgba(52,211,153,0.15)]";
      case "MISS":
        return "bg-bear/10 text-bear border-bear/20 shadow-[0_0_15px_rgba(248,113,113,0.15)]";
      case "INLINE":
        return "bg-human/10 text-human border-human/20 shadow-[0_0_15px_rgba(251,191,36,0.15)]";
      default:
        return "bg-ink-dim/10 text-ink-mute border-panel-line";
    }
  };

  return (
    <span
      className={`px-4 py-1.5 rounded-lg text-xs font-mono font-bold tracking-widest border inline-block text-center min-w-[90px] select-none ${getStyles()}`}
    >
      {consensus}
    </span>
  );
}
