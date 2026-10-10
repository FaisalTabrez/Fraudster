import { useEffect, useRef } from "react";

import { Icon } from "../../components/Icon";
import type { AnalysisResponse, ConversationMessage, Evidence } from "../../types/analysis";
import {
  actionHeadline,
  coverageIcon,
  coverageLabel,
  coverageOrder,
  indicatorTitle,
  moduleName,
  severityLabel,
  statusLabel,
  verdictIcon,
  verdictLabel,
  verdictTone,
} from "./labels";

// ActionCard foot, right side. It always hedges: a result is never a guarantee.
function actionMeta(result: AnalysisResponse): string {
  if (result.status === "unavailable") return "No checks completed";
  if (result.verdict === "unknown") return "Not a clean result";
  const parts: string[] = [];
  if (result.verdict === "suspected_scam") {
    parts.push(`${result.evidence.length} warning ${result.evidence.length === 1 ? "sign" : "signs"} found`);
  }
  if (result.severity !== "unknown") parts.push(`${severityLabel[result.severity]} severity`);
  parts.push("Not a guarantee");
  return parts.join(" · ");
}

// Coverage banner under the action card: names what did not run and what the result rests on.
function CoverageBanner({ result }: { result: AnalysisResponse }) {
  if (result.status === "complete") return null;

  const named = (status: "unavailable" | "not_run") =>
    coverageOrder.filter((key) => result.coverage[key] === status).map((key) => moduleName[key]);
  const unavailable = named("unavailable");
  const notRun = named("not_run");
  const partial = result.status === "partial";

  return (
    <div className={`fr-banner fr-banner--${result.status}`} role="status">
      <Icon name={partial ? "coverage-partial" : "coverage-unavailable"} />
      <div>
        <strong>{partial ? "Partial result." : "Checks unavailable."}</strong>{" "}
        {partial
          ? "Some checks could not finish. The result below is based only on what did run."
          : "No check could give a result. This is not a clean result."}
        {unavailable.length > 0 && <div>Unavailable: {unavailable.join(", ")}.</div>}
        {notRun.length > 0 && <div>Not run: {notRun.join(", ")}.</div>}
      </div>
    </div>
  );
}

// Evidence from a pasted conversation names the exact message it came from, resolved against
// the request that was actually submitted, so the lookup survives later edits to the form.
function MessageReference({ id, quote, messages }: { id: string; quote?: string | null; messages: ConversationMessage[] }) {
  const message = messages.find((candidate) => candidate.id === id);
  if (!message) {
    return <p className="message-ref">Message <code className="fr-mono">{id}</code> is not part of the submitted conversation.</p>;
  }
  return (
    <>
      <p className="message-ref"><strong>Message <code className="fr-mono">{id}</code> - {message.sender_id}</strong></p>
      {quote !== message.text && <blockquote className="source-message">{message.text}</blockquote>}
    </>
  );
}

function EvidenceItem({ item, number, messages }: { item: Evidence; number: number; messages: ConversationMessage[] }) {
  return (
    <li className="fr-evidence">
      <span className="fr-evidence__num" aria-hidden="true">{number}</span>
      <div className="fr-evidence__body">
        <span className="fr-evidence__title">{indicatorTitle(item.indicator_type)}</span>
        {item.quote && <blockquote className="fr-quote"><mark className="fr-mark">“{item.quote}”</mark></blockquote>}
        {item.observed_value !== undefined && item.observed_value !== null && (
          <p className="fr-evidence__why"><strong>Observed:</strong> <code className="fr-mono">{String(item.observed_value)}</code></p>
        )}
        {item.message_id && <MessageReference id={item.message_id} quote={item.quote} messages={messages} />}
        <p className="fr-evidence__why">{item.explanation}</p>
        <div className="tag-row">
          <span className="fr-tag">{moduleName[item.source_module]}</span>
          <span className="fr-tag fr-mono">{item.indicator_type}</span>
        </div>
      </div>
    </li>
  );
}

interface ResultPanelProps {
  result: AnalysisResponse;
  /** The messages that were actually submitted, used to resolve evidence message IDs. */
  messages?: ConversationMessage[];
}

