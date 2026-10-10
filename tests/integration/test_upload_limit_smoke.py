"""The opt-in proxy regression must fail clearly, including under python -O."""
import importlib.util
from pathlib import Path
from urllib.error import HTTPError

import pytest

spec = importlib.util.spec_from_file_location(
    "upload_limit_smoke", Path(__file__).resolve().parents[1] / "e2e/upload_limit_smoke.py"
)
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


def fixture(monkeypatch, tmp_path):
    root = tmp_path / "repo"
    image = root / ".venv/ingestion-fixtures/synthetic-ocr.png"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"synthetic fixture; network mocked")
    monkeypatch.setattr(smoke, "ROOT", root)
    monkeypatch.chdir(tmp_path)


def test_missing_fixture_has_setup_instruction(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(smoke, "ROOT", tmp_path)
    with pytest.raises(SystemExit) as failure:
        smoke.main([])
    assert failure.value.code == 2
    assert "python tests/e2e/generate_ingestion.py" in capsys.readouterr().err


def test_model_free_mode_does_not_need_generated_fixture(monkeypatch, tmp_path):
    monkeypatch.setattr(smoke, "ROOT", tmp_path)
    sizes = []

    def upload(base, image):
        sizes.append(len(image))
        if len(image) == smoke.MAX_IMAGE_BYTES:
            return 503, {"status": "unavailable", "text": None, "boxes": []}
        return 413, {"status": "unavailable", "text": None, "boxes": [], "image": None, "detail": "Too large"}

    def analyze(request, timeout):
        raise HTTPError(request.full_url, 413, "Too large", {}, None)

    monkeypatch.setattr(smoke, "upload", upload)
    monkeypatch.setattr(smoke, "urlopen", analyze)
    assert smoke.main(["--expect-ocr-unavailable"]) == 0
    assert sizes == [5_000_000, 5_000_001, 5_065_536]


@pytest.mark.parametrize("model_free", [False, True])
def test_boundary_checks_from_another_directory(monkeypatch, tmp_path, model_free):
    fixture(monkeypatch, tmp_path)
    sizes = []

    def upload(base, image):
        sizes.append(len(image))
        if len(image) == smoke.MAX_IMAGE_BYTES:
            if model_free:
                return 503, {"status": "unavailable", "text": None, "boxes": []}
            return 200, {"status": "complete", "image": {"width": 1, "height": 1}, "boxes": [1]}
        return 413, {"status": "unavailable", "text": None, "boxes": [], "image": None, "detail": "Too large"}

    def analyze(request, timeout):
        assert request.full_url.endswith("/v1/analyze")
        assert len(request.data) == 1_048_577
        raise HTTPError(request.full_url, 413, "Too large", {}, None)

    monkeypatch.setattr(smoke, "upload", upload)
    monkeypatch.setattr(smoke, "urlopen", analyze)
    assert smoke.main(["--expect-ocr-unavailable"] if model_free else []) == 0
    assert sizes == [5_000_000, 5_000_001, 5_065_536]


def test_html_proxy_failure_is_not_a_success(monkeypatch, tmp_path):
    fixture(monkeypatch, tmp_path)
    monkeypatch.setattr(smoke, "upload", lambda *args: (413, {}))
    with pytest.raises(RuntimeError, match="5 MB PNG rejected"):
        smoke.main([])


def test_explicit_failure_is_not_an_assertion():
    with pytest.raises(RuntimeError, match="synthetic failure"):
        smoke.require(False, "synthetic failure")
