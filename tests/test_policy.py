"""Tests für den Policy Domain Model und Policy Loader."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from dependapy.application.use_cases import AnalyzeDependencies, SubmitChanges
from dependapy.domain.policy import (
    AllowRule,
    CommitMessage,
    DependencyGroup,
    IgnoreRule,
    Policy,
)
from dependapy.domain.result import Ok
from dependapy.infrastructure.adapters.policy_loader import load_policy
from tests.factories import make_dep, make_project
from tests.fakes import (
    FakePackageRegistry,
    FakeProjectRepository,
    FakePythonVersionRegistry,
    FakeVCSPort,
)

# === Policy Domain Model Tests ===


class TestIgnoreRule:
    def test_exact_match(self) -> None:
        rule = IgnoreRule(name="requests")
        assert rule.matches("requests")
        assert not rule.matches("flask")

    def test_glob_match(self) -> None:
        rule = IgnoreRule(name="boto*")
        assert rule.matches("boto3")
        assert rule.matches("botocore")
        assert not rule.matches("flask")

    def test_case_insensitive(self) -> None:
        rule = IgnoreRule(name="Requests")
        assert rule.matches("requests")
        assert rule.matches("REQUESTS")


class TestAllowRule:
    def test_exact_match(self) -> None:
        rule = AllowRule(name="requests", update_types=frozenset({"minor", "patch"}))
        assert rule.matches("requests")
        assert not rule.matches("flask")

    def test_glob_match(self) -> None:
        rule = AllowRule(name="*", update_types=frozenset({"patch"}))
        assert rule.matches("anything")

    def test_default_all_types(self) -> None:
        rule = AllowRule(name="*")
        assert rule.update_types == frozenset({"major", "minor", "patch"})


class TestDependencyGroup:
    def test_matches_patterns(self) -> None:
        group = DependencyGroup(name="aws", patterns=("boto*", "aws*"))
        assert group.matches("boto3")
        assert group.matches("aws-cdk")
        assert not group.matches("requests")

    def test_empty_patterns(self) -> None:
        group = DependencyGroup(name="empty")
        assert not group.matches("anything")


class TestPolicy:
    def test_is_ignored(self) -> None:
        policy = Policy(ignore=(IgnoreRule(name="legacy-pkg"), IgnoreRule(name="boto*")))
        assert policy.is_ignored("legacy-pkg")
        assert policy.is_ignored("boto3")
        assert not policy.is_ignored("requests")

    def test_allowed_update_types_default(self) -> None:
        policy = Policy()
        assert policy.allowed_update_types("anything") == frozenset({"major", "minor", "patch"})

    def test_allowed_update_types_restricted(self) -> None:
        policy = Policy(
            allow=(
                AllowRule(name="requests", update_types=frozenset({"major", "minor", "patch"})),
                AllowRule(name="*", update_types=frozenset({"minor", "patch"})),
            )
        )
        # requests has its own specific rule
        assert policy.allowed_update_types("requests") == frozenset({"major", "minor", "patch"})
        # Everything else matches the wildcard
        assert policy.allowed_update_types("flask") == frozenset({"minor", "patch"})

    def test_find_group(self) -> None:
        policy = Policy(
            groups=(
                DependencyGroup(name="aws", patterns=("boto*",)),
                DependencyGroup(name="web", patterns=("flask*", "django*")),
            )
        )
        assert policy.find_group("boto3") is not None
        assert policy.find_group("boto3").name == "aws"  # type: ignore[union-attr]
        assert policy.find_group("flask") is not None
        assert policy.find_group("unknown") is None

    def test_format_commit_message_with_scope(self) -> None:
        policy = Policy(commit_message=CommitMessage(prefix="fix(deps)", include_scope=True))
        msg = policy.format_commit_message("api", "update requests")
        assert msg == "fix(deps)(api): update requests"

    def test_format_commit_message_without_scope(self) -> None:
        policy = Policy(commit_message=CommitMessage(prefix="chore", include_scope=False))
        msg = policy.format_commit_message("api", "update requests")
        assert msg == "chore: update requests"


# === Policy Loader Tests ===


class TestPolicyLoader:
    def test_load_not_found(self, tmp_path: Path) -> None:
        result = load_policy(tmp_path)
        assert result.is_err()

    def test_load_valid_policy(self, tmp_path: Path) -> None:
        yaml_content = dedent("""\
            version: 1
            ignore:
              - name: "legacy-pkg"
                reason: "deprecated"
              - "old-package"
            allow:
              - name: "*"
                update-types: ["minor", "patch"]
            labels:
              - dependencies
              - automated
            reviewers:
              - "@user1"
              - "@org/team"
            assignees:
              - "@user2"
            commit-message:
              prefix: "fix(deps)"
              include-scope: false
            groups:
              - name: "aws"
                patterns: ["boto*", "aws*"]
        """)
        (tmp_path / ".dependapy.yml").write_text(yaml_content)

        result = load_policy(tmp_path)
        assert result.is_ok()
        policy = result.unwrap()

        assert policy.version == 1
        assert len(policy.ignore) == 2
        assert policy.ignore[0].name == "legacy-pkg"
        assert policy.ignore[0].reason == "deprecated"
        assert policy.ignore[1].name == "old-package"
        assert len(policy.allow) == 1
        assert policy.allow[0].update_types == frozenset({"minor", "patch"})
        assert policy.labels == ("dependencies", "automated")
        assert policy.reviewers == ("@user1", "@org/team")
        assert policy.assignees == ("@user2",)
        assert policy.commit_message.prefix == "fix(deps)"
        assert policy.commit_message.include_scope is False
        assert len(policy.groups) == 1
        assert policy.groups[0].name == "aws"

    def test_load_yaml_variant(self, tmp_path: Path) -> None:
        (tmp_path / ".dependapy.yaml").write_text("version: 1\n")
        result = load_policy(tmp_path)
        assert result.is_ok()

    def test_load_invalid_yaml(self, tmp_path: Path) -> None:
        (tmp_path / ".dependapy.yml").write_text(": invalid: yaml: [")
        result = load_policy(tmp_path)
        assert result.is_err()

    def test_load_non_dict_yaml(self, tmp_path: Path) -> None:
        (tmp_path / ".dependapy.yml").write_text("- just a list\n")
        result = load_policy(tmp_path)
        assert result.is_err()

    def test_load_invalid_version(self, tmp_path: Path) -> None:
        (tmp_path / ".dependapy.yml").write_text("version: 99\n")
        result = load_policy(tmp_path)
        assert result.is_err()

    def test_load_minimal_policy(self, tmp_path: Path) -> None:
        (tmp_path / ".dependapy.yml").write_text("version: 1\n")
        result = load_policy(tmp_path)
        assert result.is_ok()
        policy = result.unwrap()
        assert policy.ignore == ()
        assert policy.allow == ()
        assert policy.labels == ()


# === Policy Integration in Use Cases ===


class TestPolicyInAnalyze:
    def test_ignored_packages_excluded(self) -> None:
        registry = FakePackageRegistry(
            versions={"requests": "3.0.0", "legacy": "2.0.0"},
        )
        proj_repo = FakeProjectRepository()
        python_reg = FakePythonVersionRegistry()

        proj = make_project(
            make_dep("requests", "2.31.0", latest="3.0.0"),
            make_dep("legacy", "1.0.0", latest="2.0.0"),
            path=Path("/tmp/test"),
        )
        proj_repo.add_project(proj)

        uc = AnalyzeDependencies(
            registry=registry,
            project_repo=proj_repo,
            python_registry=python_reg,
        )

        result_no_policy = uc.execute(Path("/tmp/test"))
        assert isinstance(result_no_policy, Ok)
        assert result_no_policy.unwrap()[0].outdated_count == 2

    def test_policy_filters_ignored(self) -> None:
        registry = FakePackageRegistry(
            versions={"requests": "3.0.0", "legacy": "2.0.0"},
        )
        proj_repo = FakeProjectRepository()
        python_reg = FakePythonVersionRegistry()

        proj = make_project(
            make_dep("requests", "2.31.0", latest="3.0.0"),
            make_dep("legacy", "1.0.0", latest="2.0.0"),
            path=Path("/tmp/test"),
        )
        proj_repo.add_project(proj)

        uc = AnalyzeDependencies(
            registry=registry,
            project_repo=proj_repo,
            python_registry=python_reg,
        )
        policy = Policy(ignore=(IgnoreRule(name="legacy"),))
        result = uc.execute(Path("/tmp/test"), policy=policy)
        assert isinstance(result, Ok)
        assert result.unwrap()[0].outdated_count == 1

    def test_policy_filters_update_types(self) -> None:
        registry = FakePackageRegistry(
            versions={"requests": "3.0.0"},
        )
        proj_repo = FakeProjectRepository()
        python_reg = FakePythonVersionRegistry()

        proj = make_project(
            make_dep("requests", "2.31.0", latest="3.0.0"),
            path=Path("/tmp/test"),
        )
        proj_repo.add_project(proj)

        uc = AnalyzeDependencies(
            registry=registry,
            project_repo=proj_repo,
            python_registry=python_reg,
        )
        policy = Policy(
            allow=(
                AllowRule(
                    name="*",
                    update_types=frozenset({"minor", "patch"}),
                ),
            ),
        )
        result = uc.execute(Path("/tmp/test"), policy=policy)
        assert isinstance(result, Ok)
        assert result.unwrap()[0].outdated_count == 0


class TestPolicyInSubmit:
    def test_policy_labels_in_pr(self) -> None:
        vcs = FakeVCSPort()
        uc = SubmitChanges(vcs=vcs)
        policy = Policy(labels=("dependencies", "automated"))

        result = uc.execute(
            Path("/tmp/repo"),
            [Path("/tmp/repo/pyproject.toml")],
            policy=policy,
        )
        assert isinstance(result, Ok)
        assert vcs.prs_created[0].labels == [
            "dependencies",
            "automated",
        ]

    def test_policy_reviewers_merged_with_codeowners(self) -> None:
        assert SubmitChanges._merge_reviewers(
            ["@alice"],
            Policy(reviewers=("@bob", "@org/team")),
        ) == ["@alice", "@bob", "@org/team"]

    def test_policy_commit_message(self) -> None:
        vcs = FakeVCSPort()
        uc = SubmitChanges(vcs=vcs)
        policy = Policy(
            commit_message=CommitMessage(
                prefix="build(deps)",
                include_scope=True,
            ),
        )

        result = uc.execute(
            Path("/tmp/repo"),
            [Path("/tmp/repo/pyproject.toml")],
            policy=policy,
        )
        assert isinstance(result, Ok)
        assert "build(deps)" in vcs.commits_made[0]


# === Auto-Merge Tests ===


class TestAutoMerge:
    def test_auto_merge_in_pr_request(self) -> None:
        vcs = FakeVCSPort()
        uc = SubmitChanges(vcs=vcs)
        policy = Policy(auto_merge=True)

        result = uc.execute(
            Path("/tmp/repo"),
            [Path("/tmp/repo/pyproject.toml")],
            policy=policy,
        )
        assert isinstance(result, Ok)
        assert vcs.prs_created[0].auto_merge is True

    def test_no_auto_merge_by_default(self) -> None:
        vcs = FakeVCSPort()
        uc = SubmitChanges(vcs=vcs)

        result = uc.execute(
            Path("/tmp/repo"),
            [Path("/tmp/repo/pyproject.toml")],
        )
        assert isinstance(result, Ok)
        assert vcs.prs_created[0].auto_merge is False

    def test_auto_merge_parsed_from_policy(self, tmp_path: Path) -> None:
        yaml_content = dedent("""\
            version: 1
            auto-merge: true
        """)
        (tmp_path / ".dependapy.yml").write_text(yaml_content)
        result = load_policy(tmp_path)
        assert result.is_ok()
        assert result.unwrap().auto_merge is True


# === Dependency Grouping Tests ===


class TestGroupedPRs:
    def _make_analysis(
        self,
        name: str,
        *dep_names: str,
        path: Path | None = None,
    ) -> tuple:
        """Erzeugt ein AnalysisResult + Dateien-Mapping."""
        from dependapy.application.dtos import AnalysisResult

        deps = [make_dep(n, "1.0.0", latest="2.0.0") for n in dep_names]
        proj_path = path or Path(f"/tmp/{name}")
        proj = make_project(*deps, name=name, path=proj_path)
        proj.mark_analyzed()
        analysis = AnalysisResult(
            project=proj,
            outdated_count=len(deps),
            total_count=len(deps),
        )
        files = [proj_path / "pyproject.toml"]
        return analysis, {proj_path: files}

    def test_grouped_deps_single_pr(self) -> None:
        """Dependencies in der gleichen Gruppe → ein PR."""
        vcs = FakeVCSPort()
        uc = SubmitChanges(vcs=vcs)

        policy = Policy(
            groups=(
                DependencyGroup(
                    name="aws",
                    patterns=("boto*", "s3transfer"),
                ),
            ),
        )

        a1, f1 = self._make_analysis(
            "svc-a",
            "boto3",
            path=Path("/tmp/svc-a"),
        )
        a2, f2 = self._make_analysis(
            "svc-b",
            "s3transfer",
            path=Path("/tmp/svc-b"),
        )

        all_files = {**f1, **f2}
        results = uc.execute_per_project(
            repo_path=Path("/tmp"),
            analysis_results=[a1, a2],
            updated_files_by_project=all_files,
            policy=policy,
        )

        # Nur 1 PR für die "aws"-Gruppe
        ok_results = [r for r in results if isinstance(r, Ok)]
        assert len(ok_results) == 1
        assert "group-aws" in vcs.branches_created[0]

    def test_ungrouped_get_individual_prs(self) -> None:
        """Dependencies ohne Gruppen-Match → per-Projekt PRs."""
        vcs = FakeVCSPort()
        uc = SubmitChanges(vcs=vcs)

        policy = Policy(
            groups=(
                DependencyGroup(
                    name="aws",
                    patterns=("boto*",),
                ),
            ),
        )

        a1, f1 = self._make_analysis(
            "svc-a",
            "flask",
            path=Path("/tmp/svc-a"),
        )
        a2, f2 = self._make_analysis(
            "svc-b",
            "django",
            path=Path("/tmp/svc-b"),
        )

        all_files = {**f1, **f2}
        results = uc.execute_per_project(
            repo_path=Path("/tmp"),
            analysis_results=[a1, a2],
            updated_files_by_project=all_files,
            policy=policy,
        )

        ok_results = [r for r in results if isinstance(r, Ok)]
        assert len(ok_results) == 2
        branches = vcs.branches_created
        assert any("update-svc-a" in b for b in branches)
        assert any("update-svc-b" in b for b in branches)

    def test_mixed_grouped_and_ungrouped(self) -> None:
        """Gemischt: Gruppen-PR + individuelle PRs."""
        vcs = FakeVCSPort()
        uc = SubmitChanges(vcs=vcs)

        policy = Policy(
            groups=(
                DependencyGroup(
                    name="testing",
                    patterns=("pytest*", "coverage"),
                ),
            ),
        )

        a1, f1 = self._make_analysis(
            "lib-a",
            "pytest",
            path=Path("/tmp/lib-a"),
        )
        a2, f2 = self._make_analysis(
            "lib-b",
            "coverage",
            path=Path("/tmp/lib-b"),
        )
        a3, f3 = self._make_analysis(
            "app",
            "flask",
            path=Path("/tmp/app"),
        )

        all_files = {**f1, **f2, **f3}
        results = uc.execute_per_project(
            repo_path=Path("/tmp"),
            analysis_results=[a1, a2, a3],
            updated_files_by_project=all_files,
            policy=policy,
        )

        ok_results = [r for r in results if isinstance(r, Ok)]
        # 1 group PR (testing) + 1 individual PR (app/flask)
        assert len(ok_results) == 2

        branches = vcs.branches_created
        assert any("group-testing" in b for b in branches)
        assert any("update-app" in b for b in branches)

    def test_grouping_respects_max_prs(self) -> None:
        """max_prs begrenzt auch Gruppen-PRs."""
        vcs = FakeVCSPort()
        uc = SubmitChanges(vcs=vcs)

        policy = Policy(
            groups=(
                DependencyGroup(name="g1", patterns=("pkg-a",)),
                DependencyGroup(name="g2", patterns=("pkg-b",)),
                DependencyGroup(name="g3", patterns=("pkg-c",)),
            ),
        )

        analyses = []
        all_files: dict[Path, list[Path]] = {}
        for name in ("pkg-a", "pkg-b", "pkg-c"):
            a, f = self._make_analysis(
                name,
                name,
                path=Path(f"/tmp/{name}"),
            )
            analyses.append(a)
            all_files.update(f)

        results = uc.execute_per_project(
            repo_path=Path("/tmp"),
            analysis_results=analyses,
            updated_files_by_project=all_files,
            max_prs=2,
            policy=policy,
        )

        ok_results = [r for r in results if isinstance(r, Ok)]
        assert len(ok_results) == 2

    def test_no_groups_falls_back_to_per_project(self) -> None:
        """Ohne Gruppen-Definition → normales per-Projekt Verhalten."""
        vcs = FakeVCSPort()
        uc = SubmitChanges(vcs=vcs)

        policy = Policy()  # Keine Gruppen

        a1, f1 = self._make_analysis(
            "svc-a",
            "requests",
            path=Path("/tmp/svc-a"),
        )
        a2, f2 = self._make_analysis(
            "svc-b",
            "flask",
            path=Path("/tmp/svc-b"),
        )

        all_files = {**f1, **f2}
        results = uc.execute_per_project(
            repo_path=Path("/tmp"),
            analysis_results=[a1, a2],
            updated_files_by_project=all_files,
            policy=policy,
        )

        ok_results = [r for r in results if isinstance(r, Ok)]
        assert len(ok_results) == 2
