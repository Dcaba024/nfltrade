import type { LeaderboardEntry, LeaderboardPosition } from "../types";
import { getPositionColors } from "../lib/positionColors";
import { LeaderboardRow } from "./LeaderboardRow";

function SkeletonRow() {
  return (
    <div className="flex min-h-11 items-center gap-3 rounded-xl border border-border bg-surface px-3 py-2">
      <div className="h-4 w-5 shrink-0 rounded bg-surface-2" />
      <div className="h-9 w-9 shrink-0 rounded-full bg-surface-2" />
      <div className="flex-1 space-y-1.5">
        <div className="h-3 w-2/3 rounded bg-surface-2" />
        <div className="h-2.5 w-1/3 rounded bg-surface-2" />
      </div>
      <div className="h-4 w-8 shrink-0 rounded bg-surface-2" />
    </div>
  );
}

interface LeaderboardColumnProps {
  position: LeaderboardPosition;
  entries: LeaderboardEntry[] | undefined;
  loading: boolean;
  showHeader?: boolean;
}

export function LeaderboardColumn({ position, entries, loading, showHeader = false }: LeaderboardColumnProps) {
  const colors = getPositionColors(position);

  return (
    <div className="flex flex-col gap-2">
      {showHeader && (
        <h3 className={`text-xs font-semibold uppercase tracking-wide ${colors.text}`}>{position}</h3>
      )}
      <div className="flex flex-col gap-1.5 animate-pulse" aria-hidden="true">
        {loading && Array.from({ length: 5 }).map((_, i) => <SkeletonRow key={i} />)}
      </div>
      {loading && <p className="sr-only" role="status">{`Loading ${position} leaderboard…`}</p>}
      {!loading && (
        <div className="flex flex-col gap-1.5">
          {(!entries || entries.length === 0) && (
            <p className="rounded-xl border border-border bg-surface px-3 py-6 text-center text-sm text-text-dim">
              No {position} data yet
            </p>
          )}
          {entries?.map((entry) => (
            <LeaderboardRow key={`${entry.rank}-${entry.name}`} entry={entry} />
          ))}
        </div>
      )}
    </div>
  );
}
