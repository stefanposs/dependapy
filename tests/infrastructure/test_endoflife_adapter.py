"""Tests für dependapy.infrastructure.adapters.endoflife — EndOfLifeAdapter."""

from __future__ import annotations

import pytest
import responses as responses_lib

from dependapy.domain.result import Ok
from dependapy.domain.value_objects import Version
from dependapy.infrastructure.adapters.endoflife import (
    _FALLBACK_VERSION_STRINGS,
    EndOfLifeAdapter,
    _fallback_versions,
)
from dependapy.infrastructure.http import HttpClient

EOL_URL = "https://endoflife.date/api/python.json"


@pytest.fixture(autouse=True)
def _clear_fallback_cache() -> None:
    """Clear functools.cache between tests."""
    _fallback_versions.cache_clear()


_API_RESPONSE = [
    {"cycle": "3.13", "eol": False},
    {"cycle": "3.12", "eol": False},
    {"cycle": "3.11", "eol": False},
    {"cycle": "3.10", "eol": False},
    {"cycle": "3.9", "eol": True},
    {"cycle": "2.7", "eol": True},
]


def _make_adapter(num_versions: int = 3) -> EndOfLifeAdapter:
    return EndOfLifeAdapter(
        http_client=HttpClient(max_retries=0),
        api_url=EOL_URL,
        num_versions=num_versions,
    )


class TestGetSupportedVersions:
    @responses_lib.activate
    def test_returns_top_n_versions_from_api(self) -> None:
        responses_lib.add(responses_lib.GET, EOL_URL, json=_API_RESPONSE, status=200)

        adapter = _make_adapter(num_versions=3)
        result = adapter.get_supported_versions()

        assert isinstance(result, Ok)
        versions = result.value
        assert len(versions) == 3
        assert versions[0] == Version.from_string("3.13")
        assert versions[1] == Version.from_string("3.12")
        assert versions[2] == Version.from_string("3.11")

    @responses_lib.activate
    def test_returns_2_versions_when_configured(self) -> None:
        responses_lib.add(responses_lib.GET, EOL_URL, json=_API_RESPONSE, status=200)

        adapter = _make_adapter(num_versions=2)
        result = adapter.get_supported_versions()

        assert isinstance(result, Ok)
        assert len(result.value) == 2

    @responses_lib.activate
    def test_caches_successful_response(self) -> None:
        responses_lib.add(responses_lib.GET, EOL_URL, json=_API_RESPONSE, status=200)

        adapter = _make_adapter()
        result1 = adapter.get_supported_versions()
        result2 = adapter.get_supported_versions()

        assert isinstance(result1, Ok)
        assert isinstance(result2, Ok)
        assert result1.value == result2.value
        # Only 1 HTTP call should have been made
        assert len(responses_lib.calls) == 1

    @responses_lib.activate
    def test_fallback_on_http_500(self) -> None:
        responses_lib.add(responses_lib.GET, EOL_URL, status=500)

        adapter = _make_adapter()
        result = adapter.get_supported_versions()

        assert isinstance(result, Ok)
        expected = [Version.from_string(v) for v in _FALLBACK_VERSION_STRINGS]
        assert result.value == expected

    @responses_lib.activate
    def test_fallback_on_network_error(self) -> None:
        responses_lib.add(
            responses_lib.GET,
            EOL_URL,
            body=responses_lib.ConnectionError("Network unreachable"),
        )

        adapter = _make_adapter()
        result = adapter.get_supported_versions()

        assert isinstance(result, Ok)
        expected = [Version.from_string(v) for v in _FALLBACK_VERSION_STRINGS]
        assert result.value == expected

    @responses_lib.activate
    def test_fallback_on_invalid_json(self) -> None:
        responses_lib.add(
            responses_lib.GET,
            EOL_URL,
            body="not valid json",
            status=200,
            content_type="application/json",
        )

        adapter = _make_adapter()
        result = adapter.get_supported_versions()

        assert isinstance(result, Ok)
        expected = [Version.from_string(v) for v in _FALLBACK_VERSION_STRINGS]
        assert result.value == expected

    @responses_lib.activate
    def test_fallback_cached_prevents_repeated_api_calls(self) -> None:
        """B2 regression: Fallback soll gecacht werden, damit nicht jeder
        Aufruf erneut die API kontaktiert."""
        responses_lib.add(responses_lib.GET, EOL_URL, status=500)

        adapter = _make_adapter()
        adapter.get_supported_versions()
        adapter.get_supported_versions()

        # Should only call API once — second call uses cache
        assert len(responses_lib.calls) == 1

    @responses_lib.activate
    def test_filters_only_python3(self) -> None:
        """Soll nur Python 3.x Versionen zurückgeben."""
        data = [
            {"cycle": "3.13", "eol": False},
            {"cycle": "2.7", "eol": True},
            {"cycle": "3.12", "eol": False},
        ]
        responses_lib.add(responses_lib.GET, EOL_URL, json=data, status=200)

        adapter = _make_adapter(num_versions=5)
        result = adapter.get_supported_versions()

        assert isinstance(result, Ok)
        # Should only contain 3.x versions
        for v in result.value:
            assert v.major == 3
