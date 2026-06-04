"""Verify login rate-limit cannot be bypassed by spoofing X-Forwarded-For."""
import pytest

from app import app
from routes.auth import _get_client_ip


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["PROXY_FIX_DEPTH"] = 0  # no proxy
    with app.test_client() as c:
        yield c


class TestClientIpResolution:
    def test_get_client_ip_ignores_xff_without_proxy(self):
        """With PROXY_FIX_DEPTH=0, XFF must be ignored."""
        with app.test_request_context(
            headers={"X-Forwarded-For": "1.2.3.4"},
            environ_base={"REMOTE_ADDR": "127.0.0.1"},
        ):
            assert _get_client_ip() == "127.0.0.1"

    def test_get_client_ip_falls_back_to_zero(self):
        """If remote_addr is None, return 0.0.0.0 (no crash)."""
        with app.test_request_context(environ_base={"REMOTE_ADDR": ""}):
            result = _get_client_ip()
            assert result == "0.0.0.0"
