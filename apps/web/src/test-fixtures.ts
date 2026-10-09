import type { AnalysisResponse } from "./types/analysis";

// Test-only copies of the response shapes in contracts/examples/. They are typed here so the
// web tests do not import from, or depend on edits to, the frozen contracts directory.
// All values are synthetic demo data, not model output.

export const fixtureScamResponse: AnalysisResponse = {
  analysis_id: "fixture-example-1",
  status: "complete",
  verdict: "suspected_scam",
  severity: "high",
  risk_score: null,
  probability_calibrated: false,
  evidence: [
    {
      id: "fixture-text-example",
      indicator_type: "secret_request",
      source_module: "text",
      quote: "Send your OTP",
      observed_value: null,
      message_id: null,
      explanation: "Fixture rule matched a request to disclose a secret.",
    },
  ],
  coverage: { text: "complete", url: "not_applicable", conversation: "not_applicable", reputation: "not_run" },
  module_results: {
    text: {
      status: "complete",
      version: "fixture-text-0.1.0",
      raw_score_type: "fixture_rule_hits",
      verdict: "suspected_scam",
      severity: "high",
      score: 1,
      evidence: [],
      detail: null,
      fixture_generated: true,
    },
  },
  recommendation: "Verify independently before responding.",
  limitations: ["Detector outputs are fixture-generated demo data, not live inference."],
  versions: { gateway: "0.1.0", text: "fixture-text-0.1.0" },
  processing_ms: 2,
  fixture_generated: true,
};

export const unavailableResponse: AnalysisResponse = {
  analysis_id: "unavailable-example-1",
  status: "unavailable",
  verdict: "unknown",
  severity: "unknown",
  risk_score: null,
  probability_calibrated: false,
  evidence: [],
  coverage: { text: "unavailable", url: "not_applicable", conversation: "not_applicable", reputation: "not_run" },
  module_results: {
    text: {
      status: "unavailable",
      version: "not_available",
      raw_score_type: "none",
      verdict: "unknown",
      severity: "unknown",
      score: null,
      evidence: [],
      detail: "text service returned HTTP 503",
      fixture_generated: false,
    },
  },
  recommendation: "Some checks were unavailable. Verify independently before acting.",
  limitations: ["Unavailable checks: text."],
  versions: { gateway: "0.1.0", text: "not_available" },
  processing_ms: 8,
  fixture_generated: false,
};

// Derived shapes the contract allows but the examples do not show.
export const partialResponse: AnalysisResponse = {
  ...unavailableResponse,
  analysis_id: "partial-test-1",
  status: "partial",
  coverage: { text: "complete", url: "unavailable", conversation: "not_applicable", reputation: "not_run" },
  module_results: {},
  limitations: ["URL analysis was unavailable."],
};

export const noWarningResponse: AnalysisResponse = {
  ...fixtureScamResponse,
  analysis_id: "no-warning-test-1",
  verdict: "legitimate",
  severity: "low",
  evidence: [],
  module_results: {},
  recommendation: "Nothing stood out in the checks that ran.",
  limitations: ["Nothing stood out in the checks that ran."],
  fixture_generated: false,
};
