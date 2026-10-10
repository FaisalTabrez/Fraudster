import type { PointerEvent } from "react";

// Moves the specular highlight (.glass::after) to follow the pointer by setting --mx / --my on the
// element. It only writes two CSS variables, so React does not re-render, and it resets when the
// pointer leaves. Keyboard focus keeps the default highlight position.
export function useSpecular() {
  return {
    onPointerMove(event: PointerEvent<HTMLElement>) {
      const element = event.currentTarget;
      const box = element.getBoundingClientRect();
      if (!box.width || !box.height) return;
      element.style.setProperty("--mx", `${((event.clientX - box.left) / box.width) * 100}%`);
      element.style.setProperty("--my", `${((event.clientY - box.top) / box.height) * 100}%`);
    },
    onPointerLeave(event: PointerEvent<HTMLElement>) {
      event.currentTarget.style.removeProperty("--mx");
      event.currentTarget.style.removeProperty("--my");
    },
  };
}
