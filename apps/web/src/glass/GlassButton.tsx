import type { ButtonHTMLAttributes } from "react";

import { useSpecular } from "./useSpecular";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  /** "glass" is translucent with brand text; "primary" is brand-tinted glass with on-brand text. */
  variant?: "glass" | "primary";
}

export function GlassButton({ variant = "glass", className = "", type = "button", ...rest }: Props) {
  const specular = useSpecular();
  return (
    <button
      type={type}
      data-interactive=""
      className={`glass glass--2 glass-btn ${variant === "primary" ? "glass-btn--primary" : ""} ${className}`.trim()}
      {...specular}
      {...rest}
    />
  );
}
