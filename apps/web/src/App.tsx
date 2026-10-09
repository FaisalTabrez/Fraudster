import { useState } from "react";

import { analyze } from "./api/analysis";
import { Icon } from "./components/Icon";
import { LogoMark } from "./components/Logo";
import { IngestionStatus } from "./features/ingestion/IngestionStatus";
import { ResultPanel } from "./features/results/ResultPanel";
import { ScanForm } from "./features/scan/ScanForm";
import type { AnalysisRequest, AnalysisResponse } from "./types/analysis";

// The result is kept with the exact request it answers, so evidence message IDs resolve
// against what was analysed even if the form is edited afterwards.
interface Analysis {
  request: AnalysisRequest;
  result: AnalysisResponse;
}

export default function App() {
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (payload: AnalysisRequest) => {
    setBusy(true);
    setError("");
    try {
      setAnalysis({ request: payload, result: await analyze(payload) });
    } catch (requestError) {
      setAnalysis(null);
      setError(requestError instanceof Error ? requestError.message : "Analysis could not be completed.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fr app">
      <header className="fr-header app-header">
        <div className="fr-brand">
          <LogoMark size={40} />
          <span className="wordmark">Fraudster</span>
        </div>
      </header>

      <main className="app-main">
        <div className="app-intro">
          <h1 className="page-title">Check it before you act on it.</h1>
          <p className="lead">
            Paste a message, a link or a conversation. You get what to do next, the evidence, and a plain account of
            what could not be checked.
          </p>
        </div>

        <div className="app-grid">
          <ScanForm busy={busy} onSubmit={submit} />

          <section className="app-result" aria-label="Result">
            {error && (
              <p className="fr-banner fr-banner--unavailable" role="alert">
                <Icon name="coverage-unavailable" />
                {error}
              </p>
            )}
            {analysis ? (
              <ResultPanel result={analysis.result} messages={analysis.request.messages} />
            ) : (
              <div className="fr-card empty-result">
                <p className="fr-eyebrow">Step 2</p>
                <h2 className="fr-h2">No analysis yet</h2>
                <p className="lead">
                  Your result appears here: what to do now, the strongest evidence, what we checked, and the limits.
                </p>
              </div>
            )}
            <IngestionStatus />
          </section>
        </div>
      </main>
    </div>
  );
}
