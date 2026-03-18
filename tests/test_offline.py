"""Tests für den Offline-Betrieb — OfflineRegistryAdapter und Config."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from dependapy.domain.result import Err, Ok
from dependapy.infrastructure.adapters.offline_registry import OfflineRegistryAdapter


class TestOfflineRegistryFromUvLock:
    def test_load_from_uv_lock(self, tmp_path: Path) -> None:
        uv_lock = dedent("""\
            version = 1
            requires-python = ">=3.12"

            [[package]]
            name = "requests"
            version = "2.32.3"
            source = { registry = "https://pypi.org/simple" }

            [[package]]
            name = "flask"
            version = "3.1.0"
            source = { registry = "https://pypi.org/simple" }
        """)
        (tmp_path / "uv.lock").write_text(uv_lock)

        adapter = OfflineRegistryAdapter(tmp_path)
        result = adapter.get_latest_version("requests")
        assert isinstance(result, Ok)
        assert str(result.unwrap()) == "2.32.3"

        result2 = adapter.get_latest_version("flask")
        assert isinstance(result2, Ok)
        assert str(result2.unwrap()) == "3.1.0"

    def test_package_not_found(self, tmp_path: Path) -> None:
        (tmp_path / "uv.lock").write_text('version = 1\nrequires-python = ">=3.12"\n')
        adapter = OfflineRegistryAdapter(tmp_path)
        result = adapter.get_latest_version("nonexistent")
        assert isinstance(result, Err)

    def test_batch_lookup(self, tmp_path: Path) -> None:
        uv_lock = dedent("""\
            version = 1

            [[package]]
            name = "requests"
            version = "2.32.3"

            [[package]]
            name = "flask"
            version = "3.1.0"
        """)
        (tmp_path / "uv.lock").write_text(uv_lock)

        adapter = OfflineRegistryAdapter(tmp_path)
        results = adapter.get_latest_versions_batch(["requests", "flask", "unknown"])
        assert isinstance(results["requests"], Ok)
        assert isinstance(results["flask"], Ok)
        assert isinstance(results["unknown"], Err)

    def test_normalized_names(self, tmp_path: Path) -> None:
        """PEP 503 name normalization: dashes, underscores, dots → interchangeable."""
        uv_lock = dedent("""\
            version = 1

            [[package]]
            name = "my-cool-package"
            version = "1.0.0"
        """)
        (tmp_path / "uv.lock").write_text(uv_lock)

        adapter = OfflineRegistryAdapter(tmp_path)
        assert isinstance(adapter.get_latest_version("my-cool-package"), Ok)
        assert isinstance(adapter.get_latest_version("my_cool_package"), Ok)
        assert isinstance(adapter.get_latest_version("my.cool.package"), Ok)


class TestOfflineRegistryFromRequirements:
    def test_load_from_requirements_txt(self, tmp_path: Path) -> None:
        reqs = dedent("""\
            requests==2.32.3
            flask==3.1.0
            # A comment
            -r other.txt
            some-package>=1.0  # Not pinned, ignored
        """)
        (tmp_path / "requirements.txt").write_text(reqs)

        adapter = OfflineRegistryAdapter(tmp_path)
        result = adapter.get_latest_version("requests")
        assert isinstance(result, Ok)
        assert str(result.unwrap()) == "2.32.3"

        # Non-pinned packages should not be loaded
        result2 = adapter.get_latest_version("some-package")
        assert isinstance(result2, Err)

    def test_uv_lock_has_priority(self, tmp_path: Path) -> None:
        """uv.lock wird vor requirements.txt geladen."""
        (tmp_path / "uv.lock").write_text(
            'version = 1\n\n[[package]]\nname = "requests"\nversion = "2.99.0"\n'
        )
        (tmp_path / "requirements.txt").write_text("requests==1.0.0\n")

        adapter = OfflineRegistryAdapter(tmp_path)
        result = adapter.get_latest_version("requests")
        assert isinstance(result, Ok)
        assert str(result.unwrap()) == "2.99.0"


class TestOfflineRegistryNoFiles:
    def test_empty_project(self, tmp_path: Path) -> None:
        adapter = OfflineRegistryAdapter(tmp_path)
        result = adapter.get_latest_version("requests")
        assert isinstance(result, Err)


class TestOfflineConfig:
    def test_offline_config_env(self) -> None:
        import os

        from dependapy.application.config import AppConfig

        old_val = os.environ.get("DEPENDAPY_OFFLINE")
        try:
            os.environ["DEPENDAPY_OFFLINE"] = "true"
            config = AppConfig.from_env()
            assert config.offline is True
        finally:
            if old_val is None:
                os.environ.pop("DEPENDAPY_OFFLINE", None)
            else:
                os.environ["DEPENDAPY_OFFLINE"] = old_val

    def test_offline_default_false(self) -> None:
        import os

        from dependapy.application.config import AppConfig

        old_val = os.environ.pop("DEPENDAPY_OFFLINE", None)
        try:
            config = AppConfig.from_env()
            assert config.offline is False
        finally:
            if old_val is not None:
                os.environ["DEPENDAPY_OFFLINE"] = old_val
