import { afterEach, describe, expect, it, vi } from "vitest";
import { extractScreenshot, reviewRequest, validateFile } from "./ingestion";

afterEach(() => vi.unstubAllGlobals());

describe("ingestion validation and transport", () => {
  it("enforces exact byte limit, rejects empty/unsupported files before any request", async () => {
    const fetch = vi.fn(); vi.stubGlobal("fetch", fetch);
    expect(() => validateFile(new File([new Uint8Array(5_000_000)], "test.png", { type: "image/png" }))).not.toThrow();
    for (const file of [new File([new Uint8Array(5_000_001)], "large.png", { type: "image/png" }),
                        new File([], "empty.png", { type: "image/png" }),
                        new File(["x"], "bad.svg", { type: "image/svg+xml" })]) {
      await expect(extractScreenshot(file)).rejects.toThrow();
    }
    expect(fetch).not.toHaveBeenCalled();
  });
  it("only uploads to the same-origin gateway and preserves clear unavailable states", async () => {
    const fetch = vi.fn().mockResolvedValue({ ok: false, json: async () => ({ status: "unavailable", detail: "OCR is unavailable" }) });
    vi.stubGlobal("fetch", fetch);
    await expect(extractScreenshot(new File(["test"], "test.png", { type: "image/png" }))).rejects.toThrow("OCR is unavailable");
    expect(fetch).toHaveBeenCalledWith("/api/v1/extract", { method: "POST", body: expect.any(FormData) });
  });
  it.each(["upi://pay?pa=synthetic", "javascript:alert(1)", "WIFI:T:WPA;S:synthetic;;", "BEGIN:VCARD\nFN:synthetic",
           "mailto:synthetic@example.test", "https://", "https://user:pass@example.test", "\u0000binary", ""])
    ("rejects unsupported/invalid QR content %s", content => {
      expect(() => reviewRequest(content, "qr")).toThrow();
    });
  it("routes HTTP(S) as URL strings and readable text as text, with original source", () => {
    expect(reviewRequest("https://example.test/path", "qr")).toEqual({ urls: ["https://example.test/path"], messages: [], source: "qr" });
    expect(reviewRequest("synthetic plain text", "qr")).toEqual({ text: "synthetic plain text", urls: [], messages: [], source: "qr" });
    expect(reviewRequest("corrected text", "screenshot").source).toBe("screenshot");
    expect(reviewRequest("Note: synthetic plain text", "qr").text).toBe("Note: synthetic plain text");
  });
});
