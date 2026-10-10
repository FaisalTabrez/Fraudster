"""Clean native startup: real uvicorn processes on loopback, checked with scripts/smoke.py.

This is the no-Docker equivalent of the Compose demo start. It launches the gateway (and, for
the full stack, the real text and URL services) from the repository, with no .env file, no
provider key and no model download, then runs the smoke script against it.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.request
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import pytest

from tests.integration.support import ROOT, requires_url_service

SMOKE = ROOT / "scripts" / "smoke.py"
CLOSED_PORT_URL = "http://127.0.0.1:9"  # nothing listens here


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@contextmanager
def service(module: str, port: int, log: Path, **env: str) -> Iterator[None]:
    environment = {k: v for k, v in os.environ.items() if k not in {"TEXT_API_KEY", "DEMO_MODE"}}
    environment.update(PYTHONPATH=str(ROOT), **env)
    with log.open("wb") as handle:
        process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", module, "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
            cwd=ROOT, env=environment, stdout=handle, stderr=subprocess.STDOUT,
        )
    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if process.poll() is not None:
                pytest.fail(f"{module} exited early:\n{log.read_text(errors='replace')[-2000:]}")
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/health/live", timeout=2):
                    break
            except OSError:
                time.sleep(0.2)
        else:
            pytest.fail(f"{module} did not become live:\n{log.read_text(errors='replace')[-2000:]}")
        yield
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()


def smoke(port: int, expect: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SMOKE), "--base-url", f"http://127.0.0.1:{port}", "--expect", expect],
        capture_output=True, text=True, timeout=120, cwd=ROOT,
    )


def test_fixture_mode_starts_cleanly_and_passes_smoke(tmp_path: Path) -> None:
    port = free_port()
    with service("services.gateway.app.main:app", port, tmp_path / "gateway.log", DEMO_MODE="true"):
        result = smoke(port, "fixture")
    assert result.returncode == 0, result.stderr + result.stdout


def test_default_mode_without_services_is_unavailable_not_clean(tmp_path: Path) -> None:
    port = free_port()
    with service(
        "services.gateway.app.main:app", port, tmp_path / "gateway.log",
        TEXT_SERVICE_URL=CLOSED_PORT_URL, URL_SERVICE_URL=CLOSED_PORT_URL,
    ):
        result = smoke(port, "unavailable")
    assert result.returncode == 0, result.stderr + result.stdout


@requires_url_service
def test_full_native_stack_without_a_provider_key(tmp_path: Path) -> None:
    gateway_port, text_port, url_port = free_port(), free_port(), free_port()
    with service("services.text.app.main:app", text_port, tmp_path / "text.log"), \
         service("services.url.app.main:app", url_port, tmp_path / "url.log"), \
         service(
             "services.gateway.app.main:app", gateway_port, tmp_path / "gateway.log",
             TEXT_SERVICE_URL=f"http://127.0.0.1:{text_port}", URL_SERVICE_URL=f"http://127.0.0.1:{url_port}",
         ):
        result = smoke(gateway_port, "live-no-key")
    assert result.returncode == 0, result.stderr + result.stdout


def test_smoke_reports_a_failure_for_the_wrong_expectation(tmp_path: Path) -> None:
    """The smoke script must fail loudly, not pass whatever it is pointed at."""
    port = free_port()
    with service("services.gateway.app.main:app", port, tmp_path / "gateway.log", DEMO_MODE="true"):
        result = smoke(port, "unavailable")
    assert result.returncode == 1
    assert "smoke: FAIL" in result.stderr
