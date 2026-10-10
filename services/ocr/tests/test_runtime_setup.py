import hashlib
import io
import zipfile

import pytest

from services.ocr.install_model import headless_wheel


def synthetic_wheel():
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as wheel:
        wheel.writestr("synthetic/module.py", "# original synthetic implementation\n")
        wheel.writestr("synthetic-1.0.dist-info/METADATA", "Name: synthetic\nVersion: 1.0\nRequires-Dist: opencv-python\nRequires-Dist: opencv-contrib-python\nRequires-Dist: numpy<2\n")
        wheel.writestr("synthetic-1.0.dist-info/WHEEL", "Wheel-Version: 1.0\n")
        wheel.writestr("synthetic-1.0.dist-info/RECORD", "")
    return data.getvalue()


def test_verified_compatibility_wheel_changes_metadata_only(tmp_path):
    data = synthetic_wheel()
    artifact = {"filename": "synthetic-1.0-py3-none-any.whl", "sha256": hashlib.sha256(data).hexdigest()}
    output = headless_wheel(data, artifact, tmp_path)
    with zipfile.ZipFile(output) as wheel:
        metadata = wheel.read("synthetic-1.0.dist-info/METADATA").decode()
        assert metadata.count("Requires-Dist: opencv-python-headless==4.10.0.84") == 1
        assert "Requires-Dist: opencv-contrib-python" not in metadata
        assert "Requires-Dist: numpy<2" in metadata
        assert wheel.read("synthetic/module.py") == b"# original synthetic implementation\n"
        assert b"sha256=" in wheel.read("synthetic-1.0.dist-info/RECORD")


def test_wheel_hash_mismatch_refuses_repackaging(tmp_path):
    with pytest.raises(ValueError, match="fingerprint"):
        headless_wheel(synthetic_wheel(), {"sha256": "0" * 64}, tmp_path)
    assert not list(tmp_path.iterdir())
