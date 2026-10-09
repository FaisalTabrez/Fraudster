export type Source = "manual" | "screenshot" | "qr" | "conversation";
export type Verdict = "legitimate" | "spam" | "suspected_scam" | "unknown";
export type Severity = "low" | "medium" | "high" | "unknown";
export type AnalysisStatus = "complete" | "partial" | "unavailable";
export type CoverageStatus = "complete" | "not_applicable" | "not_run" | "unavailable";

export interface ConversationMessage {
  id: string;
  sender_id: string;
  text: string;
  timestamp?: string;
}

export interface AnalysisRequest {
  text?: string;
  urls: string[];
  messages: ConversationMessage[];
  sender_id?: string;
  conversation_id?: string;
  source: Source;
}

export interface Evidence {
  id: string;
  indicator_type: string;
  source_module: "text" | "url" | "conversation" | "reputation";
  quote?: string | null;
  observed_value?: string | number | boolean | null;
  message_id?: string | null;
  explanation: string;
}

export interface ModuleResult {
  status: CoverageStatus;
  version: string;
  raw_score_type: string;
  verdict: Verdict;
  severity: Severity;
  score?: number | null;
  evidence: Evidence[];
  detail?: string | null;
  fixture_generated: boolean;
}

export interface AnalysisResponse {
  analysis_id: string;
  status: AnalysisStatus;
  verdict: Verdict;
  severity: Severity;
  risk_score: null;
  probability_calibrated: false;
  evidence: Evidence[];
  coverage: Record<"text" | "url" | "conversation" | "reputation", CoverageStatus>;
  module_results: Record<string, ModuleResult>;
  recommendation: string;
  limitations: string[];
  versions: Record<string, string>;
  processing_ms: number;
  fixture_generated: boolean;
}
