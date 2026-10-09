"""Optional pinned PaddleOCR CPU adapter. No download on app startup/request."""
from pathlib import Path
from threading import Lock
import hashlib
import json


def model_options(root: Path) -> dict:
    return dict(use_gpu=False, lang="en", ocr_version="PP-OCRv4", use_angle_cls=True,
                show_log=False, enable_mkldnn=False, cpu_threads=2,
                det_model_dir=str(root / "det"), rec_model_dir=str(root / "rec"),
                cls_model_dir=str(root / "cls"))


class PaddleEngine:
    def __init__(self, root: Path):
        # Paddle's constructor auto-downloads missing assets. Guard every file first.
        verify_assets(root)
        from paddleocr import PaddleOCR
        self.ocr = PaddleOCR(**model_options(root))
        self.lock = Lock()

    def recognize(self, image):
        import numpy as np
        with self.lock:
            # Paddle expects BGR, whereas Pillow supplies RGB.
            return self.ocr.ocr(np.asarray(image)[:, :, ::-1].copy(), cls=True)[0] or []


def verify_assets(root: Path):
    fingerprints = json.loads(Path(__file__).with_name("model-assets.json").read_text())
    for relative, expected in fingerprints.items():
        path = root / relative
        if not path.is_file():
            raise FileNotFoundError("OCR assets have not been prepared")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError("OCR model fingerprint mismatch; use the reviewed model assets")
