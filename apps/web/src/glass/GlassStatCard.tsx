import type { ReactNode } from "react";

import { useSpecular } from "./useSpecular";

interface Props {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  /** Elevation tier: 1 subtle card (default), 2 interactive surface, 3 modal or popover. */
  tier?: 1 | 2 | 3;
  className?: string;
}

// Feature / stat card on glass. Text uses --eyebrow, --ink and --ink-2, which glass.contrast.test.ts
// checks against the worst-case backdrop.
export function GlassStatCard({ label, value, hint, tier = 1, className = "" }: Props) {
  const specular = useSpecular();
  return (
    <article className={`glass glass--${tier} glass-stat ${className}`.trim()} {...specular}>
      <span className="glass-stat__label">{label}</span>
      <span className="glass-stat__value">{value}</span>
      {hint && <span className="glass-stat__hint">{hint}</span>}
    </article>
  );
}
