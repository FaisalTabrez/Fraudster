import { useEffect, useRef, useState } from "react";
import type { AnalysisRequest } from "../../types/analysis";
import { extractScreenshot, reviewRequest, type ExtractionResponse } from "./ingestion";
import { decodeQr } from "./qr";

interface Props {
  busy: boolean;
  onSubmit: (request: AnalysisRequest) => Promise<void>;
}

export function IngestionPanel({ busy, onSubmit }: Props) {
  const [mode, setMode] = useState<"screenshot" | "qr">("screenshot");
  const [working, setWorking] = useState(false);
  const [review, setReview] = useState<string | null>(null);
  const [original, setOriginal] = useState("");
  const [extraction, setExtraction] = useState<ExtractionResponse | null>(null);
  const [error, setError] = useState("");
  const generation = useRef(0);
  useEffect(() => () => { generation.current++; }, []);

  const select = async (file?: File) => {
    const current = ++generation.current;
    setReview(null); setOriginal(""); setExtraction(null); setError("");
    if (!file) return;
    setWorking(true);
    try {
      if (mode === "screenshot") {
        const result = await extractScreenshot(file);
        if (current !== generation.current) return;
        setExtraction(result); setReview(result.text!); setOriginal(result.text!);
      } else {
        const content = await decodeQr(file);
        if (current !== generation.current) return;
        setReview(content); setOriginal(content);
      }
    } catch (failure) {
      if (current === generation.current) setError(failure instanceof Error ? failure.message : "Image processing failed.");
    } finally {
      if (current === generation.current) setWorking(false);
    }
  };

  let reviewError = "";
  if (review !== null) {
    try { reviewRequest(review, mode); }
    catch (failure) { reviewError = failure instanceof Error ? failure.message : "Unsupported content."; }
  }

  return <section className="fr-card ingestion-status" aria-labelledby="ingestion-heading">
    <h2 id="ingestion-heading" className="fr-h2">Screenshot and QR ingestion</h2>
    <p>Review content before analysis. QR images stay in this browser; screenshots are sent to optional OCR.
      Links are never opened. Payment recipients are not verified.</p>
    <label className="fr-field">Image use
      <select value={mode} disabled={working || busy} onChange={event => {
        generation.current++; setMode(event.target.value as typeof mode);
        setReview(null); setOriginal(""); setExtraction(null); setError("");
      }}>
        <option value="screenshot">Screenshot text (English OCR)</option>
        <option value="qr">Local QR code</option>
      </select>
    </label>
    <label className="fr-field">Upload PNG or JPEG (up to 5 MB)
      <input key={mode} type="file" accept="image/png,image/jpeg" disabled={working || busy}
        onChange={event => { void select(event.target.files?.[0]); event.target.value = ""; }} />
    </label>
    {working && <p role="status">{mode === "qr" ? "Decoding locally…" : "Extracting screenshot text…"}</p>}
    {error && <p role="alert" className="fr-banner fr-banner--unavailable">{error}</p>}
    {review !== null && <>
      <details><summary>Original {mode === "qr" ? "decoded content" : "extracted text"}</summary><pre>{original}</pre></details>
      {extraction?.image && <>
        <p>Image: {extraction.image.width} × {extraction.image.height} pixels. {extraction.boxes.length} text boxes.</p>
        <details><summary>Extracted text coordinates</summary>
          <ul>{extraction.boxes.map((box, index) => <li key={index}>
            {box.text} — x {box.x}, y {box.y}, width {box.width}, height {box.height}
          </li>)}</ul>
        </details>
      </>}
      <label className="fr-field">Review and correct {mode === "qr" ? "decoded content" : "extracted text"}
        <textarea rows={6} value={review} disabled={busy} onChange={event => setReview(event.target.value)} />
        <span className="fr-hint">{review.length.toLocaleString()} / 10,000 characters. Only reviewed content is analyzed.</span>
      </label>
      {reviewError && <p role="alert" className="fr-banner fr-banner--unavailable">{reviewError}</p>}
      <button type="button" className="fr-btn fr-btn--primary fr-btn--block" disabled={busy || working || !!reviewError}
        onClick={() => { void onSubmit(reviewRequest(review, mode)); }}>
        Analyze reviewed content
      </button>
    </>}
  </section>;
}
