import type { AnalysisRequest, AnalysisResponse } from "../types/analysis";

const UNREACHABLE = "Could not reach the analysis service. Nothing was saved.";
const UNEXPECTED = "The analysis service returned a response this page cannot show. Nothing was saved.";

const STATUSES = ["complete", "partial", "unavailable"];
const VERDICTS = ["legitimate", "spam", "suspected_scam", "unknown"];
const SEVERITIES = ["low", "medium", "high", "unknown"];
const COVERAGE_KEYS = ["text", "url", "conversation", "reputation"];
const COVERAGE_STATUSES = ["complete", "not_applicable", "not_run", "unavailable"];

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function oneOf(allowed: string[], value: unknown): boolean {
  return typeof value === "string" && allowed.includes(value);
}

// Runtime check of the frozen response contract, so a malformed 2xx body is an error
// instead of a half-rendered result. The aggregate risk_score must be null until a
// documented aggregate policy exists, so anything else is rejected rather than shown.
function isAnalysisResponse(value: unknown): value is AnalysisResponse {
  if (!isRecord(value) || !isRecord(value.coverage) || !isRecord(value.module_results)) return false;
  const coverage = value.coverage;
  return (
    typeof value.analysis_id === "string" &&
    oneOf(STATUSES, value.status) &&
    oneOf(VERDICTS, value.verdict) &&
    oneOf(SEVERITIES, value.severity) &&
    value.risk_score === null &&
    value.probability_calibrated === false &&
    COVERAGE_KEYS.every((key) => oneOf(COVERAGE_STATUSES, coverage[key])) &&
    Array.isArray(value.evidence) &&
    value.evidence.every(
      (item) =>
        isRecord(item) &&
        typeof item.id === "string" &&
        typeof item.indicator_type === "string" &&
        typeof item.explanation === "string",
    ) &&
    typeof value.recommendation === "string" &&
    Array.isArray(value.limitations) &&
    value.limitations.every((item) => typeof item === "string") &&
    typeof value.processing_ms === "number" &&
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
