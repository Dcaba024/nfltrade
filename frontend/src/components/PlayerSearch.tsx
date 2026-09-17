import { useEffect, useId, useRef, useState } from "react";
import { searchPlayers } from "../lib/api";
import type { PlayerData, Scoring } from "../types";
import { PlayerHeadshot } from "./PlayerHeadshot";
import { PositionBadge } from "./PositionBadge";

interface PlayerSearchProps {
  scoring: Scoring;
  onAdd: (player: PlayerData) => void;
  excludeIds: string[];
  /** Accessible label for the input, e.g. "Search players for Team A gives". */
  label: string;
}

export function PlayerSearch({ scoring, onAdd, excludeIds, label }: PlayerSearchProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<PlayerData[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputId = useId();

  useEffect(() => {
    if (query.trim().length < 2) {
      return;
    }
    let cancelled = false;
    setLoading(true);
    const timeout = setTimeout(async () => {
      try {
        const players = await searchPlayers(query, scoring);
        if (!cancelled) setResults(players);
      } catch {
        if (!cancelled) setResults([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }, 250);
    return () => {
      cancelled = true;
      clearTimeout(timeout);
    };
  }, [query, scoring]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const filteredResults = results.filter((p) => !excludeIds.includes(p.id));
  const showDropdown = open && query.trim().length >= 2;

  const resultStatus = loading
    ? "Searching…"
    : query.trim().length >= 2
      ? `${filteredResults.length} result${filteredResults.length === 1 ? "" : "s"} found`
      : "";

  return (
    <div className="relative" ref={containerRef}>
      <label htmlFor={inputId} className="sr-only">
        {label}
      </label>
      <input
        id={inputId}
        type="text"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={(e) => {
          if (e.key === "Escape") setOpen(false);
        }}
        placeholder="Search players..."
        autoComplete="off"
        className="w-full rounded-lg border border-border bg-surface-2 px-3 py-3 text-base text-text placeholder:text-text-dim focus:outline-none focus:ring-2 focus:ring-neon-green"
      />

      {/* Announces result count/loading to screen readers without duplicating
          the visible dropdown text verbatim on every keystroke. */}
      <span className="sr-only" aria-live="polite">
        {resultStatus}
      </span>

      {showDropdown && (
        <div className="absolute z-10 mt-1 w-full max-h-72 overflow-y-auto rounded-lg border border-border bg-surface-2 shadow-lg">
          {loading && <div className="px-3 py-3 text-sm text-text-dim">Searching...</div>}
          {!loading && filteredResults.length === 0 && (
            <div className="px-3 py-3 text-sm text-text-dim">No players found</div>
          )}
          {!loading &&
            filteredResults.map((player) => (
              <button
                key={player.id}
                type="button"
                onClick={() => {
                  onAdd(player);
                  setQuery("");
                  setResults([]);
                  setOpen(false);
                }}
                className="flex min-h-11 w-full items-center gap-2 px-3 py-2 text-left text-sm text-text hover:bg-surface"
              >
                <PlayerHeadshot src={player.imageUrl} size={28} position={player.position} />
                <span className="flex-1 truncate">{player.name}</span>
                <PositionBadge position={player.position} />
                <span className="text-xs text-text-dim">{player.team ?? "FA"}</span>
              </button>
            ))}
        </div>
      )}
    </div>
  );
}
