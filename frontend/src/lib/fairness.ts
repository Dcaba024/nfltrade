const PINK: [number, number, number] = [255, 61, 139];
const AMBER: [number, number, number] = [255, 176, 32];
const GREEN: [number, number, number] = [0, 245, 160];

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

/** Smoothly interpolates pink -> amber -> green as fairnessScore goes 0 -> 100. */
export function fairnessColor(score: number): string {
  const clamped = Math.max(0, Math.min(100, score));
  const [c1, c2, t] = clamped >= 50 ? [AMBER, GREEN, (clamped - 50) / 50] : [PINK, AMBER, clamped / 50];
  const r = Math.round(lerp(c1[0], c2[0], t));
  const g = Math.round(lerp(c1[1], c2[1], t));
  const b = Math.round(lerp(c1[2], c2[2], t));
  return `rgb(${r}, ${g}, ${b})`;
}

export function fairnessGlow(score: number): string {
  return `0 0 10px ${fairnessColor(score).replace("rgb", "rgba").replace(")", ", 0.55)")}`;
}
