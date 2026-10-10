import type { IconName } from "../../components/Icon";
import type { AnalysisStatus, CoverageStatus, Severity, Verdict } from "../../types/analysis";

// Plain-language labels. The API enums stay visible only inside Technical details.
// There is deliberately no "safe" wording: an absent warning is not a clean result.
export const verdictLabel: Record<Verdict, string> = {
  suspected_scam: "Potential scam",
  spam: "Likely promotional",
  legitimate: "No strong warning found",
  unknown: "Unable to assess",
};

// Each verdict differs by tone, border style and icon shape, never by colour alone.
export type Tone = "scam" | "promo" | "clear" | "unknown";

export const verdictTone: Record<Verdict, Tone> = {
  suspected_scam: "scam",
  spam: "promo",
  legitimate: "clear",
  unknown: "unknown",
};

export const verdictIcon: Record<Verdict, IconName> = {
  suspected_scam: "verdict-scam",
  spam: "verdict-promotional",
  legitimate: "verdict-no-warning",
  unknown: "verdict-unable",
};

// The action leads every result. It tells people what to do, not what the model thinks.
export const actionHeadline: Record<Verdict, string> = {
  suspected_scam: "Pause. Don't reply, pay, or share codes yet.",
  spam: "Treat this as marketing. Don't share codes or pay.",
  legitimate: "No strong warning found. Still verify anything you didn't expect.",
  unknown: "We couldn't assess this. Verify independently before you act.",
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
  complete: "Checked",
  not_applicable: "Not applicable",
  not_run: "Not run",
  unavailable: "Unavailable",
};

export const coverageIcon: Record<CoverageStatus, IconName> = {
  complete: "check-ran",
  not_applicable: "check-not-applicable",
  not_run: "check-not-run",
  unavailable: "coverage-partial",
};

// Fixed display order so all four coverage fields always appear in the same place.
export const coverageOrder = ["text", "url", "conversation", "reputation"] as const;
export type CoverageKey = (typeof coverageOrder)[number];

export const moduleName: Record<CoverageKey, string> = {
  text: "Message wording",
  url: "Link structure",
  conversation: "Conversation pattern",
  reputation: "Sender reputation",
};

// "secret_request" -> "Secret request"
export function indicatorTitle(indicator: string): string {
  const spaced = indicator.replaceAll("_", " ");
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}
