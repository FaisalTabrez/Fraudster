import type { AnalysisResponse, CoverageStatus } from "../../types/analysis";

const coverageLabel: Record<CoverageStatus, string> = {
  complete: "Complete",
  not_applicable: "Not applicable",
  not_run: "Not run",
  unavailable: "Unavailable",
};

export function ResultPanel({ result }: { result: AnalysisResponse }) {
  return (
    <section className={`result-panel verdict-${result.verdict}`} aria-live="polite">
      <div className="result-title-row">
        <div>
          <span className="eyebrow">Analysis result</span>
          <h2>{result.verdict.replace("_", " ")}</h2>
        </div>
        {result.fixture_generated && <span className="demo-badge">Demo data</span>}
      </div>

      <p className="recommendation">{result.recommendation}</p>
      <dl className="summary-list">
        <div><dt>Response</dt><dd>{result.status}</dd></div>
        <div><dt>Severity</dt><dd>{result.severity}</dd></div>
        <div><dt>Processing</dt><dd>{result.processing_ms} ms</dd></div>
      </dl>

      {result.risk_score !== null && (
        <p className="aggregate-score">Aggregate risk score: {result.risk_score}</p>
      )}

      <h3>Coverage</h3>
      <ul className="coverage-grid">
        {Object.entries(result.coverage).map(([name, coverage]) => (
          <li key={name} className={`coverage-${coverage}`}>
            <span>{name}</span>
            <strong>{coverageLabel[coverage]}</strong>
          </li>
        ))}
      </ul>

      <h3>Evidence</h3>
      {result.evidence.length ? (
        <div className="evidence-grid">
          {result.evidence.map((item) => (
            <article className="evidence-card" key={item.id}>
              <div className="evidence-meta">
                <span>{item.source_module}</span>
                <span>{item.indicator_type.replaceAll("_", " ")}</span>
              </div>
              {item.quote && <blockquote>“{item.quote}”</blockquote>}
              {item.observed_value !== undefined && item.observed_value !== null && (
                <p><strong>Observed:</strong> {String(item.observed_value)}</p>
              )}
              {item.message_id && <p><strong>Message ID:</strong> {item.message_id}</p>}
              <p>{item.explanation}</p>
            </article>
          ))}
        </div>
      ) : (
        <p className="empty-state">No grounded evidence was available.</p>
      )}

      <h3>Limitations</h3>
      <ul className="limitations">
        {result.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}
      </ul>
    </section>
  );
}
