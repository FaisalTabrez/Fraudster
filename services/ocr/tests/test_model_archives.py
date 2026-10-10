import hashlib
import io
import json
from pathlib import Path
import tarfile

import pytest

from services.ocr.app.prepare import install_archive


def synthetic_archive():
    data, value = io.BytesIO(), b"synthetic model bytes"
    with tarfile.open(fileobj=data, mode="w") as archive:
        member = tarfile.TarInfo("upstream/inference.pdmodel")
        member.size = len(value)
        archive.addfile(member, io.BytesIO(value))
    artifact = {"archive_sha256": hashlib.sha256(data.getvalue()).hexdigest(), "files": [
        {"archive_member": "upstream/inference.pdmodel", "path": "det/inference.pdmodel",
         "sha256": hashlib.sha256(value).hexdigest()}]}
    return data.getvalue(), artifact


def test_pinned_archive_installs_only_mapped_verified_file(tmp_path):
    data, artifact = synthetic_archive()
    install_archive(data, artifact, tmp_path)
    assert (tmp_path / "det/inference.pdmodel").read_bytes() == b"synthetic model bytes"
    assert len(list(tmp_path.rglob("*.*"))) == 1


@pytest.mark.parametrize("kind", ["archive-hash", "file-hash", "destination"])
def test_invalid_archive_refused_before_any_write(tmp_path, kind):
    data, artifact = synthetic_archive()
    if kind == "archive-hash": artifact["archive_sha256"] = "0" * 64
    if kind == "file-hash": artifact["files"][0]["sha256"] = "0" * 64
    if kind == "destination": artifact["files"][0]["path"] = "../unreviewed.pdmodel"
    with pytest.raises(ValueError): install_archive(data, artifact, tmp_path)
    assert not list(tmp_path.iterdir())


def test_manifest_records_same_exact_archive_and_file_mapping_as_runtime():
    models = json.loads(Path("services/ocr/app/model-assets.json").read_text())["artifacts"]
    manifest = json.loads(Path("third_party/manifest.json").read_text())
    entry = next(item for item in manifest["entries"] if item["name"] == "PaddleOCR")
    assert entry["model_artifacts"] == models
    assert len(models) == 3
    assert sum(len(model["files"]) for model in models) == 9
    for model in models:
        assert model["url"].startswith("https://paddleocr.bj.bcebos.com/")
        assert len(model["archive_sha256"]) == 64
