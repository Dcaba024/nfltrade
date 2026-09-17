import type { PlayerData } from "../types";
import { PlayerHeadshot } from "./PlayerHeadshot";
import { PositionBadge } from "./PositionBadge";

interface PlayerChipProps {
  player: PlayerData;
  onRemove: () => void;
}

export function PlayerChip({ player, onRemove }: PlayerChipProps) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-border bg-surface-2 py-1.5 pl-1.5 pr-1.5">
      <PlayerHeadshot src={player.imageUrl} size={40} position={player.position} />
      <div className="flex flex-1 min-w-0 flex-col leading-tight">
        <span className="truncate text-sm font-medium text-text">{player.name}</span>
        <span className="flex items-center gap-1.5 text-xs text-text-dim">
          <PositionBadge position={player.position} />
          {player.team ?? "FA"} · {player.projFantasyPts.toFixed(1)} pts
        </span>
      </div>
      <button
        type="button"
        onClick={onRemove}
        aria-label={`Remove ${player.name}`}
        className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-text-dim hover:text-neon-pink"
      >
        <span className="text-lg leading-none" aria-hidden="true">
          ✕
        </span>
      </button>
    </div>
  );
}
