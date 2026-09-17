import { useRef } from "react";
import { LEADERBOARD_POSITIONS, type LeaderboardPosition } from "../types";
import { getPositionColors } from "../lib/positionColors";
import { leaderboardPanelId, leaderboardTabId } from "../lib/leaderboardIds";

interface LeaderboardTabsProps {
  active: LeaderboardPosition;
  onChange: (position: LeaderboardPosition) => void;
}

export function LeaderboardTabs({ active, onChange }: LeaderboardTabsProps) {
  const tabRefs = useRef<Partial<Record<LeaderboardPosition, HTMLButtonElement | null>>>({});

  function focusAndSelect(position: LeaderboardPosition) {
    onChange(position);
    tabRefs.current[position]?.focus();
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLButtonElement>, index: number) {
    const lastIndex = LEADERBOARD_POSITIONS.length - 1;
    let nextIndex: number | null = null;
    if (e.key === "ArrowRight") nextIndex = index === lastIndex ? 0 : index + 1;
    else if (e.key === "ArrowLeft") nextIndex = index === 0 ? lastIndex : index - 1;
    else if (e.key === "Home") nextIndex = 0;
    else if (e.key === "End") nextIndex = lastIndex;

    if (nextIndex !== null) {
      e.preventDefault();
      focusAndSelect(LEADERBOARD_POSITIONS[nextIndex]);
    }
  }

  return (
    <nav aria-label="Position leaderboards" className="md:hidden">
      <div
        role="tablist"
        aria-label="Position leaderboards"
        className="flex gap-2 overflow-x-auto pb-1"
        style={{ scrollbarWidth: "none" }}
      >
        {LEADERBOARD_POSITIONS.map((position, index) => {
          const colors = getPositionColors(position);
          const isActive = position === active;
          return (
            <button
              key={position}
              ref={(el) => {
                tabRefs.current[position] = el;
              }}
              type="button"
              role="tab"
              id={leaderboardTabId(position)}
              aria-selected={isActive}
              aria-controls={leaderboardPanelId(position)}
              tabIndex={isActive ? 0 : -1}
              onClick={() => onChange(position)}
              onKeyDown={(e) => handleKeyDown(e, index)}
              className={`min-h-11 shrink-0 rounded-lg border px-4 text-sm font-semibold transition ${
                isActive ? colors.tabActive : "border-border bg-surface text-text-dim"
              }`}
            >
              {position}
            </button>
          );
        })}
      </div>
    </nav>
  );
}
