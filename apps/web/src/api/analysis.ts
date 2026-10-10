import type { AnalysisRequest, AnalysisResponse } from "../types/analysis";

const UNREACHABLE = "Could not reach the analysis service. Nothing was saved.";
const UNEXPECTED = "The analysis service returned a response this page cannot show. Nothing was saved.";

const STATUSES = ["complete", "partial", "unavailable"];
const VERDICTS = ["legitimate", "spam", "suspected_scam", "unknown"];
const SEVERITIES = ["low", "medium", "high", "unknown"];
const COVERAGE_KEYS = ["text", "url", "conversation", "reputation"];
const COVERAGE_STATUSES = ["complete", "not_applicable", "not_run", "unavailable"];
const SOURCE_MODULES = ["text", "url", "conversation", "reputation"];

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function oneOf(allowed: string[], value: unknown): boolean {
  return typeof value === "string" && allowed.includes(value);
}

function isString(value: unknown, min = 0, max = Infinity): value is string {
  return typeof value === "string" && value.length >= min && value.length <= max;
}

function isNonBlank(value: unknown, max = Infinity): value is string {
  return isString(value, 1, max) && value.trim() !== "";
}

function isAbsentOr(value: unknown, check: (candidate: unknown) => boolean): boolean {
  return value === undefined || value === null || check(value);
}

// One evidence item, checked field by field against contracts/analysis-response.schema.json.
// The contract also requires a nonblank quote or an actual observed value, so an item with
// neither is rejected instead of being rendered as an empty card.
function isEvidence(value: unknown): boolean {
  if (!isRecord(value)) return false;
  const { quote, observed_value: observed } = value;
  const hasObserved = isNonBlank(observed) || typeof observed === "boolean" || (typeof observed === "number" && Number.isFinite(observed));
  return (
    isString(value.id, 1, 128) &&
    isString(value.indicator_type, 1, 64) &&
    oneOf(SOURCE_MODULES, value.source_module) &&
    isAbsentOr(quote, (candidate) => isNonBlank(candidate, 2000)) &&
    isAbsentOr(observed, () => hasObserved) &&
    isAbsentOr(value.message_id, (candidate) => isString(candidate, 0, 128)) &&
    isString(value.explanation, 1, 500) &&
    (isNonBlank(quote, 2000) || hasObserved)
  );
}

// A list of evidence that also honours the contract rule that a suspected-scam verdict
// needs at least one item. Showing that warning with "no grounded evidence" is not allowed.
function hasValidEvidence(evidence: unknown, verdict: unknown): boolean {
  return Array.isArray(evidence) && evidence.every(isEvidence) && (verdict !== "suspected_scam" || evidence.length > 0);
}

// One entry of module_results. The result panel reads fixture_generated, detail and the
// module's evidence, so every field of the entry is checked, including null entries.
function isModuleResult(value: unknown): boolean {
  if (!isRecord(value)) return false;
  return (
    oneOf(COVERAGE_STATUSES, value.status) &&
    isString(value.version, 1) &&
    isString(value.raw_score_type, 1) &&
    oneOf(VERDICTS, value.verdict) &&
    oneOf(SEVERITIES, value.severity) &&
    (value.score === null || (typeof value.score === "number" && Number.isFinite(value.score))) &&
    hasValidEvidence(value.evidence, value.verdict) &&
    isAbsentOr(value.detail, (candidate) => isString(candidate, 0, 300)) &&
    typeof value.fixture_generated === "boolean"
  );
}

// Runtime check of the frozen response contract, so a malformed 2xx body is an error
// instead of a half-rendered result or a crash while rendering. The aggregate risk_score
// must be null until a documented aggregate policy exists, so anything else is rejected
// rather than shown.
function isAnalysisResponse(value: unknown): value is AnalysisResponse {
  if (!isRecord(value) || !isRecord(value.coverage) || !isRecord(value.module_results) || !isRecord(value.versions)) return false;
  const coverage = value.coverage;
  return (
    isString(value.analysis_id, 1) &&
    oneOf(STATUSES, value.status) &&
    oneOf(VERDICTS, value.verdict) &&
    oneOf(SEVERITIES, value.severity) &&
    value.risk_score === null &&
    value.probability_calibrated === false &&
    COVERAGE_KEYS.every((key) => oneOf(COVERAGE_STATUSES, coverage[key])) &&
    hasValidEvidence(value.evidence, value.verdict) &&
    Object.values(value.module_results).every(isModuleResult) &&
    Object.values(value.versions).every((version) => isString(version)) &&
    isString(value.recommendation, 1) &&
    Array.isArray(value.limitations) &&
    value.limitations.every((item) => isString(item, 1)) &&
    typeof value.processing_ms === "number" &&
    Number.isInteger(value.processing_ms) &&
    value.processing_ms >= 0 &&
    typeof value.fixture_generated === "boolean"
  );
}

export async function analyze(payload: AnalysisRequest): Promise<AnalysisResponse> {
  let response: Response;
  try {
    response = await fetch("/api/v1/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    // Do not surface the browser's raw network error text.
    throw new Error(UNREACHABLE);
  }

  if (!response.ok) {
    let message = `Analysis request failed with HTTP ${response.status}`;
    try {
      const error = (await response.json()) as { detail?: string | Array<{ msg?: string }> };
      if (typeof error.detail === "string") message = error.detail;
      if (Array.isArray(error.detail)) {
        message = error.detail.map((item) => item.msg ?? "Invalid input").join("; ");
      }
    } catch {
      // Keep the status-only message. Never expose a raw server stack trace.
    }
    throw new Error(message);
  }

  let body: unknown;
  try {
    body = await response.json();
  } catch {
    throw new Error(UNEXPECTED);
  }
  if (!isAnalysisResponse(body)) throw new Error(UNEXPECTED);
  return body;
}
