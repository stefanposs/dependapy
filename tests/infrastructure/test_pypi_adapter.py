"""Tests für dependapy.infrastructure.adapters.pypi — PyPIAdapter."""

from __future__ import annotations

import responses as responses_lib

from dependapy.domain.errors import PackageNotFoundError
from dependapy.domain.result import Err
from dependapy.domain.value_objects import Version
from dependapy.infrastructure.adapters.pypi import PyPIAdapter
from dependapy.infrastructure.http import HttpClient

PYPI_BASE_URL = "https://pypi.org/pypi/{package_name}/json"
REQUESTS_URL = "https://pypi.org/pypi/requests/json"
FLASK_URL = "https://pypi.org/pypi/flask/json"
NONEXISTENT_URL = "https://pypi.org/pypi/nonexistent-xyz/json"


def _pypi_response(version: str) -> dict:
    return {"info": {"version": version}, "releases": {}}


def _make_adapter() -> PyPIAdapter:
    return PyPIAdapter(http_client=HttpClient(max_retries=0), base_url=PYPI_BASE_URL)


class TestPyPIAdapterGetLatestVersion:
    @responses_lib.activate
    def test_returns_version_on_200(self) -> None:
        responses_lib.add(
            responses_lib.GET,
            REQUESTS_URL,
            json=_pypi_response("2.32.4"),
            status=200,
        )

        adapter = _make_adapter()
        result = adapter.get_latest_version("requests")

        assert result.is_ok()
        assert result.unwrap() == Version.from_string("2.32.4")

    @responses_lib.activate
    def test_returns_err_on_404(self) -> None:
        responses_lib.add(
            responses_lib.GET,
            NONEXISTENT_URL,
            status=404,
        )

        adapter = _make_adapter()
        result = adapter.get_latest_version("nonexistent-xyz")

        assert result.is_err()
        assert isinstance(result.unwrap_or(None) or result, Err)
        # Verify it's a PackageNotFoundError
        match result:
            case Err(e):
                assert isinstance(e, PackageNotFoundError)

    @responses_lib.activate
    def test_returns_registry_error_on_non_200_non_404(self) -> None:
        responses_lib.add(
            responses_lib.GET,
            REQUESTS_URL,
            status=503,
        )

        adapter = _make_adapter()
        result = adapter.get_latest_version("requests")
        assert result.is_err()

    @responses_lib.activate
    def test_caches_result_on_second_call(self) -> None:
        responses_lib.add(
            responses_lib.GET,
            REQUESTS_URL,
            json=_pypi_response("2.32.4"),
            status=200,
        )

        adapter = _make_adapter()
        result1 = adapter.get_latest_version("requests")
        result2 = adapter.get_latest_version("requests")

        # Only 1 HTTP call should have been made (second is from cache)
        assert len(responses_lib.calls) == 1
        assert result1 == result2

    @responses_lib.activate
    def test_handles_malformed_json(self) -> None:
        responses_lib.add(
            responses_lib.GET,
            REQUESTS_URL,
            json={"unexpected": "format"},
            status=200,
        )

        adapter = _make_adapter()
        result = adapter.get_latest_version("requests")
        assert result.is_err()

    @responses_lib.activate
    def test_network_error_returns_err(self) -> None:
        import requests as req_lib

        responses_lib.add(
            responses_lib.GET,
            REQUESTS_URL,
            body=req_lib.ConnectionError("Network unreachable"),
        )

        adapter = _make_adapter()
        result = adapter.get_latest_version("requests")
        assert result.is_err()


class TestPyPIAdapterGetLatestVersionsBatch:
    @responses_lib.activate
    def test_returns_dict_with_all_packages(self) -> None:
        responses_lib.add(
            responses_lib.GET, REQUESTS_URL, json=_pypi_response("2.32.4"), status=200
        )
        responses_lib.add(responses_lib.GET, FLASK_URL, json=_pypi_response("3.1.0"), status=200)

        adapter = _make_adapter()
        results = adapter.get_latest_versions_batch(["requests", "flask"])

        assert "requests" in results
        assert "flask" in results
        assert results["requests"].is_ok()
        assert results["flask"].is_ok()
        assert results["requests"].unwrap() == Version.from_string("2.32.4")
        assert results["flask"].unwrap() == Version.from_string("3.1.0")

    @responses_lib.activate
    def test_partial_failures_in_batch(self) -> None:
        responses_lib.add(
            responses_lib.GET, REQUESTS_URL, json=_pypi_response("2.32.4"), status=200
        )
        responses_lib.add(responses_lib.GET, NONEXISTENT_URL, status=404)

        adapter = _make_adapter()
        results = adapter.get_latest_versions_batch(["requests", "nonexistent-xyz"])

        assert results["requests"].is_ok()
        assert results["nonexistent-xyz"].is_err()

    @responses_lib.activate
    def test_uses_cache_for_already_queried_packages(self) -> None:
        responses_lib.add(
            responses_lib.GET, REQUESTS_URL, json=_pypi_response("2.32.4"), status=200
        )

        adapter = _make_adapter()
        # Prime cache
        adapter.get_latest_version("requests")

        # Batch query — should use cache for requests
        results = adapter.get_latest_versions_batch(["requests"])
        assert len(responses_lib.calls) == 1  # No additional HTTP call
        assert results["requests"].is_ok()

    @responses_lib.activate
    def test_empty_list_returns_empty_dict(self) -> None:
        adapter = _make_adapter()
        results = adapter.get_latest_versions_batch([])
        assert results == {}
