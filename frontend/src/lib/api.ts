import type { ApiError, EvaluateResponse, LeaderboardResponse, PlayerData, Scoring } from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:5001";

async function parseJsonOrThrow<T>(res: Response): Promise<T> {
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const message = (body as ApiError | null)?.error || `Request failed with status ${res.status}`;
    throw new Error(message);
  }
  return body as T;
}

export async function searchPlayers(query: string, scoring: Scoring): Promise<PlayerData[]> {
  if (query.trim().length < 2) return [];
  const params = new URLSearchParams({ q: query, scoring });
  const res = await fetch(`${API_BASE_URL}/api/players/search?${params.toString()}`);
  const data = await parseJsonOrThrow<{ players: PlayerData[] }>(res);
  return data.players;
}

export async function getLeaderboard(scoring: Scoring): Promise<LeaderboardResponse> {
  const params = new URLSearchParams({ scoring });
  const res = await fetch(`${API_BASE_URL}/api/leaderboard?${params.toString()}`);
  return parseJsonOrThrow<LeaderboardResponse>(res);
}

export async function evaluateTrade(
  teamA: PlayerData[],
  teamB: PlayerData[],
  scoring: Scoring
): Promise<EvaluateResponse> {
  const res = await fetch(`${API_BASE_URL}/api/evaluate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ teamA, teamB, scoring }),
  });
  return parseJsonOrThrow<EvaluateResponse>(res);
}
