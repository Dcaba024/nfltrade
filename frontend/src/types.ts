export type Scoring = "ppr" | "half" | "standard";

export interface PlayerData {
  id: string;
  name: string;
  team: string | null;
  position: string;
  opponent: string | null;
  injuryStatus: string | null;
  projFantasyPts: number;
  projYards: number;
  projTDs: number;
  imageUrl: string;
}

export interface PlayerEvaluation {
  name: string;
  projFantasyPts: number;
  adjFantasyPts: number;
  adjustmentReason: string;
  riskFlags: string[];
}

export type FairnessGrade = "Even" | "Fair" | "Slight Edge" | "Lopsided" | "Unfair";

export interface ValueGap {
  teamAReceives: number;
  teamBReceives: number;
  percentGap: number;
}

export interface EvaluateResponse {
  winner: "A" | "B" | "even";
  confidence: number;
  marginDescription: string;
  players: PlayerEvaluation[];
  rationale: string;
  fairnessScore: number;
  fairnessGrade: FairnessGrade;
  fairnessRationale: string;
  valueGap: ValueGap;
  /** true if this verdict came from the server-side cache (no OpenAI call was made). */
  cached: boolean;
}

export interface ApiError {
  error: string;
}

export const LEADERBOARD_POSITIONS = ["QB", "RB", "WR", "TE", "K", "DEF"] as const;
export type LeaderboardPosition = (typeof LEADERBOARD_POSITIONS)[number];

export interface LeaderboardEntry {
  rank: number;
  name: string;
  team: string | null;
  position: string;
  imageUrl: string;
  points: number;
}

export type LeaderboardResponse = Partial<Record<LeaderboardPosition, LeaderboardEntry[]>>;
