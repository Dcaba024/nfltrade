import type { LeaderboardEntry } from "../types";
import { getPositionColors } from "../lib/positionColors";
import { PlayerHeadshot } from "./PlayerHeadshot";
import { PositionBadge } from "./PositionBadge";

export function LeaderboardRow({ entry }: { entry: LeaderboardEntry }) {
  const colors = getPositionColors(entry.position);
  const isTop = entry.rank === 1;

  return (
    <div
      className={`flex min-h-11 items-center gap-3 rounded-xl border px-3 py-2 ${
        isTop ? `bg-surface-2 ${colors.ring.split(" ")[0]}` : "border-border bg-surface"
      }`}
      style={isTop ? { boxShadow: colors.glowShadow } : undefined}
    >
      <span className="w-5 shrink-0 text-center text-sm font-semibold text-text-dim">{entry.rank}</span>
      <PlayerHeadshot src={entry.imageUrl} size={36} position={entry.position} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5">
          <PositionBadge position={entry.position} />
          <p className="truncate text-sm font-medium text-text">{entry.name}</p>
        </div>
        <p className="text-xs text-text-dim">{entry.team ?? "FA"}</p>
      </div>
      <span className={`shrink-0 text-right text-sm font-bold tabular-nums ${colors.text}`}>
        {entry.points.toFixed(1)}
      </span>
    </div>
  );
}