export function ResultPanel({ result, messages = [] }: ResultPanelProps) {
  const headingRef = useRef<HTMLHeadingElement>(null);

  // Move focus to the new result so keyboard and screen-reader users land on it.
  useEffect(() => {
    headingRef.current?.focus();
  }, [result]);

  // A result that is partial or unavailable never takes a verdict tone of its own.
  const tone = result.status === "complete" ? verdictTone[result.verdict] : "unknown";
  const demo = result.fixture_generated || Object.values(result.module_results).some((module) => module.fixture_generated);
  const shown = result.evidence.slice(0, 3);
  const more = result.evidence.slice(3);
  const applicable = coverageOrder.filter((key) => result.coverage[key] !== "not_applicable");
  const ran = applicable.filter((key) => result.coverage[key] === "complete");
  const modules = Object.entries(result.module_results);

  return (
    <div className="result-stack">
      {demo && (
        <div className="fr-banner fr-banner--demo demo-sticky" role="status">
          <Icon name="demo-data" />
          <span><strong>Demo data</strong> · not live detection</span>
        </div>
      )}

      <section className={`fr-action fr-tone-${tone}`} aria-labelledby="result-heading">
        <p className="fr-eyebrow">What to do now</p>
        <h2 id="result-heading" ref={headingRef} tabIndex={-1} className="fr-action__title">
          {result.status !== "complete" && result.verdict === "legitimate"
            ? "Only some checks ran. Verify before you act."
            : actionHeadline[result.verdict]}
        </h2>
        <p className="fr-action__body">{result.recommendation}</p>
        <div className="fr-action__foot">
          <span className="fr-action__verdict"><Icon name={verdictIcon[result.verdict]} size={22} />{verdictLabel[result.verdict]}</span>
          <span className="fr-action__meta">{actionMeta(result)}</span>
        </div>
      </section>

      <CoverageBanner result={result} />

      <section className="fr-card result-card" aria-labelledby="evidence-heading">
        <h3 id="evidence-heading" className="fr-h2">{result.verdict === "suspected_scam" ? "Why we're warning you" : "Evidence"}</h3>
        {shown.length ? (
          <>
            <ol className="evidence-list">
              {shown.map((item, index) => <EvidenceItem key={item.id} item={item} number={index + 1} messages={messages} />)}
            </ol>
            {more.length > 0 && (
              <details className="more-evidence">
                <summary>Show {more.length} more</summary>
                <ol className="evidence-list" start={shown.length + 1}>
                  {more.map((item, index) => <EvidenceItem key={item.id} item={item} number={shown.length + index + 1} messages={messages} />)}
                </ol>
              </details>
            )}
          </>
        ) : (
          <p className="empty-state">No grounded evidence was available.</p>
        )}
      </section>

      <section className="fr-card result-card" aria-labelledby="coverage-heading">
        <div className="card-head">
          <h3 id="coverage-heading" className="fr-h2">What we checked</h3>
          <span className="fr-hint">{ran.length} of {applicable.length} applicable {applicable.length === 1 ? "check" : "checks"} ran</span>
        </div>
        <ul className="fr-coverage" aria-labelledby="coverage-heading">
          {coverageOrder.map((key) => {
            const status = result.coverage[key];
            const note = result.module_results[key]?.detail;
            return (
              <li key={key} className={`fr-row ${status === "unavailable" ? "fr-row--unavailable" : ""}`.trim()}>
                <div>
                  <div className="fr-row__name">{moduleName[key]}</div>
                  {note && <div className="fr-row__note">{note}</div>}
                </div>
                <span className={`fr-status ${status === "complete" ? "fr-status--checked" : status === "unavailable" ? "fr-status--unavailable" : ""}`.trim()}>
                  <Icon name={coverageIcon[status]} size={18} />{coverageLabel[status]}
                </span>
              </li>
            );
          })}
        </ul>
      </section>

      <section className="fr-card result-card" aria-labelledby="limits-heading">
        <h3 id="limits-heading" className="fr-h2">Limits of this result</h3>
        <ul className="fr-list">
          {result.limitations.map((limitation, index) => <li key={index}>{limitation}</li>)}
        </ul>
      </section>

      <details className="fr-card fr-details">
        <summary>
          <span>Technical details</span>
          <span className="fr-hint fr-mono">{modules.length} {modules.length === 1 ? "module" : "modules"} · {result.processing_ms} ms</span>
        </summary>
        <table>
          <tbody>
            <tr><th scope="row">Verdict</th><td>{result.verdict}</td></tr>
            <tr><th scope="row">Severity</th><td>{result.severity}</td></tr>
            <tr><th scope="row">Response</th><td>{result.status} ({statusLabel[result.status]})</td></tr>
            <tr><th scope="row">Analysis ID</th><td>{result.analysis_id}</td></tr>
            {Object.entries(result.versions).map(([name, version]) => (
              <tr key={`version-${name}`}><th scope="row">Version · {name}</th><td>{version}</td></tr>
            ))}
            {modules.map(([name, module]) => (
              <tr key={`module-${name}`}>
                <th scope="row">Module · {name}</th>
                <td>{module.status} · {module.version} · {module.raw_score_type}{module.detail ? ` · ${module.detail}` : ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="fr-hint details-note">Scores are not probabilities. No overall percentage is calculated.</p>
      </details>
    </div>
  );
}
