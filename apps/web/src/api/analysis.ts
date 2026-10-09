import type { AnalysisRequest, AnalysisResponse } from "../types/analysis";

export async function analyze(payload: AnalysisRequest): Promise<AnalysisResponse> {
  const response = await fetch("/api/v1/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

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

  return (await response.json()) as AnalysisResponse;
}
