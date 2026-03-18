"""Tests für den CODEOWNERS Parser."""

from __future__ import annotations

from pathlib import Path

from dependapy.infrastructure.adapters.codeowners import (
    CodeownersEntry,
    find_owners_for_file,
    find_owners_for_files,
    parse_codeowners,
)


class TestCodeownersEntry:
    """Tests für CodeownersEntry.matches()."""

    def test_exact_file_match(self) -> None:
        entry = CodeownersEntry("pyproject.toml", ["@alice"])
        assert entry.matches("pyproject.toml")

    def test_directory_pattern_matches_file_inside(self) -> None:
        entry = CodeownersEntry("src/", ["@team/backend"])
        assert entry.matches("src/main.py")
        assert entry.matches("src/deep/nested/file.py")

    def test_directory_pattern_does_not_match_outside(self) -> None:
        entry = CodeownersEntry("src/", ["@team/backend"])
        assert not entry.matches("tests/test_main.py")

    def test_glob_pattern_matches(self) -> None:
        entry = CodeownersEntry("*.toml", ["@ops"])
        assert entry.matches("pyproject.toml")
        assert entry.matches("config.toml")

    def test_glob_pattern_does_not_match_other_extension(self) -> None:
        entry = CodeownersEntry("*.toml", ["@ops"])
        assert not entry.matches("README.md")

    def test_path_prefix_match_without_trailing_slash(self) -> None:
        entry = CodeownersEntry("dependapy", ["@team/core"])
        assert entry.matches("dependapy/main.py")
        assert entry.matches("dependapy/domain/models.py")

    def test_leading_slash_is_stripped(self) -> None:
        entry = CodeownersEntry("/src/", ["@alice"])
        assert entry.matches("src/main.py")

    def test_no_match_for_unrelated_path(self) -> None:
        entry = CodeownersEntry("docs/", ["@docs-team"])
        assert not entry.matches("src/main.py")


class TestParseCodeowners:
    """Tests für parse_codeowners()."""

    def test_parses_standard_codeowners_file(self, tmp_path: Path) -> None:
        codeowners_dir = tmp_path / ".github"
        codeowners_dir.mkdir()
        codeowners_file = codeowners_dir / "CODEOWNERS"
        codeowners_file.write_text(
            "# Global owners\n* @global-owner\n*.toml @ops-team\ndependapy/ @team/core @alice\n"
        )

        entries = parse_codeowners(tmp_path)
        assert len(entries) == 3
        assert entries[0].pattern == "*"
        assert entries[0].owners == ["@global-owner"]
        assert entries[1].pattern == "*.toml"
        assert entries[1].owners == ["@ops-team"]
        assert entries[2].pattern == "dependapy/"
        assert entries[2].owners == ["@team/core", "@alice"]

    def test_returns_empty_when_no_file(self, tmp_path: Path) -> None:
        entries = parse_codeowners(tmp_path)
        assert entries == []

    def test_ignores_comment_lines(self, tmp_path: Path) -> None:
        codeowners = tmp_path / "CODEOWNERS"
        codeowners.write_text("# Only comments\n# Another comment\n")
        entries = parse_codeowners(tmp_path)
        assert entries == []

    def test_ignores_empty_lines(self, tmp_path: Path) -> None:
        codeowners = tmp_path / "CODEOWNERS"
        codeowners.write_text("\n\n* @owner\n\n")
        entries = parse_codeowners(tmp_path)
        assert len(entries) == 1

    def test_finds_codeowners_in_root(self, tmp_path: Path) -> None:
        codeowners = tmp_path / "CODEOWNERS"
        codeowners.write_text("* @root-owner\n")
        entries = parse_codeowners(tmp_path)
        assert len(entries) == 1

    def test_finds_codeowners_in_docs(self, tmp_path: Path) -> None:
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        codeowners = docs_dir / "CODEOWNERS"
        codeowners.write_text("docs/ @docs-team\n")
        entries = parse_codeowners(tmp_path)
        assert len(entries) == 1

    def test_prefers_github_directory(self, tmp_path: Path) -> None:
        """GitHub CODEOWNERS has priority over root CODEOWNERS."""
        # Create both .github/CODEOWNERS and root CODEOWNERS
        github_dir = tmp_path / ".github"
        github_dir.mkdir()
        (github_dir / "CODEOWNERS").write_text("* @github-owner\n")
        (tmp_path / "CODEOWNERS").write_text("* @root-owner\n")

        entries = parse_codeowners(tmp_path)
        assert len(entries) == 1
        assert entries[0].owners == ["@github-owner"]


class TestFindOwnersForFile:
    """Tests für find_owners_for_file()."""

    def test_last_matching_rule_wins(self) -> None:
        entries = [
            CodeownersEntry("*", ["@global"]),
            CodeownersEntry("*.toml", ["@ops"]),
        ]
        owners = find_owners_for_file("pyproject.toml", entries)
        assert owners == ["@ops"]

    def test_returns_empty_when_no_match(self) -> None:
        entries = [CodeownersEntry("src/", ["@team"])]
        owners = find_owners_for_file("README.md", entries)
        assert owners == []

    def test_specific_rule_overrides_global(self) -> None:
        entries = [
            CodeownersEntry("*", ["@global"]),
            CodeownersEntry("dependapy/", ["@core-team"]),
        ]
        owners = find_owners_for_file("dependapy/main.py", entries)
        assert owners == ["@core-team"]


class TestFindOwnersForFiles:
    """Tests für find_owners_for_files()."""

    def test_collects_unique_owners_across_files(self) -> None:
        entries = [
            CodeownersEntry("*.toml", ["@ops"]),
            CodeownersEntry("dependapy/", ["@core", "@alice"]),
        ]
        owners = find_owners_for_files(
            ["pyproject.toml", "dependapy/main.py"],
            entries,
        )
        assert owners == ["@alice", "@core", "@ops"]

    def test_returns_empty_for_no_matches(self) -> None:
        entries = [CodeownersEntry("src/", ["@team"])]
        owners = find_owners_for_files(["README.md", "LICENSE"], entries)
        assert owners == []

    def test_deduplicates_owners(self) -> None:
        entries = [
            CodeownersEntry("*", ["@shared-owner"]),
        ]
        owners = find_owners_for_files(["file1.py", "file2.py"], entries)
        assert owners == ["@shared-owner"]
