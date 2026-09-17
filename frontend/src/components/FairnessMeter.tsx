import type { FairnessGrade, ValueGap } from "../types";
import { fairnessColor, fairnessGlow } from "../lib/fairness";

interface FairnessMeterProps {
  valueGap: ValueGap;
  fairnessScore: number;
  fairnessGrade: FairnessGrade;
  fairnessRationale: string;
}

export function FairnessMeter({ valueGap, fairnessScore, fairnessGrade, fairnessRationale }: FairnessMeterProps) {
  const { teamAReceives, teamBReceives } = valueGap;
  const totalPts = teamAReceives + teamBReceives;
  // Position along the bar: 50 = even. Leans toward whichever side receives more.
  const needlePct = totalPts > 0 ? (teamBReceives / totalPts) * 100 : 50;
  const color = fairnessColor(fairnessScore);
  const glow = fairnessGlow(fairnessScore);

  const summary = `Fairness ${Math.round(fairnessScore)} of 100, ${fairnessGrade}. Team A receives ${teamAReceives.toFixed(1)} points, Team B receives ${teamBReceives.toFixed(1)} points.`;

  return (
    <div className="rounded-xl border border-border bg-surface p-4">
      {/* A bar/needle graphic has no text equivalent of its own for screen
          readers -- this is the one place that information is available to
          them, so the visual bar below is marked decorative. */}
      <p className="sr-only">{summary}</p>

      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1">
        <div className="text-left">
          <p className="text-xs uppercase tracking-wide text-text-dim">Team A gets</p>
          <p className="text-sm font-semibold text-text">{teamAReceives.toFixed(1)} pts</p>
        </div>
        <div className="text-right">
          <p className="text-xs uppercase tracking-wide text-text-dim">Team B gets</p>
          <p className="text-sm font-semibold text-text">{teamBReceives.toFixed(1)} pts</p>
        </div>
      </div>

      <div className="relative mt-3 h-3 w-full rounded-full bg-surface-2" aria-hidden="true">
        {/* Even center mark */}
        <div className="absolute left-1/2 top-1/2 h-4 w-px -translate-x-1/2 -translate-y-1/2 bg-text-dim/50" />
        {/* Needle */}
        <div
          className="absolute top-1/2 h-4 w-4 -translate-y-1/2 -translate-x-1/2 rounded-full border-2 transition-all"
          style={{
            left: `${needlePct}%`,
            backgroundColor: color,
            borderColor: color,
            boxShadow: glow,
          }}
        />
      </div>

      <p className="mt-3 text-xs text-text-dim">{fairnessRationale}</p>

      <p className="mt-2 text-[11px] leading-snug text-text-dim">
        Winner shows WHO is favored. Fairness shows BY HOW MUCH — high fairness means it's close and
        either side is fine to accept; low fairness means one side is getting fleeced and being the
        winner is the one to be.
      </p>
    </div>
  );
}
