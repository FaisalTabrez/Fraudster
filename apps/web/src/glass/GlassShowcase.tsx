import { useState } from "react";

import { GlassButton, GlassField, GlassStatCard, GlassTabs } from "./index";
import { useSpecular } from "./useSpecular";

// Dev-only preview of the glass layer on its ambient stage. Open the app with ?preview=glass.
// It is loaded dynamically behind import.meta.env.DEV, so it is not part of the production bundle.
export function GlassShowcase() {
  const [tab, setTab] = useState("message");
  const [value, setValue] = useState("");
  const popover = useSpecular();

  return (
    <div className="fr glass-stage" style={{ minHeight: "100vh", padding: "48px 32px" }}>
      <div style={{ maxWidth: 1080, margin: "0 auto", display: "grid", gap: 32 }}>
        <header style={{ display: "grid", gap: 8 }}>
          <p className="fr-eyebrow">Glass layer preview</p>
          <h1 style={{ margin: 0, fontSize: 40, lineHeight: 1.1, letterSpacing: "-0.02em" }}>Frosted surfaces on brand light</h1>
          <p style={{ margin: 0, color: "var(--ink-2)", maxWidth: 640 }}>
            Three elevation tiers over a soft brand glow. Verdicts, evidence and coverage stay flat and solid in the real app.
          </p>
        </header>

        <section aria-label="Stat cards" style={{ display: "grid", gap: 20, gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))" }}>
          <GlassStatCard tier={1} label="Tier 1 · card" value="2 of 2" hint="applicable checks ran" />
          <GlassStatCard tier={2} label="Tier 2 · interactive" value="20" hint="messages per conversation" />
          <GlassStatCard tier={3} label="Tier 3 · popover" value="5 MB" hint="screenshot upload limit" />
        </section>

        <section aria-label="Controls" style={{ display: "grid", gap: 24 }}>
          <GlassTabs
            label="Type of content"
            value={tab}
            onChange={setTab}
            tabs={[
              { id: "message", label: "Message" },
              { id: "link", label: "Link" },
              { id: "conversation", label: "Conversation" },
            ]}
          />
          <div style={{ display: "grid", gap: 20, gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", alignItems: "start" }}>
            <GlassField label="Sender ID" hint="Compared exactly as typed, including spaces." placeholder="sender-a" value={value} onChange={(event) => setValue(event.target.value)} />
            <GlassField label="Link" error="Enter at least one link." placeholder="https://example.test" />
          </div>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            <GlassButton variant="primary">Check this message</GlassButton>
            <GlassButton>Add supplied message</GlassButton>
            <GlassButton disabled>Disabled</GlassButton>
          </div>
        </section>

        <section aria-label="Popover" className="glass glass--3" style={{ padding: 24, maxWidth: 420 }} {...popover}>
          <h2 style={{ margin: "0 0 6px", fontSize: 20 }}>Tier 3 surface</h2>
          <p style={{ margin: 0, color: "var(--ink-2)" }}>The most opaque tier, for modals and popovers that must stay readable over anything.</p>
        </section>
      </div>
    </div>
  );
}
