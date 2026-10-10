import { afterEach, describe, expect, it, vi } from "vitest";

import { fixtureScamResponse, partialResponse, unavailableResponse } from "../test-fixtures";
import type { AnalysisRequest, Evidence, ModuleResult } from "../types/analysis";
import { analyze } from "./analysis";

const request: AnalysisRequest = { text: "Synthetic test message", urls: [], messages: [], source: "manual" };

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("analyze", () => {
  it("posts JSON to the same-origin /api gateway route and returns the response", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(fixtureScamResponse));
    vi.stubGlobal("fetch", fetchMock);

    await expect(analyze(request)).resolves.toEqual(fixtureScamResponse);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/v1/analyze");
    expect(init.method).toBe("POST");
    expect(init.headers).toEqual({ "Content-Type": "application/json" });
    expect(JSON.parse(init.body as string)).toEqual(request);
  });

  it("accepts an unavailable response as a normal result", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(unavailableResponse)));
    await expect(analyze(request)).resolves.toMatchObject({ status: "unavailable", risk_score: null });
  });

  it("turns a string validation detail into the error message", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ detail: "Provide text, a URL or a message." }, 400)));
    await expect(analyze(request)).rejects.toThrow("Provide text, a URL or a message.");
  });

  it("joins an array of validation details into one readable message", async () => {
    const detail = [{ msg: "String should have at most 10000 characters" }, {}];
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ detail }, 422)));
    await expect(analyze(request)).rejects.toThrow("String should have at most 10000 characters; Invalid input");
  });

  it("falls back to a status-only message when an error body is not JSON", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("<html>Bad gateway</html>", { status: 502 })));
    await expect(analyze(request)).rejects.toThrow("Analysis request failed with HTTP 502");
  });

  it("replaces a network failure with a plain message", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    await expect(analyze(request)).rejects.toThrow("Could not reach the analysis service. Nothing was saved.");
  });

  it("rejects a 200 body that is not valid JSON", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("not json", { status: 200 })));
    await expect(analyze(request)).rejects.toThrow(/cannot show/);
  });

  it("rejects a 200 body that breaks the response contract", async () => {
    const { coverage: _coverage, ...missingCoverage } = fixtureScamResponse;
    for (const body of [
      {},
      [],
      missingCoverage,
      { ...fixtureScamResponse, verdict: "safe" },
      { ...fixtureScamResponse, coverage: { ...fixtureScamResponse.coverage, url: "ok" } },
      { ...fixtureScamResponse, risk_score: 0 },
      { ...fixtureScamResponse, probability_calibrated: true },
    ]) {
      vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(body)));
      await expect(analyze(request)).rejects.toThrow(/cannot show/);
    }
  });
});

