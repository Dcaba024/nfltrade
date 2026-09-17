import { useEffect, useRef } from "react";
import type { EvaluateResponse, PlayerData } from "../types";
import { PlayerHeadshot } from "./PlayerHeadshot";
import { PositionBadge } from "./PositionBadge";
import { FairnessMeter } from "./FairnessMeter";
import { FairnessGradePill } from "./FairnessGradePill";

interface ResultsPanelProps {
  result: EvaluateResponse;
  teamA: PlayerData[];
  teamB: PlayerData[];
}

const WINNER_LABEL: Record<EvaluateResponse["winner"], string> = {
  A: "Team A wins the trade",
  B: "Team B wins the trade",
  even: "Even trade",
};

interface WinnerAccent {
  border: string;
  glow: string;
  text: string;
  textGlow: string;
  barColor: string;
  barShadow: string;
}

const WINNER_ACCENT: Record<EvaluateResponse["winner"], WinnerAccent> = {
  A: {
    border: "border-neon-green",
    glow: "glow-green",
    text: "text-neon-green",
    textGlow: "text-glow-green",
    barColor: "var(--neon-green)",
    barShadow: "0 0 8px rgba(0,245,160,0.7)",
  },
  B: {
    border: "border-neon-cyan",
    glow: "glow-cyan",
    text: "text-neon-cyan",
    textGlow: "text-glow-cyan",
    barColor: "var(--neon-cyan)",
    barShadow: "0 0 8px rgba(34,224,255,0.7)",
  },
  even: {
    border: "border-border",
    glow: "",
    text: "text-text",
    textGlow: "",
    barColor: "var(--text-dim)",
    barShadow: "none",
  },
};

function findPlayer(name: string, teamA: PlayerData[], teamB: PlayerData[]): PlayerData | undefined {
  return [...teamA, ...teamB].find((p) => p.name === name);
}

export function ResultsPanel({ result, teamA, teamB }: ResultsPanelProps) {
  const accent = WINNER_ACCENT[result.winner];
  const confidencePct = Math.round(result.confidence * 100);
  const headingRef = useRef<HTMLHeadingElement>(null);

  // Verdict replaced the leaderboards -- move keyboard focus to the verdict
  // heading so keyboard/screen-reader users land somewhere meaningful.
  useEffect(() => {
    headingRef.current?.focus();
  }, []);

  return (
    <div className="flex flex-col gap-6">
      <div aria-live="polite" className="sr-only">
        Trade evaluated.
      </div>

      <FairnessMeter
        valueGap={result.valueGap}
        fairnessScore={result.fairnessScore}
        fairnessGrade={result.fairnessGrade}
        fairnessRationale={result.fairnessRationale}
      />

      <div className={`rounded-2xl border p-5 bg-surface ${accent.border} ${accent.glow}`}>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-2">
            <h2 ref={headingRef} tabIndex={-1} className={`text-lg font-bold ${accent.text} ${accent.textGlow}`}>
              {WINNER_LABEL[result.winner]}
            </h2>
            <FairnessGradePill grade={result.fairnessGrade} score={result.fairnessScore} />
            {result.cached && (
              <span className="rounded-full border border-neon-cyan px-2.5 py-1 text-xs font-bold uppercase tracking-wide text-neon-cyan">
                Cached — no API cost
              </span>
            )}
          </div>
          <span className="text-sm font-medium text-text-dim">{confidencePct}% confidence</span>
        </div>

        <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-surface-2">
          <div
            className="h-full rounded-full transition-all"
            style={{
              width: `${confidencePct}%`,
              backgroundColor: accent.barColor,
              boxShadow: accent.barShadow,
            }}
          />
        </div>

        <p className="mt-3 text-sm text-text-dim">{result.marginDescription}</p>
      </div>

      <div className="flex flex-col gap-3">
        {result.players.map((p) => {
          const player = findPlayer(p.name, teamA, teamB);
          const delta = p.adjFantasyPts - p.projFantasyPts;
          const deltaLabel = delta === 0 ? "±0.0" : `${delta > 0 ? "+" : ""}${delta.toFixed(1)}`;
          const deltaColor = delta > 0 ? "text-neon-green" : delta < 0 ? "text-neon-pink" : "text-text-dim";
          const deltaArrow = delta > 0 ? "▲" : delta < 0 ? "▼" : "▬";
          const deltaDescription =
            delta === 0
              ? "No change from baseline"
              : `${delta > 0 ? "Increased" : "Decreased"} by ${Math.abs(delta).toFixed(1)} points from baseline`;

          return (
            <div key={p.name} className="rounded-xl border border-border bg-surface p-4">
              <div className="flex items-center gap-3">
                <PlayerHeadshot src={player?.imageUrl ?? ""} size={44} position={player?.position} />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5">
                    {player && <PositionBadge position={player.position} />}
                    <p className="truncate text-sm font-medium text-text">{p.name}</p>
                  </div>
                  <p className="text-xs text-text-dim">
                    {p.projFantasyPts.toFixed(1)} → {p.adjFantasyPts.toFixed(1)} pts{" "}
                    <span className={deltaColor} aria-label={deltaDescription}>
                      <span aria-hidden="true">
                        ({deltaArrow} {deltaLabel})
                      </span>
                    </span>
                  </p>
                </div>
              </div>
              <p className="mt-2 text-sm text-text-dim">{p.adjustmentReason}</p>
              {p.riskFlags.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {p.riskFlags.map((flag) => (
                    <span
                      key={flag}
                      className="rounded-full border border-neon-amber px-2 py-0.5 text-xs font-medium text-neon-amber shadow-[0_0_6px_rgba(255,176,32,0.35)]"
                    >
                      <span className="sr-only">Risk: </span>
                      {flag}
                    </span>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="rounded-xl border border-border bg-surface p-5">
        <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-text-dim">Rationale</h3>
        <p className="whitespace-pre-line text-sm text-text">{result.rationale}</p>
      </div>
    </div>
  );
}
