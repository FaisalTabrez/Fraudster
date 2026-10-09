import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { AnalysisResponse } from "../../types/analysis";
import { ResultPanel } from "./ResultPanel";

const result: AnalysisResponse = {
  analysis_id: "fixture-test",
  status: "partial",
  verdict: "unknown",
  severity: "unknown",
  risk_score: null,
  probability_calibrated: false,
  evidence: [],
  coverage: {
    text: "complete",
    url: "unavailable",
    conversation: "not_applicable",
    reputation: "not_run",
  },
  module_results: {},
  recommendation: "Verify independently.",
  limitations: ["URL analysis was unavailable."],
  versions: { gateway: "0.1.0" },
  processing_ms: 12,
  fixture_generated: true,
};

describe("ResultPanel", () => {
  it("keeps a null aggregate score absent and shows unavailable coverage", () => {
    render(<ResultPanel result={result} />);
    expect(screen.queryByText(/aggregate risk score/i)).not.toBeInTheDocument();
    expect(screen.getByText("Demo data")).toBeInTheDocument();
    expect(screen.getByText("Unavailable")).toBeInTheDocument();
    expect(screen.queryByText(/0%/)).not.toBeInTheDocument();
  });
});
