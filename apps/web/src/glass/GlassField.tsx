import { useId, type InputHTMLAttributes } from "react";

import { useSpecular } from "./useSpecular";

interface Props extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  hint?: string;
  error?: string;
}

// Labelled glass input. The hint and error are tied to the input with aria-describedby, and an
// error sets aria-invalid, which also tints the rim with --scam-fg (never colour alone: the text
// error is shown too).
export function GlassField({ label, hint, error, id, className = "", ...rest }: Props) {
  const generated = useId();
  const inputId = id ?? generated;
  const hintId = hint ? `${inputId}-hint` : undefined;
  const errorId = error ? `${inputId}-error` : undefined;
  const specular = useSpecular();

  return (
    <div className="glass-field">
      <label htmlFor={inputId}>{label}</label>
      <div className="glass glass--2 glass-field__control" {...specular}>
        <input
          id={inputId}
          className={className}
          aria-invalid={error ? true : undefined}
          aria-describedby={[hintId, errorId].filter(Boolean).join(" ") || undefined}
          {...rest}
        />
      </div>
      {hint && <span id={hintId} className="glass-field__hint">{hint}</span>}
      {error && <span id={errorId} className="glass-field__error">{error}</span>}
    </div>
  );
}
