import "@fontsource-variable/public-sans";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import "./styles/tokens.css";
import "./styles/components.css";
import "./glass/glass.css";
import "./styles.css";

const root = createRoot(document.getElementById("root")!);

// ?preview=glass shows the glass layer on its ambient stage. Dev only: the dynamic import sits
// behind import.meta.env.DEV, so the preview is not part of the production bundle.
if (import.meta.env.DEV && new URLSearchParams(location.search).get("preview") === "glass") {
  void import("./glass/GlassShowcase").then(({ GlassShowcase }) => {
    root.render(
      <StrictMode>
        <GlassShowcase />
      </StrictMode>,
    );
  });
} else {
  root.render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
}
