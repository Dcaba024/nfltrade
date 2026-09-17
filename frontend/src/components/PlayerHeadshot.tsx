import { useState } from "react";
import { getPositionColors } from "../lib/positionColors";

const PLACEHOLDER_SRC = "/placeholder-player.png";

interface PlayerHeadshotProps {
  src: string;
  /** Every current usage shows the player's name as adjacent text, so the
   * image is decorative by default (alt=""). Pass a real alt only if no
   * adjacent name text exists for a given usage. */
  alt?: string;
  size?: number;
  position?: string;
}

export function PlayerHeadshot({ src, alt = "", size = 40, position }: PlayerHeadshotProps) {
  const [imgSrc, setImgSrc] = useState(src || PLACEHOLDER_SRC);
  const ring = position ? getPositionColors(position).ring : "border-border";

  return (
    <img
      src={imgSrc}
      alt={alt}
      width={size}
      height={size}
      onError={() => setImgSrc(PLACEHOLDER_SRC)}
      className={`rounded-full border-2 object-cover bg-surface-2 shrink-0 ${ring}`}
      style={{ width: size, height: size }}
    />
  );
}
