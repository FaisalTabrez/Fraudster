"""Opt-in public proxy limit regression; generated synthetic image only."""
import argparse
import base64
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
MAX_IMAGE_BYTES = 5_000_000
MAX_BODY_BYTES = MAX_IMAGE_BYTES + 65_536


def require(condition: bool, detail: str):
    if not condition:
        raise RuntimeError(detail)


def upload(base: str, image: bytes):
    boundary = "fraudster-synthetic-limit-test"
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"synthetic.png\"\r\n"
            "Content-Type: image/png\r\n\r\n").encode() + image + f"\r\n--{boundary}--\r\n".encode()
    request = Request(base.rstrip("/") + "/v1/extract", data=body,
                      headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}, method="POST")
    try:
        with urlopen(request, timeout=30) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        with error:
            try:
                result = json.load(error)
            except json.JSONDecodeError:
                result = {}  # A proxy HTML error is not a contract-shaped response.
            return error.code, result


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:4173/api")
    parser.add_argument("--expect-ocr-unavailable", action="store_true",
                        help="Verify the upload boundary without an installed OCR model.")
    args = parser.parse_args(argv)
    # PNG readers permit trailing bytes: pad a tiny synthetic image to test the
    # transport boundary without allocating millions of decoded pixels.
    if args.expect_ocr_unavailable:
        # Keep the model-free CI boundary check hermetic. PNG readers permit
        # trailing bytes, so this one-pixel input can be safely padded below.
        image = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )
    else:
        fixture = ROOT / ".venv/ingestion-fixtures/synthetic-ocr.png"
        if not fixture.is_file():
            parser.error("Synthetic PNG fixture is missing. From the repository root, run "
                         "python tests/e2e/generate_ingestion.py before this smoke check.")
        image = fixture.read_bytes()
    require(len(image) < MAX_IMAGE_BYTES, "Synthetic PNG must be smaller than 5,000,000 bytes.")
    padded = image + bytes(MAX_IMAGE_BYTES - len(image))
    code, result = upload(args.base_url, padded)
    if args.expect_ocr_unavailable:
        require(code == 503 and result.get("status") == "unavailable"
                and result.get("text") is None and result.get("boxes") == [],
                f"5 MB PNG did not reach the unavailable OCR path (HTTP {code}).")
    else:
        require(code == 200 and result.get("status") == "complete",
                f"5 MB PNG rejected at public boundary (HTTP {code}).")
        require(bool(result.get("image")) and bool(result.get("boxes")),
                "Completed OCR must include image dimensions and boxes.")
    for size in (MAX_IMAGE_BYTES + 1, MAX_BODY_BYTES):
        response_code, response = upload(args.base_url, image + bytes(size - len(image)))
        require({"status", "text", "boxes", "image", "detail"} <= response.keys()
                and response_code == 413 and response.get("status") == "unavailable"
                and response.get("text") is None and response.get("boxes") == []
                and response.get("image") is None and isinstance(response.get("detail"), str),
                f"Oversize {size}-byte image did not receive a contract-shaped 413 (HTTP {response_code}).")
    # Extract's larger limit must not expand the JSON analysis route's default ceiling.
    request = Request(args.base_url.rstrip("/") + "/v1/analyze", data=b" " * 1_048_577,
                      headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=30) as response:
            analyze_code = response.status
    except HTTPError as error:
        analyze_code = error.code
        error.close()
    require(analyze_code == 413, f"Analyze proxy body ceiling changed (HTTP {analyze_code}).")
    mode = "reached unavailable OCR (no extraction success claimed)" if args.expect_ocr_unavailable else "extracted successfully"
    print(f"PASS public proxy: 5,000,000-byte PNG {mode}; image/envelope excess return JSON unavailable 413; analyze retains 1 MiB limit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
