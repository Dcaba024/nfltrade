import type { FairnessGrade } from "../types";
import { fairnessColor, fairnessGlow } from "../lib/fairness";

export function FairnessGradePill({ grade, score }: { grade: FairnessGrade; score: number }) {
  const color = fairnessColor(score);
  const glow = fairnessGlow(score);

  return (
    <span
      className="rounded-full border px-2.5 py-1 text-xs font-bold uppercase tracking-wide"
      style={{ color, borderColor: color, boxShadow: glow }}
    >
      {grade} · {Math.round(score)}/100
    </span>
  );
}
