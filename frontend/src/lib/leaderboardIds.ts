import type { LeaderboardPosition } from "../types";

export function leaderboardTabId(position: LeaderboardPosition): string {
  return `leaderboard-tab-${position}`;
}

export function leaderboardPanelId(position: LeaderboardPosition): string {
  return `leaderboard-panel-${position}`;
}
