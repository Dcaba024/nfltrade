import { useEffect, useState } from "react";
import { getLeaderboard } from "../lib/api";
import { LEADERBOARD_POSITIONS, type LeaderboardPosition, type LeaderboardResponse, type Scoring } from "../types";
import { LeaderboardTabs } from "./LeaderboardTabs";
import { LeaderboardColumn } from "./LeaderboardColumn";
import { leaderboardPanelId, leaderboardTabId } from "../lib/leaderboardIds";

export function Leaderboard({ scoring }: { scoring: Scoring }) {
  const [board, setBoard] = useState<LeaderboardResponse>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<LeaderboardPosition>("QB");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getLeaderboard(scoring)
      .then((data) => {
        if (!cancelled) setBoard(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load leaderboard");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [scoring]);

  return (
    <div className="flex flex-col gap-3">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-text-dim">Leaderboards</h2>

      {error && <p className="text-sm text-neon-pink">{error}</p>}

      <LeaderboardTabs active={activeTab} onChange={setActiveTab} />

      {/* Mobile: one position at a time. */}
      <div
        className="md:hidden"
        role="tabpanel"
        id={leaderboardPanelId(activeTab)}
        aria-labelledby={leaderboardTabId(activeTab)}
        tabIndex={0}
      >
        <LeaderboardColumn position={activeTab} entries={board[activeTab]} loading={loading} />
      </div>

      {/* Desktop: all positions side by side. */}
      <div className="hidden grid-cols-2 gap-4 md:grid lg:grid-cols-3">
        {LEADERBOARD_POSITIONS.map((position) => (
          <LeaderboardColumn
            key={position}
            position={position}
            entries={board[position]}
            loading={loading}
            showHeader
          />
        ))}
      </div>
    </div>
  );
}
