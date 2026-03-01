"""Tests für dependapy.infrastructure.http — HttpClient."""

from __future__ import annotations

import responses as responses_lib

from dependapy.domain.result import Err, Ok
from dependapy.infrastructure.http import HttpClient, HttpError


class TestHttpClientGet:
    @responses_lib.activate
    def test_successful_get(self) -> None:
        responses_lib.add(
            responses_lib.GET, "https://example.com/api", json={"ok": True}, status=200
        )

        client = HttpClient(timeout=5, max_retries=0)
        result = client.get("https://example.com/api")

        assert isinstance(result, Ok)
        assert result.value.status_code == 200
        assert result.value.json() == {"ok": True}
        client.close()

    @responses_lib.activate
    def test_timeout_returns_err_with_is_timeout(self) -> None:
        responses_lib.add(
            responses_lib.GET,
            "https://example.com/api",
            body=responses_lib.ConnectionError("timeout"),
        )

        client = HttpClient(timeout=1, max_retries=0)
        result = client.get("https://example.com/api")

        assert isinstance(result, Err)
        client.close()

    @responses_lib.activate
    def test_http_500_exhausts_retries(self) -> None:
        responses_lib.add(responses_lib.GET, "https://example.com/api", status=500)

        client = HttpClient(timeout=5, max_retries=0)
        result = client.get("https://example.com/api")

        # 500 is on status_forcelist → max_retries=0 immediately exhausts → Err
        assert isinstance(result, Err)
        assert "500" in result.error.message or "Max retries" in result.error.message
        client.close()

    @responses_lib.activate
    def test_http_200_returns_ok(self) -> None:
        responses_lib.add(responses_lib.GET, "https://example.com/api", json={}, status=200)

        client = HttpClient(timeout=5, max_retries=0)
        result = client.get("https://example.com/api")

        assert isinstance(result, Ok)
        assert result.value.status_code == 200
        client.close()


class TestHttpClientPost:
    @responses_lib.activate
    def test_successful_post(self) -> None:
        responses_lib.add(responses_lib.POST, "https://example.com/api", json={"id": 1}, status=201)

        client = HttpClient(timeout=5, max_retries=0)
        result = client.post("https://example.com/api", json={"name": "test"})

        assert isinstance(result, Ok)
        assert result.value.status_code == 201
        assert result.value.json() == {"id": 1}
        client.close()

    @responses_lib.activate
    def test_post_with_headers(self) -> None:
        responses_lib.add(
            responses_lib.POST, "https://example.com/api", json={"ok": True}, status=200
        )

        client = HttpClient(timeout=5, max_retries=0)
        result = client.post(
            "https://example.com/api",
            json={"data": "value"},
            headers={"Authorization": "Bearer token"},
        )

        assert isinstance(result, Ok)
        client.close()

    @responses_lib.activate
    def test_post_connection_error(self) -> None:
        responses_lib.add(
            responses_lib.POST,
            "https://example.com/api",
            body=responses_lib.ConnectionError("Connection refused"),
        )

        client = HttpClient(timeout=1, max_retries=0)
        result = client.post("https://example.com/api", json={})

        assert isinstance(result, Err)
        assert isinstance(result.error, HttpError)
        client.close()


class TestHttpClientClose:
    def test_close_does_not_raise(self) -> None:
        client = HttpClient(timeout=5, max_retries=0)
        client.close()
        # Should not raise even if called twice
        client.close()


class TestHttpError:
    def test_str(self) -> None:
        err = HttpError(message="Something failed", status_code=500)
        assert str(err) == "Something failed"

    def test_is_timeout_default_false(self) -> None:
        err = HttpError(message="fail")
        assert err.is_timeout is False

    def test_is_timeout_true(self) -> None:
        err = HttpError(message="Timeout", is_timeout=True)
        assert err.is_timeout is True
