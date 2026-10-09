import { afterEach, describe, expect, it, vi } from "vitest";

import { fixtureScamResponse, unavailableResponse } from "../test-fixtures";
import type { AnalysisRequest } from "../types/analysis";
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
