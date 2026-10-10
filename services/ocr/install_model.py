"""Explicit isolated CPU setup; upstream code unchanged, one cv2 distribution.

PaddleOCR/imgaug unconditionally require GUI OpenCV distributions. Build local
compatibility wheels after verifying published hashes; only dependency metadata,
the build marker and RECORD change. Never edit an installed distribution in place.
"""
import base64
import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from urllib.request import urlopen
import zipfile


def headless_wheel(data: bytes, artifact: dict, directory: Path) -> Path:
    if hashlib.sha256(data).hexdigest() != artifact["sha256"]:
        raise ValueError("Upstream runtime wheel fingerprint mismatch")
    with zipfile.ZipFile(io.BytesIO(data)) as source:
        files = {name: source.read(name) for name in source.namelist() if not name.endswith("/")}
    metadata = next(name for name in files if name.endswith(".dist-info/METADATA"))
    lines, replaced = [], 0
    for line in files[metadata].decode().splitlines():
        if line.startswith(("Requires-Dist: opencv-python", "Requires-Dist: opencv-contrib-python")):
            replaced += 1
            line = "Requires-Dist: opencv-python-headless==4.10.0.84"
            if line in lines:
                continue
        lines.append(line)
    if not replaced:
        raise ValueError("Expected reviewed OpenCV dependency metadata was absent")
    files[metadata] = ("\n".join(lines) + "\n").encode()
    wheel_info = metadata.removesuffix("METADATA") + "WHEEL"
    files[wheel_info] += b"Build: 1fraudster\n"
    record = metadata.removesuffix("METADATA") + "RECORD"
    files.pop(record, None)
    for suffix in (".jws", ".p7s"):
        files.pop(record + suffix, None)
    rows = io.StringIO(newline="")
    writer = csv.writer(rows)
    for name, value in files.items():
        digest = base64.urlsafe_b64encode(hashlib.sha256(value).digest()).rstrip(b"=").decode()
        writer.writerow([name, "sha256=" + digest, len(value)])
    writer.writerow([record, "", ""])
    files[record] = rows.getvalue().encode()
    parts = artifact["filename"].split("-")
    output = directory / "-".join(parts[:2] + ["1fraudster"] + parts[2:])
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for name, value in files.items():
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            target.writestr(info, value)
    return output


def main():
    service = Path(__file__).resolve().parent
    artifacts = json.loads((service / "runtime-wheels.json").read_text())
    with tempfile.TemporaryDirectory(prefix="fraudster-ocr-setup-") as temporary:
        wheels = []
        for artifact in artifacts.values():
            with urlopen(artifact["url"], timeout=30) as response:
                data = response.read(25_000_001)
            if len(data) > 25_000_000:
                raise ValueError("Upstream runtime wheel exceeds setup size limit")
            wheels.append(str(headless_wheel(data, artifact, Path(temporary))))
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(service / "requirements-model.txt"), *wheels], check=True)
    # Check metadata and actual cv2 ownership; pip check alone misses collisions.
    from importlib.metadata import distributions
    cv = [dist.metadata["Name"] for dist in distributions() if dist.metadata["Name"].lower().startswith("opencv-")]
    if cv != ["opencv-python-headless"]:
        raise RuntimeError("Use a fresh isolated environment: exactly one headless OpenCV distribution is required")
    subprocess.run([sys.executable, "-m", "pip", "check"], check=True)
    print("CPU OCR installed with hash-verified upstream wheels and one headless OpenCV distribution.")


if __name__ == "__main__":
    main()
