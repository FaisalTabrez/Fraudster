"""Explicit downloads of pinned, hashed archives; no package-internal lookup."""
import hashlib
import io
import json
import os
from pathlib import Path
import tarfile
from urllib.request import urlopen

from .engine import verify_assets


def install_archive(data: bytes, artifact: dict, root: Path):
    if hashlib.sha256(data).hexdigest() != artifact["archive_sha256"]:
        raise ValueError("Upstream model archive fingerprint mismatch")
    verified = []
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as archive:
        for mapping in artifact["files"]:
            member = archive.getmember(mapping["archive_member"])
            if not member.isfile() or member.size > 20_000_000:
                raise ValueError("Invalid model archive member")
            value = archive.extractfile(member).read()
            if hashlib.sha256(value).hexdigest() != mapping["sha256"]:
                raise ValueError("Model file fingerprint mismatch")
            target = (root / mapping["path"]).resolve()
            if not target.is_relative_to(root.resolve()):
                raise ValueError("Invalid model destination")
            verified.append((target, value))
    # Never extract archive paths. Only the reviewed destination mapping is used.
    for target, value in verified:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + ".download")
        try:
            temporary.write_bytes(value)
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)


def main():
    root = Path(os.environ.get("OCR_MODEL_DIR", "services/ocr/models")).resolve()
    artifacts = json.loads(Path(__file__).with_name("model-assets.json").read_text())["artifacts"]
    for artifact in artifacts:
        if all((root / file["path"]).is_file() and
               hashlib.sha256((root / file["path"]).read_bytes()).hexdigest() == file["sha256"]
               for file in artifact["files"]):
            continue
        with urlopen(artifact["url"], timeout=30) as response:
            data = response.read(25_000_001)
        if len(data) > 25_000_000:
            raise ValueError("Upstream model archive exceeds setup size limit")
        install_archive(data, artifact, root)
    verify_assets(root)
    print("Pinned English CPU model archives/files verified and prepared. No user images processed.")


if __name__ == "__main__":
    main()
