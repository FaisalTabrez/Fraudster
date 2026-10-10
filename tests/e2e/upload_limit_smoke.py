"""Opt-in public proxy limit regression; generated synthetic image only."""
import argparse
import base64
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


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
        try:
            result = json.load(error)
        except json.JSONDecodeError:
            result = {}  # A proxy HTML error is not a contract-shaped response.
        return error.code, result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:4173/api")
    parser.add_argument(
        "--expect-ocr-unavailable",
        action="store_true",
        help="Verify the proxy boundary without installing the optional OCR model.",
    )
    args = parser.parse_args()
    # PNG readers permit trailing bytes: pad a tiny synthetic image to test the
    # transport boundary without allocating millions of decoded pixels.
    if args.expect_ocr_unavailable:
        image = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )
    else:
        image = Path(".venv/ingestion-fixtures/synthetic-ocr.png").read_bytes()
    assert len(image) < 5_000_000
    padded = image + bytes(5_000_000 - len(image))
    code, result = upload(args.base_url, padded)
    if args.expect_ocr_unavailable:
        assert code == 503 and result.get("status") == "unavailable", (
            f"5 MB PNG did not reach the unavailable OCR boundary (HTTP {code})"
        )
        assert result.get("text") is None and result.get("boxes") == []
    else:
        assert code == 200 and result.get("status") == "complete", (
            f"5 MB PNG rejected at public boundary (HTTP {code})"
        )
        assert result["image"] and result["boxes"]
    code, result = upload(args.base_url, padded + b"x")
    assert code == 413 and result["status"] == "unavailable"
    assert result["text"] is None and result["boxes"] == []
    expectation = "reached OCR availability handling" if args.expect_ocr_unavailable else "completed OCR"
    print(
        "PASS public proxy: 5,000,000-byte synthetic PNG "
        f"{expectation}; 5,000,001 rejected with unavailable response"
    )


if __name__ == "__main__":
    main()
