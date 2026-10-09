import { useState } from "react";

import { analyze } from "./api/analysis";
import { IngestionStatus } from "./features/ingestion/IngestionStatus";
import { ResultPanel } from "./features/results/ResultPanel";
import { ScanForm } from "./features/scan/ScanForm";
import type { AnalysisRequest, AnalysisResponse } from "./types/analysis";

export default function App() {
  const [result, setResult] = useState<AnalysisResponse | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (payload: AnalysisRequest) => {
    setBusy(true);
    setError("");
    try {
      setResult(await analyze(payload));
    } catch (requestError) {
      setResult(null);
      setError(requestError instanceof Error ? requestError.message : "Analysis could not be completed.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <main>
      <header className="hero">
        <div className="hero-mark" aria-hidden="true">F</div>
        <div>
          <span className="eyebrow">Fraudster prototype</span>
          <h1>Explain the warning before asking for trust</h1>
          <p>
            Analyze pasted text, URL strings, and only the conversation history you choose to provide.
            Coverage gaps stay visible instead of becoming a zero-risk score.
          </p>
        </div>
      </header>

      <div className="workspace">
        <ScanForm busy={busy} onSubmit={submit} />
        <aside className="result-column">
          {error && <p className="request-error" role="alert">{error}</p>}
          {result ? (
            <ResultPanel result={result} />
          ) : (
            <section className="empty-result">
              <span className="eyebrow">Evidence-first output</span>
              <h2>No analysis yet</h2>
              <p>Results will show category, coverage, exact evidence, limitations, and the next safe action.</p>
            </section>
          )}
          <IngestionStatus />
        </aside>
      </div>
    </main>
  );
}
