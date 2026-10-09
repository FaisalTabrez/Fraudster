import type { AnalysisRequest } from "../../types/analysis";

export const MAX_IMAGE_BYTES = 5_000_000;
export const MAX_IMAGE_PIXELS = 20_000_000;

export interface ExtractionResponse {
  status: "complete" | "unavailable";
  text: string | null;
  boxes: Array<{ text: string; x: number; y: number; width: number; height: number }>;
  image: { width: number; height: number } | null;
  detail: string | null;
}

export function validateFile(file: File) {
  if (!["image/png", "image/jpeg"].includes(file.type)) throw new Error("Only PNG and JPEG images are supported.");
  if (!file.size) throw new Error("The image is empty.");
  if (file.size > MAX_IMAGE_BYTES) throw new Error("Image exceeds the 5 MB upload limit.");
}

export async function extractScreenshot(file: File): Promise<ExtractionResponse> {
  validateFile(file);
  const body = new FormData();
  body.append("file", file);
  let response: Response;
  try {
    response = await fetch("/api/v1/extract", { method: "POST", body });
  } catch {
    throw new Error("OCR service is unavailable. You can still paste text manually.");
  }
  try {
    const result = await response.json() as ExtractionResponse;
    if (result.status !== "complete" || !response.ok) {
      throw new Error(result.status === "unavailable" && typeof result.detail === "string"
        ? result.detail : "OCR extraction failed. Try another image or paste text manually.");
    }
    if (typeof result.text !== "string" || !result.text.trim() || !result.image || !Array.isArray(result.boxes)) {
      throw new Error("OCR returned an invalid extraction result.");
    }
    return result;
  } catch (error) {
    if (error instanceof SyntaxError) throw new Error("OCR service returned an unreadable response.");
    throw error;
  }
}

export function reviewRequest(value: string, source: "qr" | "screenshot"): AnalysisRequest {
  const text = value.trim();
  if (!text) throw new Error("Enter text to analyze after review.");
  if (text.length > 10_000) throw new Error("Reviewed content exceeds the 10,000 character analysis limit. Shorten it first.");
  if (source === "qr") {
    if (/^[a-z][a-z0-9+.-]*:\S/i.test(text)
        || /^(https?|upi|mailto|sms|smsto|tel|javascript|data|file|intent|wifi|mecard|matmsg):/i.test(text)) {
      if (!/^https?:\/\//i.test(text)) {
        throw new Error("Unsupported QR payload. Payment, contact, Wi-Fi and app links are not analyzed; no recipient has been verified.");
      }
      let url: URL;
      try { url = new URL(text); } catch { throw new Error("The decoded URL is invalid."); }
      if (!url.hostname || url.username || url.password || text.length > 2048 || /\s/.test(text)) {
        throw new Error("The decoded URL is invalid or exceeds the 2,048 character limit.");
      }
      return { urls: [text], messages: [], source };
    }
    if (/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f\ufffd]/.test(text)
        || /^(BEGIN:VCARD|BEGIN:VEVENT|MECARD:|MATMSG:|WIFI:|SMSTO:)/i.test(text)) {
      throw new Error("Unsupported QR payload. Only readable text and HTTP(S) URLs are supported.");
    }
  }
  return { text, urls: [], messages: [], source };
}
