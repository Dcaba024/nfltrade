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
  /** Projected points per game over the rest of the season, bye excluded. */
  rosPtsPerGame?: number | null;
  /** Upcoming bye week, if still ahead this season. */
  byeWeek?: number | null;
  onBye?: boolean;
}

export interface PlayerEvaluation {
  name: string;
  projFantasyPts: number;
  adjFantasyPts: number;
  adjustmentReason: string;
  riskFlags: string[];
  onBye?: boolean;
  byeWeek?: number | null;
  /** What the player brings to a roster. Missing on verdicts cached before this field existed. */
  outlook?: string;
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
  /** Key factors behind the verdict. Missing on verdicts cached before this field existed. */
  decisionBreakdown?: string[];
  fairnessScore: number;
  fairnessGrade: FairnessGrade;
  fairnessRationale: string;
  valueGap: ValueGap;
  /** Verdict for the user's own roster -- only present when one was sent. */
  rosterFit?: RosterFit | null;
  /** true if this verdict came from the server-side cache (no OpenAI call was made). */
  cached: boolean;
}

export type RosterSlot = "starter" | "bench" | "ir";

export interface RosterPlayer extends PlayerData {
  slot: RosterSlot;
}

export interface ParseRosterResponse {
  players: RosterPlayer[];
  /** Names read off the screenshot that didn't match any known player. */
  unmatched: string[];
}

export interface MyRoster {
  side: "A" | "B";
  players: RosterPlayer[];
}

export interface RosterFit {
  recommendation: "accept" | "decline" | "consider";
  summary: string;
  reasons: string[];
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
