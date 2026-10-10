import { useId, useRef, type KeyboardEvent } from "react";

import { useSpecular } from "./useSpecular";

export interface GlassTab {
  id: string;
  label: string;
}

interface Props {
  tabs: GlassTab[];
  value: string;
  onChange: (id: string) => void;
  /** Accessible name of the tab list. */
  label: string;
}

// WAI-ARIA tabs with a roving tabindex: arrows, Home and End move and select. The consumer renders
// the panel and can point aria-labelledby at `${prefix}-${id}`; ids are exposed through data-tab-id.
export function GlassTabs({ tabs, value, onChange, label }: Props) {
  const prefix = useId();
  const list = useRef<HTMLDivElement>(null);
  const specular = useSpecular();

  const move = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    const last = tabs.length - 1;
    const next =
      event.key === "ArrowRight" ? (index === last ? 0 : index + 1)
      : event.key === "ArrowLeft" ? (index === 0 ? last : index - 1)
      : event.key === "Home" ? 0
      : event.key === "End" ? last
      : -1;
    if (next < 0) return;
    event.preventDefault();
    onChange(tabs[next].id);
    list.current?.querySelectorAll<HTMLButtonElement>('[role="tab"]')[next]?.focus();
  };

  return (
    <div ref={list} role="tablist" aria-label={label} className="glass glass--1 glass-tabs" {...specular}>
      {tabs.map((tab, index) => {
        const selected = tab.id === value;
        return (
          <button
            key={tab.id}
            id={`${prefix}-${tab.id}`}
            data-tab-id={tab.id}
            type="button"
            role="tab"
            aria-selected={selected}
            tabIndex={selected ? 0 : -1}
            className="glass-tab"
            onClick={() => onChange(tab.id)}
            onKeyDown={(event) => move(event, index)}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
