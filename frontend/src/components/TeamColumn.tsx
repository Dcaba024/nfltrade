import type { PlayerData, Scoring } from "../types";
import { PlayerChip } from "./PlayerChip";
import { PlayerSearch } from "./PlayerSearch";

export type ColumnGlow = "green" | "cyan" | null;

interface TeamColumnProps {
  title: string;
  players: PlayerData[];
  scoring: Scoring;
  onAdd: (player: PlayerData) => void;
  onRemove: (playerId: string) => void;
  glow?: ColumnGlow;
}

const GLOW_CLASSES: Record<NonNullable<ColumnGlow>, string> = {
  green: "border-neon-green glow-green",
  cyan: "border-neon-cyan glow-cyan",
};

const WINNER_BADGE_CLASSES: Record<NonNullable<ColumnGlow>, string> = {
  green: "border-neon-green text-neon-green",
  cyan: "border-neon-cyan text-neon-cyan",
};

export function TeamColumn({ title, players, scoring, onAdd, onRemove, glow = null }: TeamColumnProps) {
  const glowClass = glow ? GLOW_CLASSES[glow] : "border-border";

  return (
    <div className={`flex flex-1 flex-col gap-3 rounded-xl border bg-surface p-4 transition-shadow ${glowClass}`}>
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-text-dim sm:text-sm">{title}</h2>
        {/* Winning side is also labeled with text, not just the column glow. */}
        {glow && (
          <span
            className={`rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ${WINNER_BADGE_CLASSES[glow]}`}
          >
            Winner
          </span>
        )}
      </div>
      <PlayerSearch
        scoring={scoring}
        onAdd={onAdd}
        excludeIds={players.map((p) => p.id)}
        label={`Search players for ${title}`}
      />
      <div className="flex min-h-12 flex-col gap-2">
        {players.length === 0 && (
          <p className="py-4 text-center text-sm text-text-dim">No players added yet</p>
        )}
        {players.map((player) => (
          <PlayerChip key={player.id} player={player} onRemove={() => onRemove(player.id)} />
        ))}
      </div>
    </div>
  );
}
