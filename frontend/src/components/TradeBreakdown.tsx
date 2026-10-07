import type { EvaluateResponse, PlayerData, PlayerEvaluation, RosterFit } from "../types";
import { tradeCall } from "../lib/fairness";
import { PlayerHeadshot } from "./PlayerHeadshot";
import { PositionBadge } from "./PositionBadge";
import { ByeTag } from "./PlayerChip";

interface TradeBreakdownProps {
  result: EvaluateResponse;
  /** Players Team A gives up (so Team B receives them). */
  teamA: PlayerData[];
  /** Players Team B gives up (so Team A receives them). */
  teamB: PlayerData[];
}

function evaluationFor(player: PlayerData, players: PlayerEvaluation[]): PlayerEvaluation | undefined {
  const key = player.name.trim().toLowerCase();
  return players.find((p) => p.name.trim().toLowerCase() === key);
}

function ReceivesGroup({
  title,
  received,
  players,
}: {
  title: string;
  received: PlayerData[];
  players: PlayerEvaluation[];
}) {
  return (
    <div className="flex flex-col gap-3">
      <h4 className="text-xs font-semibold uppercase tracking-wide text-text-dim">{title}</h4>
      {received.map((player) => {
        const evaluation = evaluationFor(player, players);
        const outlook = evaluation?.outlook || evaluation?.adjustmentReason || "No outlook available.";
        return (
          <div key={player.id} className="flex gap-3">
            <PlayerHeadshot src={player.imageUrl} size={32} position={player.position} />
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-1.5">
                <PositionBadge position={player.position} />
                <p className="truncate text-sm font-medium text-text">{player.name}</p>
                {player.onBye && <ByeTag />}
                {evaluation && (
                  <span className="ml-auto shrink-0 text-xs text-text-dim">
                    {evaluation.adjFantasyPts.toFixed(1)} pts/g
                  </span>
                )}
              </div>
              <p className="mt-1 text-sm text-text-dim">{outlook}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

const FIT_STYLES: Record<RosterFit["recommendation"], { label: string; classes: string }> = {
  accept: { label: "Accept — it works for your team", classes: "border-neon-green text-neon-green" },
  consider: { label: "Consider — it depends on your plans", classes: "border-neon-amber text-neon-amber" },
  decline: { label: "Decline — it doesn't work for your team", classes: "border-neon-pink text-neon-pink" },
};

function RosterFitCard({ fit }: { fit: RosterFit }) {
  const style = FIT_STYLES[fit.recommendation];
  return (
    <div className={`mt-6 rounded-xl border p-4 ${style.classes}`}>
      <p className="text-xs font-semibold uppercase tracking-wide text-text-dim">For your team</p>
      <p className="mt-1 text-lg font-bold">{style.label}</p>
      {fit.summary && <p className="mt-1 text-sm text-text">{fit.summary}</p>}
      {fit.reasons.length > 0 && (
        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-text-dim">
          {fit.reasons.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function TradeBreakdown({ result, teamA, teamB }: TradeBreakdownProps) {
  const call = tradeCall(result.fairnessScore, result.winner);
  const isFleece = call.label === "Fleece";
  const callStyles = isFleece
    ? "border-neon-pink text-neon-pink glow-pink"
    : "border-neon-green text-neon-green glow-green";
  const factors = result.decisionBreakdown ?? [];

  return (
    <section className="rounded-xl border border-border bg-surface p-5" aria-labelledby="trade-breakdown-heading">
      <h3 id="trade-breakdown-heading" className="mb-4 text-sm font-semibold uppercase tracking-wide text-text-dim">
        Trade Breakdown
      </h3>

      <div className="grid gap-6 sm:grid-cols-2">
        <ReceivesGroup title="Team A receives" received={teamB} players={result.players} />
        <ReceivesGroup title="Team B receives" received={teamA} players={result.players} />
      </div>

      <div className="mt-6 border-t border-border pt-4">
        <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-text-dim">Why this verdict</h4>
        <p className="whitespace-pre-line text-sm text-text">{result.rationale}</p>
        {factors.length > 0 && (
          <ul className="mt-3 list-disc space-y-1.5 pl-5 text-sm text-text">
            {factors.map((factor) => (
              <li key={factor}>{factor}</li>
            ))}
          </ul>
        )}
      </div>

      {result.rosterFit && <RosterFitCard fit={result.rosterFit} />}

      <div className={`mt-6 rounded-xl border-2 p-4 ${callStyles}`}>
        <p className="text-xs font-semibold uppercase tracking-wide text-text-dim">Final call</p>
        <p className="mt-1 text-2xl font-black uppercase tracking-wide">{call.label}</p>
        <p className="mt-1 text-sm font-semibold text-text">{call.headline}</p>
        <p className="mt-1 text-sm text-text-dim">{call.advice}</p>
      </div>
    </section>
  );
}
