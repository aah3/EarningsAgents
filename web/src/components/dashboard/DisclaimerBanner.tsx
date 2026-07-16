import { AlertTriangle } from "lucide-react";

export default function DisclaimerBanner() {
    return (
        <div className="flex items-center gap-2.5 px-4 py-2.5 rounded-lg border border-panel-line bg-[var(--color-panel-sunk)] select-none">
            <AlertTriangle className="w-3.5 h-3.5 text-ink-dim shrink-0" />
            <p className="text-[11px] font-body font-normal text-ink-dim leading-snug">
                Not investment advice. Predictions are AI-generated and may be wrong — do your own research before making any financial decision.
            </p>
        </div>
    );
}
