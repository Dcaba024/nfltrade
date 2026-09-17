import { useRef, useState } from "react";
import { TeamColumn } from "./components/TeamColumn";
import { ResultsPanel } from "./components/ResultsPanel";
import { Leaderboard } from "./components/Leaderboard";
import { evaluateTrade } from "./lib/api";
import type { EvaluateResponse, PlayerData, Scoring } from "./types";

function addPlayer(list: PlayerData[], player: PlayerData): PlayerData[] {
  if (list.some((p) => p.id === player.id)) return list;
  return [...list, player];
}

function App() {
  const [teamA, setTeamA] = useState<PlayerData[]>([]);
  const [teamB, setTeamB] = useState<PlayerData[]>([]);
  const [scoring, setScoring] = useState<Scoring>("ppr");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<EvaluateResponse | null>(null);
  const builderHeadingRef = useRef<HTMLHeadingElement>(null);

  const canEvaluate = teamA.length > 0 && teamB.length > 0 && !loading;

  async function handleEvaluate() {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const response = await evaluateTrade(teamA, teamB, scoring);
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  function handleNewTrade() {
    setResult(null);
    setTeamA([]);
    setTeamB([]);
    // Leaderboards are about to replace the verdict -- return focus to a
    // sensible spot in the trade builder rather than leaving it stranded.
    builderHeadingRef.current?.focus();
  }

  return (
    <div className="min-h-screen bg-bg">
      <div className="mx-auto max-w-5xl px-4 pb-40 pt-6 md:pb-12 md:pt-8">
        <header className="mb-6 flex flex-col gap-1">
          <h1 className="text-2xl font-bold text-text">Teach Me to Football</h1>
          <p className="text-sm text-text-dim">Commissioner: Nicky Nick</p>
        </header>

        <main>
          <div className="mb-4 flex items-center justify-between">
            <label className="flex items-center gap-2 text-sm text-text-dim">
              Scoring format
              <select
                value={scoring}
                onChange={(e) => setScoring(e.target.value as Scoring)}
                className="min-h-11 rounded-lg border border-border bg-surface px-2 py-1 text-base text-text"
              >
                <option value="ppr">PPR</option>
                <option value="half">Half PPR</option>
                <option value="standard">Standard</option>
              </select>
            </label>
          </div>

          {/* Visually hidden, but a real focusable heading: lets "New trade"
              return focus somewhere meaningful, and gives the builder its
              own place in the heading structure for screen reader users. */}
          <h2 ref={builderHeadingRef} tabIndex={-1} className="sr-only">
            Build your trade
          </h2>

          <div className="flex flex-col gap-4 md:flex-row">
            <TeamColumn
              title="Team A gives"
              players={teamA}
              scoring={scoring}
              onAdd={(p) => setTeamA((list) => addPlayer(list, p))}
              onRemove={(id) => setTeamA((list) => list.filter((p) => p.id !== id))}
              glow={result?.winner === "A" ? "green" : null}
            />
            <TeamColumn
              title="Team B gives"
              players={teamB}
              scoring={scoring}
              onAdd={(p) => setTeamB((list) => addPlayer(list, p))}
              onRemove={(id) => setTeamB((list) => list.filter((p) => p.id !== id))}
              glow={result?.winner === "B" ? "cyan" : null}
            />
          </div>

          {/* Sticky, thumb-reachable CTA on mobile; inline (above the leaderboards) on desktop. */}
          <div className="fixed inset-x-0 bottom-0 z-50 border-t border-border bg-surface/95 p-3 backdrop-blur md:static md:mt-6 md:border-0 md:bg-transparent md:p-0 md:backdrop-blur-none">
            <div
              className="mx-auto flex max-w-5xl flex-col items-center gap-2 px-1 md:px-0"
              style={{ paddingBottom: "max(0px, env(safe-area-inset-bottom))" }}
            >
              {error && <p className="text-sm text-neon-pink">{error}</p>}
              <button
                type="button"
                disabled={!canEvaluate}
                onClick={handleEvaluate}
                className={`flex min-h-11 w-full items-center justify-center gap-2 rounded-lg border px-6 py-3 text-sm font-semibold transition hover:brightness-110 disabled:cursor-not-allowed md:w-auto ${
                  canEvaluate
                    ? "border-neon-green bg-neon-green text-bg glow-green"
                    : "border-border bg-surface-2 text-text-dim"
                }`}
              >
                {loading && (
                  <span
                    aria-hidden="true"
                    className="h-4 w-4 animate-spin rounded-full border-2 border-text-dim border-t-transparent"
                  />
                )}
                {loading ? "Evaluating trade... (up to 30s)" : "Evaluate trade"}
              </button>
            </div>
          </div>

          {/* The web-search-backed evaluation takes 10-30s -- announce both
              the wait and the arrival of results rather than leaving screen
              reader users with silence. */}
          <div className="mt-8" aria-live="polite" aria-busy={loading}>
            {loading && (
              <p className="text-sm text-text-dim">Evaluating trade — this can take up to 30 seconds…</p>
            )}
            {!loading && result && (
              <div className="flex flex-col gap-4">
                <button
                  type="button"
                  onClick={handleNewTrade}
                  className="flex min-h-11 w-fit items-center gap-1.5 rounded-lg border border-border bg-surface px-3 text-sm font-medium text-text-dim transition hover:border-neon-green hover:text-neon-green"
                >
                  <span aria-hidden="true">←</span> New trade
                </button>
                <ResultsPanel result={result} teamA={teamA} teamB={teamB} />
              </div>
            )}
            {!loading && !result && <Leaderboard scoring={scoring} />}
          </div>
        </main>

        <footer className="mt-12 pb-4 text-center text-xs text-text-dim">Created by dilly</footer>
      </div>
    </div>
  );
}

export default App;
