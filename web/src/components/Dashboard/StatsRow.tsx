import React from "react";
import { Activity, Target, Ruler, TrendingUp } from "lucide-react";
import StatCard from "./StatCard";
import { PredictionMetrics } from "@/lib/api";

interface StatsRowProps {
  metrics: PredictionMetrics | null;
}

export default function StatsRow({ metrics }: StatsRowProps) {
  // Derive win rate percentage
  const winRateVal =
    metrics && metrics.scored_predictions > 0
      ? `${(metrics.win_rate * 100).toFixed(1)}%`
      : "—";

  // Derive Brier score value
  const brierScoreVal =
    metrics && metrics.scored_predictions > 0
      ? metrics.avg_brier_score.toFixed(3)
      : "—";

  // Derive confidence percentage
  const confidenceVal = metrics
    ? `${(metrics.avg_confidence * 100).toFixed(0)}%`
    : "—";

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      <StatCard
        icon={<Activity className="w-6 h-6" />}
        label="Total Analyses"
        value={metrics ? String(metrics.total_predictions) : "—"}
        context={metrics ? `${metrics.scored_predictions} scored` : "all time"}
        tone="teal"
      />
      <StatCard
        icon={<Target className="w-6 h-6" />}
        label="Win Rate"
        value={winRateVal}
        context={
          metrics && metrics.scored_predictions > 0
            ? `n = ${metrics.scored_predictions} validated`
            : "no validated calls"
        }
        tone="bull"
      />
      <StatCard
        icon={<Ruler className="w-6 h-6" />}
        label="Avg Brier Score"
        value={brierScoreVal}
        context="lower is better"
        tone="quant"
      />
      <StatCard
        icon={<TrendingUp className="w-6 h-6" />}
        label="Avg Confidence"
        value={confidenceVal}
        context="across predictions"
        tone="teal"
      />
    </div>
  );
}
