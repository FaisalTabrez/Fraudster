export function IngestionStatus() {
  return (
    <section className="ingestion-status" aria-labelledby="ingestion-heading">
      <span className="eyebrow">P1 after P0 passes</span>
      <h2 id="ingestion-heading">Screenshot and QR ingestion</h2>
      <p>
        OCR and local QR decoding are intentionally unavailable in this bootstrap. Their extracted text will use
        this same scan flow, with correction before analysis and no automatic link opening.
      </p>
    </section>
  );
}
