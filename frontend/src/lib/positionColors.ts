interface PositionColorSet {
  badge: string;
  ring: string;
  text: string;
  tabActive: string;
  /** Inline box-shadow value for the #1 leaderboard row's extra glow. */
  glowShadow: string;
}

// Badges/tabs use a solid neutral background (bg-surface-2) rather than a
// translucent color tint. A tint composited over varying card backgrounds
// (surface vs. surface-2, plus the #1 row's extra glow) pushed contrast for
// the darker hues (pink especially) below the 4.5:1 AA minimum for small
// text depending on context. A fixed neutral background keeps text/border
// color as the position signal while guaranteeing contrast everywhere.
const POSITION_COLORS: Record<string, PositionColorSet> = {
  QB: {
    badge: "bg-surface-2 text-neon-pink border-neon-pink/50",
    ring: "border-neon-pink shadow-[0_0_6px_rgba(255,61,139,0.5)]",
    text: "text-neon-pink",
    tabActive: "bg-surface-2 text-neon-pink border-neon-pink shadow-[0_0_10px_rgba(255,61,139,0.35)]",
    glowShadow: "0 0 16px rgba(255,61,139,0.5)",
  },
  RB: {
    badge: "bg-surface-2 text-neon-green border-neon-green/50",
    ring: "border-neon-green shadow-[0_0_6px_rgba(0,245,160,0.5)]",
    text: "text-neon-green",
    tabActive: "bg-surface-2 text-neon-green border-neon-green shadow-[0_0_10px_rgba(0,245,160,0.35)]",
    glowShadow: "0 0 16px rgba(0,245,160,0.5)",
  },
  WR: {
    badge: "bg-surface-2 text-neon-cyan border-neon-cyan/50",
    ring: "border-neon-cyan shadow-[0_0_6px_rgba(34,224,255,0.5)]",
    text: "text-neon-cyan",
    tabActive: "bg-surface-2 text-neon-cyan border-neon-cyan shadow-[0_0_10px_rgba(34,224,255,0.35)]",
    glowShadow: "0 0 16px rgba(34,224,255,0.5)",
  },
  TE: {
    badge: "bg-surface-2 text-neon-amber border-neon-amber/50",
    ring: "border-neon-amber shadow-[0_0_6px_rgba(255,176,32,0.5)]",
    text: "text-neon-amber",
    tabActive: "bg-surface-2 text-neon-amber border-neon-amber shadow-[0_0_10px_rgba(255,176,32,0.35)]",
    glowShadow: "0 0 16px rgba(255,176,32,0.5)",
  },
  K: {
    badge: "bg-surface-2 text-neon-purple border-neon-purple/50",
    ring: "border-neon-purple shadow-[0_0_6px_rgba(181,123,255,0.5)]",
    text: "text-neon-purple",
    tabActive: "bg-surface-2 text-neon-purple border-neon-purple shadow-[0_0_10px_rgba(181,123,255,0.35)]",
    glowShadow: "0 0 16px rgba(181,123,255,0.5)",
  },
  DEF: {
    badge: "bg-surface-2 text-text-dim border-text-dim/50",
    ring: "border-text-dim",
    text: "text-text-dim",
    tabActive: "bg-surface-2 text-text border-text-dim",
    glowShadow: "0 0 12px rgba(125,139,161,0.4)",
  },
};

const DEFAULT_COLOR: PositionColorSet = {
  badge: "bg-surface-2 text-text-dim border-border",
  ring: "border-border",
  text: "text-text-dim",
  tabActive: "bg-surface-2 text-text border-border",
  glowShadow: "none",
};

export function getPositionColors(position: string): PositionColorSet {
  return POSITION_COLORS[position] ?? DEFAULT_COLOR;
}
