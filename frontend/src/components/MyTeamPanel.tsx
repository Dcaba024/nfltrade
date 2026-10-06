import { useRef, useState } from "react";
import { parseRosterScreenshot } from "../lib/api";
import type { RosterPlayer, RosterSlot, Scoring } from "../types";
import { PlayerChip } from "./PlayerChip";
import { PlayerSearch } from "./PlayerSearch";

interface MyTeamPanelProps {
  roster: RosterPlayer[];
  onRosterChange: (roster: RosterPlayer[]) => void;
  side: "A" | "B";
  /** True when the side was inferred from which column holds roster players. */
  sideInferred: boolean;
  onSideChange: (side: "A" | "B") => void;
  scoring: Scoring;
}

const SLOT_GROUPS: { slot: RosterSlot; label: string }[] = [
  { slot: "starter", label: "Starters" },
  { slot: "bench", label: "Bench" },
  { slot: "ir", label: "IR" },
];

export function MyTeamPanel({ roster, onRosterChange, side, sideInferred, onSideChange, scoring }: MyTeamPanelProps) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [unmatched, setUnmatched] = useState<string[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function handleFile(file: File | undefined) {
    if (!file) return;
    setUploading(true);
    setError(null);
    setUnmatched([]);
    try {
      const result = await parseRosterScreenshot(file, scoring);
      if (result.players.length === 0) {
        setError("Couldn't find any players in that screenshot. Try a clearer shot of your roster page.");
      } else {
        onRosterChange(result.players);
      }
      setUnmatched(result.unmatched);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't read that screenshot");
    } finally {
      setUploading(false);
      // Let the same file be picked again after a failure.
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  function handleClear() {
    onRosterChange([]);
    setUnmatched([]);
    setError(null);
  }

  return (
    <section className="mb-4 rounded-xl border border-border bg-surface p-4" aria-labelledby="my-team-heading">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 id="my-team-heading" className="text-xs font-semibold uppercase tracking-wide text-text-dim sm:text-sm">
            Your team <span className="font-normal normal-case">(optional)</span>
          </h2>
          {roster.length === 0 && (
            <p className="mt-1 text-sm text-text-dim">
              Upload a screenshot of your roster and the verdict will say whether this trade works for your team.
            </p>
          )}
        </div>
        <div className="flex gap-2">
          <input
            ref={fileInputRef}
            type="file"
            accept="image/png,image/jpeg,image/webp"
            className="sr-only"
            id="roster-upload"
            onChange={(e) => handleFile(e.target.files?.[0])}
            disabled={uploading}
          />
          <label
            htmlFor="roster-upload"
            className={`flex min-h-11 cursor-pointer items-center gap-2 rounded-lg border px-3 text-sm font-medium transition ${
              uploading
                ? "cursor-wait border-border text-text-dim"
                : "border-neon-cyan text-neon-cyan hover:brightness-110"
            }`}
          >
            {uploading && (
              <span
                aria-hidden="true"
                className="h-4 w-4 animate-spin rounded-full border-2 border-text-dim border-t-transparent"
              />
            )}
            {uploading ? "Reading roster…" : roster.length ? "Replace screenshot" : "Upload screenshot"}
          </label>
          {roster.length > 0 && !uploading && (
            <button
              type="button"
              onClick={handleClear}
              className="min-h-11 rounded-lg border border-border px-3 text-sm font-medium text-text-dim hover:border-neon-pink hover:text-neon-pink"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      <div aria-live="polite">
        {error && <p className="mt-3 text-sm text-neon-pink">{error}</p>}
        {unmatched.length > 0 && (
          <p className="mt-3 text-sm text-neon-amber">
            Couldn't match: {unmatched.join(", ")}. Add them with the search below if they're on your roster.
          </p>
        )}
      </div>

      {roster.length > 0 && (
        <>
          <fieldset className="mt-4 flex flex-wrap items-center gap-2">
            <legend className="sr-only">Which side of the trade is your team?</legend>
            <span className="text-sm text-text-dim" aria-hidden="true">
              I'm
            </span>
            {(["A", "B"] as const).map((s) => (
              <label
                key={s}
                className={`flex min-h-11 cursor-pointer items-center rounded-lg border px-3 text-sm font-medium transition ${
                  side === s ? "border-neon-green text-neon-green" : "border-border text-text-dim hover:text-text"
                }`}
              >
                <input
                  type="radio"
                  name="my-side"
                  value={s}
                  checked={side === s}
                  onChange={() => onSideChange(s)}
                  className="sr-only"
                />
                Team {s}
              </label>
            ))}
            {sideInferred && (
              <span className="text-xs text-text-dim">Detected from the players you're giving up</span>
            )}
          </fieldset>

          <div className="mt-4 grid gap-4 md:grid-cols-3">
            {SLOT_GROUPS.map(({ slot, label }) => {
              const players = roster.filter((p) => p.slot === slot);
              if (players.length === 0) return null;
              return (
                <div key={slot} className="flex flex-col gap-2">
                  <h3 className="text-xs font-semibold uppercase tracking-wide text-text-dim">
                    {label} · {players.length}
                  </h3>
                  {players.map((player) => (
                    <PlayerChip
                      key={player.id}
                      player={player}
                      onRemove={() => onRosterChange(roster.filter((p) => p.id !== player.id))}
                    />
                  ))}
                </div>
              );
            })}
          </div>

          <div className="mt-4">
            <PlayerSearch
              scoring={scoring}
              onAdd={(p) => onRosterChange([...roster, { ...p, slot: "bench" }])}
              excludeIds={roster.map((p) => p.id)}
              label="Add a missing player to your team"
            />
          </div>
        </>
      )}
    </section>
  );
}
