import { getPositionColors } from "../lib/positionColors";

export function PositionBadge({ position }: { position: string }) {
  const colors = getPositionColors(position);
  return (
    <span
      className={`inline-flex shrink-0 items-center justify-center rounded-md border px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide ${colors.badge}`}
    >
      {position}
    </span>
  );
}