// Every field the result panel reads must be validated before rendering, otherwise a
// malformed 2xx body throws while rendering instead of showing the unexpected-response error.
describe("analyze response validation", () => {
  const evidenceItem: Evidence = {
    id: "ev-1",
    indicator_type: "secret_request",
    source_module: "text",
    quote: "Send your OTP",
    observed_value: null,
    message_id: null,
    explanation: "Synthetic evidence.",
  };
  const moduleResult: ModuleResult = fixtureScamResponse.module_results.text;

  // Builds a response from the scam fixture, with one change applied to a deep copy.
  const withChange = (change: (copy: Record<string, any>) => void): unknown => {
    const copy = structuredClone(fixtureScamResponse) as unknown as Record<string, any>;
    change(copy);
    return copy;
  };
  const withModule = (patch: Record<string, unknown>) =>
    withChange((copy) => {
      copy.module_results.text = { ...structuredClone(moduleResult), ...patch };
    });
  const withEvidence = (patch: Record<string, unknown>) =>
    withChange((copy) => {
      copy.evidence = [{ ...evidenceItem, ...patch }];
    });

  const malformed: Array<[string, unknown]> = [
    ["a null module entry", withChange((copy) => { copy.module_results = { text: null }; })],
    ["missing versions", withChange((copy) => { delete copy.versions; })],
    ["null versions", withChange((copy) => { copy.versions = null; })],
    ["a non-string version", withChange((copy) => { copy.versions = { gateway: 1 }; })],
    ["a string module entry", withChange((copy) => { copy.module_results = { text: "oops" }; })],
    ["an array module entry", withChange((copy) => { copy.module_results = { text: [] }; })],
    ["a module without fixture_generated", withModule({ fixture_generated: undefined })],
    ["a non-boolean module fixture_generated", withModule({ fixture_generated: "yes" })],
    ["a numeric module detail", withModule({ detail: 503 })],
    ["an over-long module detail", withModule({ detail: "x".repeat(301) })],
    ["an unknown module status", withModule({ status: "ok" })],
    ["a module without a version", withModule({ version: "" })],
    ["a module without a raw score type", withModule({ raw_score_type: undefined })],
    ["an unknown module verdict", withModule({ verdict: "safe" })],
    ["an unknown module severity", withModule({ severity: "critical" })],
    ["a string module score", withModule({ score: "1" })],
    ["a missing module score", withModule({ score: undefined })],
    ["non-array module evidence", withModule({ evidence: "none" })],
    ["a null module evidence item", withModule({ evidence: [null] })],
    ["a malformed module evidence item", withModule({ evidence: [{ ...evidenceItem, source_module: "sms" }] })],
    ["a module scam verdict without evidence", withModule({ verdict: "suspected_scam", evidence: [] })],
    ["a null aggregate evidence item", withChange((copy) => { copy.evidence = [null]; })],
    ["a string aggregate evidence item", withChange((copy) => { copy.evidence = ["Send your OTP"]; })],
    ["an aggregate scam verdict without evidence", withChange((copy) => { copy.evidence = []; })],
    ["evidence without an id", withEvidence({ id: undefined })],
    ["evidence with an empty id", withEvidence({ id: "" })],
    ["evidence with a numeric indicator type", withEvidence({ indicator_type: 7 })],
    ["evidence with an unknown source module", withEvidence({ source_module: "sms" })],
    ["evidence without a source module", withEvidence({ source_module: undefined })],
    ["evidence with a numeric quote", withEvidence({ quote: 5 })],
    ["evidence with a blank quote", withEvidence({ quote: "   " })],
    ["evidence with an object observed value", withEvidence({ quote: null, observed_value: {} })],
    ["evidence with an array observed value", withEvidence({ quote: null, observed_value: ["a"] })],
    ["evidence with a blank observed value", withEvidence({ quote: null, observed_value: "  " })],
    ["evidence with neither quote nor observed value", withEvidence({ quote: null, observed_value: null })],
    ["evidence with a numeric message id", withEvidence({ message_id: 7 })],
    ["evidence with an object message id", withEvidence({ message_id: {} })],
    ["evidence with an over-long message id", withEvidence({ message_id: "m".repeat(129) })],
    ["evidence without an explanation", withEvidence({ explanation: undefined })],
    ["evidence with an empty explanation", withEvidence({ explanation: "" })],
    ["evidence with a numeric explanation", withEvidence({ explanation: 3 })],
    ["a negative processing time", withChange((copy) => { copy.processing_ms = -1; })],
    ["a fractional processing time", withChange((copy) => { copy.processing_ms = 12.5; })],
    ["a string processing time", withChange((copy) => { copy.processing_ms = "12"; })],
    ["a numeric limitation", withChange((copy) => { copy.limitations = [1]; })],
    ["an empty recommendation", withChange((copy) => { copy.recommendation = ""; })],
  ];

  it.each(malformed)("rejects %s before it can reach rendering", async (_name, body) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(body)));
    await expect(analyze(request)).rejects.toThrow(/cannot show/);
  });

  const accepted: Array<[string, unknown]> = [
    ["null optional evidence fields", withEvidence({ quote: "Send your OTP", observed_value: null, message_id: null })],
    ["omitted optional evidence fields", withChange((copy) => { copy.evidence = [{ id: "ev-1", indicator_type: "x", source_module: "url", quote: "q", explanation: "e" }]; })],
    ["a numeric zero observed value", withEvidence({ quote: null, observed_value: 0 })],
    ["a false observed value", withEvidence({ quote: null, observed_value: false })],
    ["a string observed value", withEvidence({ quote: null, observed_value: "192.0.2.10" })],
    ["a conversation message id", withEvidence({ source_module: "conversation", message_id: "m2" })],
    ["a null module detail and score", withModule({ detail: null, score: null })],
    ["an omitted module detail", withModule({ detail: undefined })],
    ["a module scam verdict with evidence", withModule({ verdict: "suspected_scam", evidence: [evidenceItem] })],
    ["no module results", withChange((copy) => { copy.module_results = {}; })],
  ];

  it.each(accepted)("accepts %s", async (_name, body) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(body)));
    await expect(analyze(request)).resolves.toMatchObject({ analysis_id: "fixture-example-1" });
  });

  it("accepts the unavailable and partial shapes with no evidence and no scam verdict", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(partialResponse)));
    await expect(analyze(request)).resolves.toMatchObject({ status: "partial" });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(unavailableResponse)));
    await expect(analyze(request)).resolves.toMatchObject({ status: "unavailable" });
  });
});
