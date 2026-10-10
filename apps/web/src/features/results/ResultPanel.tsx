import { useEffect, useRef } from "react";

import type { AnalysisResponse } from "../../types/analysis";
import {
  coverageLabel,
  coverageName,
  coverageOrder,
  severityLabel,
  statusLabel,
  verdictLabel,
  verdictNote,
} from "./labels";

function StatusBanner({ result }: { result: AnalysisResponse }) {
  if (result.status === "complete") return null;

  const named = (status: "unavailable" | "not_run") =>
    coverageOrder.filter((key) => result.coverage[key] === status).map((key) => coverageName[key]);
  const unavailable = named("unavailable");
  const notRun = named("not_run");

  return (
    <div className={`status-banner status-${result.status}`} role="status">
      <strong>{result.status === "partial" ? "Partial result" : "Checks unavailable"}</strong>
      <p>
        {result.status === "partial"
          ? "Some checks could not finish. The result below is based only on what did run."
          : "No check could give a result. This is not a clean result."}
      </p>
      {unavailable.length > 0 && <p>Unavailable: {unavailable.join(", ")}.</p>}
      {notRun.length > 0 && <p>Not run: {notRun.join(", ")}.</p>}
    </div>
  );
}

export function ResultPanel({ result }: { result: AnalysisResponse }) {
  const headingRef = useRef<HTMLHeadingElement>(null);

  // Move focus to the new result so keyboard and screen-reader users land on it.
  useEffect(() => {
    headingRef.current?.focus();
  }, [result]);

  // A result that is partial or unavailable never takes a verdict colour of its own.
  const tone = result.status === "complete" ? result.verdict : "unknown";
  const demo = result.fixture_generated || Object.values(result.module_results).some((module) => module.fixture_generated);
  const note = verdictNote[result.verdict];
  const details = Object.entries(result.module_results).filter(([, module]) => module.detail);

  return (
    <section className={`result-panel verdict-${tone}`} aria-labelledby="result-heading">
      <div className="result-title-row">
        <div>
          <span className="eyebrow">Analysis result</span>
          <h2 id="result-heading" ref={headingRef} tabIndex={-1}>{verdictLabel[result.verdict]}</h2>
        </div>
        {demo && <span className="demo-badge">Demo data</span>}
      </div>

      <StatusBanner result={result} />

      <p className="recommendation">{result.recommendation}</p>
      {note && <p className="verdict-note">{note}</p>}
      <p className="result-meta">
        <code>{result.verdict}</code> · severity <code>{result.severity}</code> · response <code>{result.status}</code>
      </p>
      <dl className="summary-list">
        <div><dt>Response</dt><dd>{statusLabel[result.status]}</dd></div>
        <div><dt>Severity</dt><dd>{severityLabel[result.severity]}</dd></div>
        <div><dt>Processing</dt><dd>{result.processing_ms} ms</dd></div>
      </dl>

      <h3 id="coverage-heading">Coverage</h3>
      <ul className="coverage-grid" aria-labelledby="coverage-heading">
        {coverageOrder.map((key) => (
          <li key={key} className={`coverage-${result.coverage[key]}`}>
            <span>{coverageName[key]}</span>
            <strong>{coverageLabel[result.coverage[key]]}</strong>
          </li>
        ))}
      </ul>
      {details.length > 0 && (
        <ul className="coverage-details">
          {details.map(([name, module]) => (
            <li key={name}><strong>{name}:</strong> {module.detail}</li>
          ))}
        </ul>
      )}

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
                <p><strong>Observed:</strong> <code>{String(item.observed_value)}</code></p>
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
        {result.limitations.map((limitation, index) => <li key={index}>{limitation}</li>)}
      </ul>
    </section>
  );
}
