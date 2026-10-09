"""Explicit first-run upstream model download; never invoked by the service."""
import os
from pathlib import Path

from .engine import model_options, verify_assets


def main():
    from paddleocr import PaddleOCR
    root = Path(os.environ.get("OCR_MODEL_DIR", "services/ocr/models")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    PaddleOCR(**model_options(root))
    verify_assets(root)
    print("English PP-OCRv4 CPU model assets prepared. No user images were processed.")


if __name__ == "__main__":
    main()
