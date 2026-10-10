# Optional screenshot OCR

The core app starts without PaddleOCR or model weights. OCR is a separate private
service; the browser uploads only to `POST /api/v1/extract`. The gateway bounds
multipart bodies before parsing and forwards validated-size image bytes to the
private `/extract` endpoint. PNG/JPEG content types and decoded formats must
match. The limit is **5,000,000 bytes (decimal 5 MB)** and **20,000,000 pixels**.
Image dimensions are inspected before verification, full decode, and inference.
Animated PNG, other formats, damaged images, and oversize images are rejected.
Uploads are processed in memory; gateway parser temporary files are closed after
each request. Images, text, and recognition output are not persisted or logged.

## Verified configuration

- Python 3.11.17, Windows x64 (OS build 26200), CPU only; no CUDA required.
- `paddleocr==2.9.1`, `paddlepaddle==2.6.2`, `numpy==1.26.4`,
  **only** `opencv-python-headless==4.10.0.84`, Pillow `11.3.0`, setuptools `75.8.0`.
- `lang=en`, `ocr_version=PP-OCRv4`, angle classification enabled, MKLDNN disabled,
  two CPU threads. The English v4 configuration uses the upstream
  **en_PP-OCRv3_det_infer** detector, **en_PP-OCRv4_rec_infer** recognizer, and
  **ch_ppocr_mobile_v2.0_cls_infer** orientation classifier.
- Supported recognition language in this application: **English**, including
  the English model's digits/punctuation. The Chinese-named orientation model
  does not add Chinese recognition. Other scripts are not supported by this
  configuration. Users must inspect and correct OCR errors before analysis.
- Synthetic PNG and JPEG inference passed. This is compatibility verification,
  not model accuracy or scam-detection performance.

The [official v2 quick start](https://www.paddleocr.ai/main/en/version2.x/ppocr/quick_start.html)
describes CPU operation and the first constructor's download behavior. This
service prevents constructor downloads by checking local files and their recorded
SHA-256 values before loading PaddleOCR. Startup stays live but not ready if
dependencies or verified weights are missing. The default profile is model-free.

## Native setup (from repository root)

Use a separate Python 3.11 environment; do not mix Paddle's dependencies into the
gateway or Python 3.13 URL adapter environment.

```powershell
py -3.11 -m venv .venv-ocr
.\.venv-ocr\Scripts\python.exe services\ocr\install_model.py
$env:OCR_MODEL_DIR = (Join-Path (Get-Location) 'services\ocr\models')
.\.venv-ocr\Scripts\python.exe -m services.ocr.app.prepare
.\.venv-ocr\Scripts\python.exe -m services.ocr.verify_model
.\.venv-ocr\Scripts\python.exe -m uvicorn services.ocr.app.main:app --host 127.0.0.1 --port 8003
```

Use a **fresh** environment. `install_model.py` downloads the exact official
PaddleOCR 2.9.1 and imgaug 0.4.0 wheels in `runtime-wheels.json` and checks their
SHA-256 hashes. Their upstream metadata requires overlapping GUI OpenCV wheels;
the installer builds temporary compatibility wheels (`1fraudster` build tag)
replacing only those requirements with the single headless distribution. It
preserves implementation bytes, rebuilds RECORD, checks actual OpenCV distribution
ownership and runs `pip check`. It does not modify installed packages in place.
Use this command rather than installing the model requirements alone or mixing
other OpenCV distributions into the environment. Docker uses the same installer.
Sources, hashes and the metadata-only recipe are attributed in the manifest.

The explicit `prepare` command downloads three **exact recorded** archives from Paddle's official
`paddleocr.bj.bcebos.com` host on first use (about 16 MB total), then checks the
nine inference-file fingerprints in `app/model-assets.json`. That file and the
third-party manifest record each upstream release path, exact archive URL,
archive SHA-256, member-to-local-file mapping and extracted-file SHA-256. Setup
does not use PaddleOCR's package-internal URL lookup; it verifies the archive
before reading mapped members and never extracts arbitrary archive paths. Models are stored
under the ignored `services/ocr/models/{det,rec,cls}` directories. Subsequent
startup/request processing needs no model download. If fingerprints mismatch,
OCR remains unavailable; investigate the upstream change rather than accepting
unreviewed assets. No downloaded files belong in Git. Failed preparation can be
retried after removing only the affected local model directory.

Set `$env:OCR_SERVICE_URL = 'http://127.0.0.1:8003'` in the **gateway** terminal
before launching it. Install the updated gateway requirements for its multipart
parser. Neither OCR readiness nor missing assets prevents manual/QR analysis.
The existing gateway analysis deadline also bounds the extraction HTTP call;
slow inference becomes an explicit unavailable result. In-progress CPU work may
finish after the caller times out; it never writes a result to disk. The OCR
service admits **one** request per process before reading/decode/inference, with
**no waiting queue**. Excess requests get immediate contract-shaped 503 with
`Retry-After: 1`. A cancelled/timed-out caller does not release that capacity
until the actual worker finishes and closes the image. Retries cannot accumulate
additional decoded images or CPU jobs. Deployment worker count multiplies the
process capacity; do not increase it without budgeting CPU/memory.

## Docker setup

The existing OCR profile remains model-free unless explicitly built with:

```powershell
docker compose --profile ocr build --build-arg INSTALL_OCR=true ocr
```

For model-enabled Compose, use a local override (not committed) which sets the
OCR container's `OCR_MODEL_DIR=/service/models` and mounts the prepared
`./services/ocr/models:/service/models:ro`. Prepare models natively as above or
with a separate writable bind mount for the explicit prepare command. The
non-root container also needs Linux runtime libraries provided by its Dockerfile.
Container inference has not been verified in this environment (Docker absent).
No shared root Compose configuration is changed in this PR.

## Results and failures

The existing extraction schema is unchanged: `complete` returns text, integer
axis-aligned boxes in pixel coordinates, and original decoded image dimensions.
Boxes are clipped to the image. Coordinates refer to original extracted text;
editing text does not rewrite box metadata. `unavailable` returns null text and
empty boxes, with dimensions when known and a clear detail. HTTP 413 denotes
limits, 415 unsupported image formats, 422 invalid/no-readable-text extraction,
and 503 missing model/service, timeout, or inference failure. The contract has
no separate failure status, so extraction failure uses `unavailable` plus detail.
Exceptions and provider messages are never relayed.

The panel shows original text and coordinates, provides an editable review field,
and only submits reviewed text using the existing analyze callback with
`source=screenshot`. It does not silently truncate extraction at 10,000 characters;
users must shorten oversized text themselves.

## Attribution

PaddleOCR and PaddlePaddle are Apache-2.0 dependencies. Upstream LICENSE files are
retained in `third_party/licenses/` and releases/model provenance are recorded in
`third_party/manifest.json`. Integration code is original; no upstream
implementation or weights are copied into the repository. The installer creates
temporary PaddleOCR/imgaug compatibility wheels with dependency metadata changes
only; upstream LICENSE notices, wheel hashes and that recipe are retained.
