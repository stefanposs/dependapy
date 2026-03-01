"""Tests für dependapy.application.config — AppConfig (frozen dataclass)."""

from __future__ import annotations

import pytest

from dependapy.application.config import AppConfig, VCSProvider


class TestAppConfigDefaults:
    def test_default_values(self) -> None:
        cfg = AppConfig()
        assert cfg.vcs_provider == VCSProvider.OFFLINE
        assert cfg.vcs_token is None
        assert cfg.api_timeout == 10
        assert cfg.vcs_base_branch == "main"
        assert cfg.branch_prefix == "dependapy/"
        assert cfg.log_level == "INFO"

    def test_frozen(self) -> None:
        cfg = AppConfig()
        with pytest.raises(AttributeError):
            cfg.api_timeout = 99  # type: ignore[misc]


class TestAppConfigFromEnv:
    def test_reads_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEPENDAPY_VCS_TOKEN", "ghp_test123")
        monkeypatch.setenv("DEPENDAPY_VCS_PROVIDER", "github")
        monkeypatch.setenv("DEPENDAPY_API_TIMEOUT", "30")

        cfg = AppConfig.from_env()
        assert cfg.vcs_token == "ghp_test123"
        assert cfg.vcs_provider == VCSProvider.GITHUB
        assert cfg.api_timeout == 30

    def test_overrides_take_priority(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEPENDAPY_VCS_PROVIDER", "github")
        cfg = AppConfig.from_env(vcs_provider="offline")
        assert cfg.vcs_provider == VCSProvider.OFFLINE

    def test_none_overrides_ignored(self) -> None:
        cfg = AppConfig.from_env(vcs_token=None)
        assert cfg.vcs_token is None

    def test_empty_token_becomes_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEPENDAPY_VCS_TOKEN", "")
        cfg = AppConfig.from_env()
        assert cfg.vcs_token is None


class TestVCSProvider:
    def test_github_value(self) -> None:
        assert VCSProvider("github") == VCSProvider.GITHUB

    def test_offline_value(self) -> None:
        assert VCSProvider("offline") == VCSProvider.OFFLINE

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValueError):
            VCSProvider("gitlab")
