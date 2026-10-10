# Ingestion boundary and owner handoff

`IngestionPanel` receives the existing `busy` and `onSubmit(AnalysisRequest)`
interface from `App`, alongside the manual `ScanForm`. It owns image loading,
extraction/decode states, original content, correction, and explicit submission.
It uses existing `source=screenshot|qr` values. No analysis or extraction schemas
changed; no changes to scan, conversation, result policy, or shared root runtime.
This is the proposed integration boundary for Stephen's review; Faisal should
review the narrowly scoped gateway `/v1/extract` forwarding replacement.

OCR uploads multipart field `file` to same-origin `/api/v1/extract`. QR image
bytes never leave the browser. Content is rendered as plain React text/textarea,
without anchors, HTML interpretation, navigation, or requests to decoded URLs.
Only an explicit **Analyze reviewed content** click submits reviewed text or
HTTP(S) URL strings to the existing analysis callback. New uploads clear previous
review content; failed extraction/decode cannot submit a stale result.

`@zxing/browser==0.2.1` and `@zxing/library==0.23.0` are exact package pins; the
browser release's `^0.23.0` peer range is satisfied. Versions and integrity hashes
are locked. The browser dependency loads when local decoding is requested.
The QR reader receives only an image created from a local blob URL; the URL and
handlers are released after success/failure. No camera permission is used.

Only static PNG/JPEG uploads up to decimal 5 MB are offered. Both screenshot and QR images are checked
for decoded dimensions locally (20 million pixels) before uploading a screenshot
or creating ZXing's pixel canvas. Temporary blob URLs are released on all paths.
The browser must decode the image to discover dimensions; the OCR server enforces
its dimension limit before pixel allocation. QR handling clearly reports invalid
images, no readable code, empty/overlong content, malformed HTTP(S) URLs, credentials
in URLs, and unsupported structured schemes/payloads (UPI, Wi-Fi, contact/calendar,
mail, SMS, app links, binary/control characters). Payment recipients are **never
verified**. Plain text is capped at 10,000 characters and URL strings at 2,048.
Single QR images are supported; selection among multiple codes is not implemented.

Tests exercise review/edit/submit behavior, unavailable and failure states, file
limits, unsupported QR payloads, and blob cleanup. Synthetic QR pixels are encoded
with the pinned library and decoded with the real browser reader's canvas path;
this is functional compatibility evidence, not a detection benchmark.

`third_party/manifest.json` and retained MIT (browser) / Apache-2.0 (library)
licenses describe attribution. Models and user images are not bundled.
