import type { AnalysisStatus, CoverageStatus, Severity, Verdict } from "../../types/analysis";

// Plain-language labels. The API enums stay visible only in the monospace meta line.
// There is deliberately no "safe" wording: an absent warning is not a clean result.
export const verdictLabel: Record<Verdict, string> = {
  suspected_scam: "Potential scam",
  spam: "Likely promotional",
  legitimate: "No strong warning found",
  unknown: "Unable to assess",
};

export const verdictNote: Partial<Record<Verdict, string>> = {
  legitimate: "This is not a guarantee. Still verify anything you did not expect.",
  unknown: "This is not a clean result. Verify independently before acting.",
};

export const severityLabel: Record<Severity, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
  unknown: "Unknown",
};

export const statusLabel: Record<AnalysisStatus, string> = {
  complete: "Complete",
  partial: "Partial",
  unavailable: "Unavailable",
};

export const coverageLabel: Record<CoverageStatus, string> = {
  complete: "Complete",
  not_applicable: "Not applicable",
  not_run: "Not run",
  unavailable: "Unavailable",
};

// Fixed display order so all four coverage fields always appear in the same place.
export const coverageOrder = ["text", "url", "conversation", "reputation"] as const;

export const coverageName: Record<(typeof coverageOrder)[number], string> = {
  text: "Text",
  url: "URLs",
  conversation: "Conversation",
  reputation: "Reputation",
};
