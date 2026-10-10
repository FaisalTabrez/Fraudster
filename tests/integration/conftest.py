"""Hermetic defaults for every integration test.

CI must never need a paid provider key or a large model download. Two guards make that a
property of the test run rather than a convention:

* provider credentials and mode switches are removed from the environment, so a developer's
  own ``TEXT_API_KEY`` or ``DEMO_MODE`` cannot change what a test measures;
* any attempt to open a connection to a non-loopback address fails the test.
"""

from __future__ import annotations

import ipaddress
import socket

import pytest

SCRUBBED_ENVIRONMENT = (
    "TEXT_API_KEY", "TEXT_MODEL", "TEXT_API_BASE_URL", "TEXT_TIMEOUT_SECONDS",
    "TEXT_SERVICE_URL", "URL_SERVICE_URL", "OCR_SERVICE_URL", "DEMO_MODE", "ANALYSIS_TIMEOUT_SECONDS",
)


def _is_loopback(address: object) -> bool:
    if isinstance(address, tuple) and address:
        host = address[0]
    elif isinstance(address, str):
        return True  # unix socket path
    else:
        return False
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return host == "localhost"


@pytest.fixture(autouse=True)
def hermetic_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in SCRUBBED_ENVIRONMENT:
        monkeypatch.delenv(name, raising=False)

    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex

    def guarded_connect(self: socket.socket, address: object) -> None:
        if not _is_loopback(address):
            raise AssertionError(f"integration tests must not use the network (tried {address!r})")
        return real_connect(self, address)  # type: ignore[arg-type]

    def guarded_connect_ex(self: socket.socket, address: object) -> int:
        if not _is_loopback(address):
            raise AssertionError(f"integration tests must not use the network (tried {address!r})")
        return real_connect_ex(self, address)  # type: ignore[arg-type]

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guarded_connect_ex)
