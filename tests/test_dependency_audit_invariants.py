# Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved
import json
import runpy
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

audit_module = runpy.run_path(
    str(Path(__file__).parents[1] / ".github/scripts/dependency_audit.py")
)
format_remaining_audit = audit_module["format_remaining_audit"]
format_audit = audit_module["format_audit"]
audit = audit_module["audit"]
prepare = audit_module["prepare"]


@pytest.fixture
def npm_project(tmp_path):
    (tmp_path / "package.json").write_text(
        json.dumps({"dependencies": {"renderer": "1.0.0"}})
    )
    (tmp_path / "package-lock.json").write_text('{"lockfileVersion": 3}')
    return tmp_path


@pytest.fixture
def pnpm_project(tmp_path):
    (tmp_path / "package.json").write_text(
        json.dumps(
            {"packageManager": "pnpm@11.21.0", "dependencies": {"renderer": "^1.0.0"}}
        )
    )
    (tmp_path / "pnpm-lock.yaml").write_text(
        yaml.safe_dump(
            {
                "lockfileVersion": "9.0",
                "importers": {".": {}},
                "packages": {"renderer@1.0.0": {}},
            }
        )
    )
    (tmp_path / "pnpm-workspace.yaml").write_text(
        yaml.safe_dump(
            {
                "packages": ["."],
                "minimumReleaseAge": 14400,
                "minimumReleaseAgeExclude": ["other@3.0.0"],
                "blockExoticSubdeps": True,
                "strictDepBuilds": True,
                "allowBuilds": {"core-js": False},
                "overrides": {"other": "3.0.0"},
                "resolutionMode": "highest",
            }
        )
    )
    return tmp_path


def test_info_advisory_is_reported_and_fix_attempt_includes_info(
    pnpm_project, monkeypatch
):
    commands = []
    response = {
        "metadata": {"vulnerabilities": {"info": 1, "total": 1}},
        "advisories": {
            "123": {
                "module_name": "renderer",
                "severity": "info",
                "title": "Informational renderer notice",
                "url": "https://github.com/advisories/GHSA-info",
                "vulnerable_versions": "<1.0.1",
                "patched_versions": ">=1.0.1",
                "findings": [{"version": "1.0.0"}],
            }
        },
    }

    def invoke(command, *, cwd, **kwargs):
        commands.append(command[5:])
        return subprocess.CompletedProcess(command, 1, json.dumps(response), "")

    monkeypatch.setattr(subprocess, "run", invoke)
    data = audit(pnpm_project)
    audit_module["fix_security"](pnpm_project, float("inf"))
    assert commands[:2] == [
        ["audit", "--json", "--audit-level", "info"],
        ["audit", "--fix=update", "--audit-level", "info", "--ignore-scripts"],
    ]
    assert commands[2][:4] == [
        "install",
        "--lockfile-only",
        "--no-frozen-lockfile",
        "--ignore-scripts",
    ]
    lock = audit_module["valid_snapshot"](pnpm_project)[3]
    for report in (format_remaining_audit(data, lock), format_audit(data, lock)):
        for detail in (
            "info",
            "Informational renderer notice",
            "https://github.com/advisories/GHSA-info",
            "<1.0.1",
            "1.0.0",
        ):
            assert detail in report


@pytest.mark.parametrize(
    "mutation", ["severity", "via", "nodes", "fixAvailable", "non-object", "empty-via"]
)
def test_audit_rejects_malformed_npm_vulnerability_details(
    npm_project, monkeypatch, mutation
):
    detail: Any = {
        "severity": "high",
        "range": "<1.0.1",
        "nodes": ["node_modules/renderer"],
        "via": [
            {
                "title": "Render bug",
                "url": "https://github.com/advisories/GHSA-render",
                "severity": "high",
                "range": "<1.0.1",
            }
        ],
        "fixAvailable": False,
    }
    if mutation == "severity":
        del detail["severity"]
    elif mutation == "via":
        del detail["via"][0]["range"]
    elif mutation == "nodes":
        detail["nodes"] = [None]
    elif mutation == "fixAvailable":
        detail["fixAvailable"] = {"name": 7}
    elif mutation == "non-object":
        detail = []
    else:
        detail["via"] = [""]

    response = {
        "metadata": {"vulnerabilities": {"high": 1, "total": 1}},
        "vulnerabilities": {"renderer": detail},
    }
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, **kwargs: subprocess.CompletedProcess(
            command, 1, json.dumps(response), ""
        ),
    )

    result = audit(npm_project)

    assert isinstance(result, str) and "unavailable" in result.lower()
    assert "unavailable" in format_audit(result, {}).lower()
    assert "unavailable" in format_remaining_audit(result, {}).lower()


@pytest.mark.parametrize(
    ("location", "severity"),
    [
        ("vulnerability", []),
        ("vulnerability", {}),
        ("via", []),
        ("via", {}),
    ],
)
def test_audit_rejects_non_scalar_npm_severity(
    npm_project, monkeypatch, location, severity
):
    detail: Any = {
        "severity": "high",
        "range": "<1.0.1",
        "nodes": ["node_modules/renderer"],
        "via": [
            {
                "title": "Render bug",
                "url": "https://github.com/advisories/GHSA-render",
                "severity": "high",
                "range": "<1.0.1",
            }
        ],
        "fixAvailable": False,
    }
    if location == "vulnerability":
        detail["severity"] = severity
    else:
        detail["via"][0]["severity"] = severity
    response = {
        "metadata": {"vulnerabilities": {"high": 1, "total": 1}},
        "vulnerabilities": {"renderer": detail},
    }
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, **kwargs: subprocess.CompletedProcess(
            command, 1, json.dumps(response), ""
        ),
    )

    result = audit(npm_project)

    assert isinstance(result, str) and "unavailable" in result.lower()


@pytest.mark.parametrize(
    "counts",
    [
        {"high": 2, "total": 2},
        {"low": 1, "total": 1},
    ],
)
def test_audit_rejects_npm_count_mismatches(npm_project, monkeypatch, counts):
    response = {
        "metadata": {"vulnerabilities": counts},
        "vulnerabilities": {
            "renderer": {
                "severity": "high",
                "range": "<1.0.1",
                "nodes": ["node_modules/renderer"],
                "via": [
                    {
                        "title": "Render bug",
                        "url": "https://github.com/advisories/GHSA-render",
                        "severity": "high",
                        "range": "<1.0.1",
                    }
                ],
                "fixAvailable": False,
            }
        },
    }
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, **kwargs: subprocess.CompletedProcess(
            command, 1, json.dumps(response), ""
        ),
    )

    result = audit(npm_project)

    assert isinstance(result, str) and "unavailable" in result.lower()


def test_audit_preserves_valid_npm_propagated_findings(npm_project, monkeypatch):
    response = {
        "metadata": {"vulnerabilities": {"high": 2, "total": 2}},
        "vulnerabilities": {
            "renderer": {
                "severity": "high",
                "range": "<1.0.1",
                "nodes": ["node_modules/renderer"],
                "via": [
                    {
                        "title": "Render bug",
                        "url": "https://github.com/advisories/GHSA-render",
                        "severity": "high",
                        "range": "<1.0.1",
                    }
                ],
                "fixAvailable": False,
            },
            "application": {
                "severity": "high",
                "range": "*",
                "nodes": ["node_modules/application"],
                "via": ["renderer"],
                "fixAvailable": False,
            },
        },
    }
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, **kwargs: subprocess.CompletedProcess(
            command, 1, json.dumps(response), ""
        ),
    )

    result = audit(npm_project)

    assert isinstance(result, dict)
    assert result["vulnerabilities"]["application"]["via"] == ["renderer"]
    assert "GHSA-render" in format_remaining_audit(result, {})


@pytest.mark.parametrize("exit_code", [0, 1])
@pytest.mark.parametrize(
    "operation, field, value",
    [
        ("initial-audit", "minimumReleaseAge", 1),
        ("initial-fix", "overrides", {"other": "changed"}),
        ("view", "allowBuilds", {}),
        ("install", "blockExoticSubdeps", False),
        ("followup-fix", "strictDepBuilds", False),
        ("frozen", "minimumReleaseAgeExclude", ["unrelated@9.0.0"]),
        ("build", "resolutionMode", "lowest-direct"),
        ("final-audit", "audit", {"ignore": ["GHSA-hidden"]}),
    ],
)
def test_valid_policy_mutation_restores_all_package_files(
    pnpm_project, monkeypatch, operation, field, value, exit_code
):
    workspace = pnpm_project / "pnpm-workspace.yaml"
    files = {
        name: (pnpm_project / name).read_bytes()
        for name in ("package.json", "pnpm-lock.yaml", "pnpm-workspace.yaml")
    }
    audits = fixes = 0
    mutated = False

    def invoke(command, *, cwd, **kwargs):
        nonlocal audits, fixes, mutated
        args = command[5:]
        stdout, boundary = "", None
        if args[:2] == ["audit", "--json"]:
            audits += 1
            boundary = "initial-audit" if audits == 1 else "final-audit"
            stdout = json.dumps(
                {"metadata": {"vulnerabilities": {"total": 0}}, "advisories": {}}
            )
        elif args[:2] == ["audit", "--fix=update"]:
            fixes += 1
            boundary = "initial-fix" if fixes == 1 else "followup-fix"
        elif args[0] == "view":
            boundary, stdout = "view", '"1.0.0"'
        elif "--lockfile-only" in args:
            boundary = "install"
        elif args == ["install", "--frozen-lockfile"]:
            boundary = "frozen"
        elif args == ["run", "build"]:
            boundary = "build"
        if boundary == operation and not mutated:
            policy = yaml.safe_load(workspace.read_text())
            policy[field] = value
            workspace.write_text(yaml.safe_dump(policy))
            (cwd / "package.json").write_text(
                json.dumps({"packageManager": "pnpm@11.21.0", "dependencies": {}})
            )
            lockfile = cwd / "pnpm-lock.yaml"
            lock = yaml.safe_load(lockfile.read_text())
            lock["packages"] = {"unrelated@9.0.0": {}}
            lockfile.write_text(yaml.safe_dump(lock))
            mutated = True
            return subprocess.CompletedProcess(command, exit_code, stdout, "")
        return subprocess.CompletedProcess(command, 0, stdout, "")

    monkeypatch.setattr(subprocess, "run", invoke)
    report = prepare(pnpm_project)

    assert mutated
    for name, content in files.items():
        assert (pnpm_project / name).read_bytes() == content
    assert "changed protected pnpm policy" in report


@pytest.mark.parametrize("phase", ["initial", "followup"])
@pytest.mark.parametrize(
    "addition, accepted, retained",
    [
        ("renderer@1.0.1", True, True),
        ("renderer@2.0.0", True, False),
        ("@scope/safe@2.0.0", True, False),
        ("unrelated@3.0.0", True, False),
        ("renderer@*", False, False),
        ("renderer@1.0.1 || 2.0.0", True, True),
        (None, False, False),
    ],
)
def test_security_exclusions_require_each_fix_complete_normalized_lock_delta(
    pnpm_project, monkeypatch, phase, addition, accepted, retained
):
    workspace = pnpm_project / "pnpm-workspace.yaml"
    lockfile = pnpm_project / "pnpm-lock.yaml"
    original_policy = yaml.safe_load(workspace.read_text())
    baseline_packages = {
        "renderer@1.0.0": {},
        "renderer@2.0.0": {},
        "@scope/safe@2.0.0(peer@1.0.0)": {},
    }
    if phase == "initial":
        lock = yaml.safe_load(lockfile.read_text())
        lock["packages"] = baseline_packages
        lockfile.write_text(yaml.safe_dump(lock))
    fixes = 0

    def invoke(command, *, cwd, **kwargs):
        nonlocal fixes
        args = command[5:]
        stdout = ""
        if args[:2] == ["audit", "--json"]:
            stdout = json.dumps(
                {"metadata": {"vulnerabilities": {"total": 0}}, "advisories": {}}
            )
        elif args[0] == "view":
            stdout = '"1.0.0"'
        elif "--lockfile-only" in args and phase == "followup":
            lock = yaml.safe_load(lockfile.read_text())
            lock["packages"] = baseline_packages
            lockfile.write_text(yaml.safe_dump(lock))
        elif args[:2] == ["audit", "--fix=update"]:
            fixes += 1
            if fixes == (1 if phase == "initial" else 2):
                lock = yaml.safe_load(lockfile.read_text())
                lock["packages"].pop("renderer@1.0.0")
                lock["packages"]["renderer@1.0.1"] = {}
                lock["packages"].pop("@scope/safe@2.0.0(peer@1.0.0)")
                lock["packages"]["@scope/safe@2.0.0(peer@2.0.0)"] = {}
                lockfile.write_text(yaml.safe_dump(lock))
                policy = yaml.safe_load(workspace.read_text())
                if addition is None:
                    policy["minimumReleaseAgeExclude"] = []
                else:
                    policy["minimumReleaseAgeExclude"].append(addition)
                workspace.write_text(yaml.safe_dump(policy))
        return subprocess.CompletedProcess(command, 0, stdout, "")

    monkeypatch.setattr(subprocess, "run", invoke)
    report = prepare(pnpm_project)
    policy = yaml.safe_load(workspace.read_text())
    if retained:
        original_policy["minimumReleaseAgeExclude"].append("renderer@1.0.1")
    assert policy == original_policy
    packages = yaml.safe_load(lockfile.read_text())["packages"]
    assert ("renderer@1.0.1" in packages) == accepted
    assert ("changed protected pnpm policy" in report) == (not accepted)


@pytest.mark.parametrize("security_fix", [False, True])
@pytest.mark.parametrize(
    "union, permitted",
    [
        ("renderer@1.0.0 || 1.0.1", True),
        ("renderer@1.0.1", False),
        ("renderer@1.0.0 || *", False),
        ("renderer@1.0.0 || 2.0.0", True),
        ("renderer@1.0.0 || ^1.0.1", False),
    ],
)
def test_pnpm_merged_exclusions_preserve_existing_exact_versions(
    pnpm_project, security_fix, union, permitted
):
    workspace = pnpm_project / "pnpm-workspace.yaml"
    lockfile = pnpm_project / "pnpm-lock.yaml"
    policy = yaml.safe_load(workspace.read_text())
    policy["minimumReleaseAgeExclude"].append("renderer@1.0.0")
    workspace.write_text(yaml.safe_dump(policy))
    original_policy = workspace.read_text().replace(
        "minimumReleaseAgeExclude:\n- other@3.0.0\n- renderer@1.0.0\n",
        "# Preserve the release-age policy.\n"
        "minimumReleaseAgeExclude: # Existing policy.\n"
        "- 'other@3.0.0' # Existing rationale.\n"
        "- 'renderer@1.0.0' # Baseline pin.\n",
    )
    workspace.write_text(original_policy)
    lock = yaml.safe_load(lockfile.read_text())
    lock["packages"]["renderer@2.0.0"] = {}
    lockfile.write_text(yaml.safe_dump(lock))
    snapshot = audit_module["valid_snapshot"](pnpm_project)
    policy["minimumReleaseAgeExclude"] = ["other@3.0.0", union]
    workspace.write_text(yaml.safe_dump(policy))
    lock["packages"].pop("renderer@1.0.0")
    lock["packages"]["renderer@1.0.1"] = {}
    lockfile.write_text(yaml.safe_dump(lock))
    notes = []

    restored = audit_module["restore_invalid_state"](
        pnpm_project, snapshot, notes, "Test command", security_fix=security_fix
    )

    accepted = permitted and security_fix
    assert restored == (not accepted)
    if accepted:
        expected_policy_text = original_policy
        if union == "renderer@1.0.0 || 1.0.1":
            expected_policy_text = original_policy.replace(
                "- 'renderer@1.0.0' # Baseline pin.\n",
                "- 'renderer@1.0.0' # Baseline pin.\n- renderer@1.0.1\n",
            )
        assert workspace.read_text() == expected_policy_text
        expected_policy = yaml.safe_load(expected_policy_text)
        baseline_policy = yaml.safe_load(snapshot[1]["pnpm-workspace.yaml"])
        expected_exclusions = ["other@3.0.0", "renderer@1.0.0"]
        if union == "renderer@1.0.0 || 1.0.1":
            expected_exclusions.append("renderer@1.0.1")
        assert expected_policy["minimumReleaseAgeExclude"] == expected_exclusions
        expected_policy.pop("minimumReleaseAgeExclude")
        baseline_policy.pop("minimumReleaseAgeExclude")
        assert expected_policy == baseline_policy
        assert yaml.safe_load(lockfile.read_text()) == lock
        assert bool(notes) == (union == "renderer@1.0.0 || 2.0.0")
    else:
        assert (pnpm_project / "package.json").read_bytes() == snapshot[0]
        for name, content in snapshot[1].items():
            assert (pnpm_project / name).read_bytes() == content
        assert "changed protected pnpm policy" in notes[0]


@pytest.mark.parametrize("fixture_name", ["npm_project", "pnpm_project"])
@pytest.mark.parametrize("exit_code", [0, 1])
@pytest.mark.parametrize(
    "operation", ["initial-audit", "view", "frozen", "build", "final-audit"]
)
@pytest.mark.parametrize("mutated_file", ["package.json", "lock"])
def test_nonmutating_commands_preserve_exact_package_files(
    request, monkeypatch, fixture_name, exit_code, operation, mutated_file
):
    project = request.getfixturevalue(fixture_name)
    pnpm = fixture_name == "pnpm_project"
    lock_name = "pnpm-lock.yaml" if pnpm else "package-lock.json"
    files = {
        name: (project / name).read_bytes()
        for name in (
            "package.json",
            lock_name,
            *(["pnpm-workspace.yaml"] if pnpm else []),
        )
    }
    audits = 0
    mutated = False

    def invoke(command, *, cwd, **kwargs):
        nonlocal audits, mutated
        args = command[5:] if pnpm else command[4:]
        stdout, boundary = "", None
        if args[:2] == ["audit", "--json"]:
            audits += 1
            boundary = "initial-audit" if audits == 1 else "final-audit"
            stdout = json.dumps(
                {
                    "metadata": {"vulnerabilities": {"total": 0}},
                    "advisories" if pnpm else "vulnerabilities": {},
                }
            )
        elif args[0] == "view":
            boundary, stdout = "view", '"1.0.0"'
        elif args[0] == "ci" or args == ["install", "--frozen-lockfile"]:
            boundary = "frozen"
        elif args == ["run", "build"]:
            boundary = "build"
        if boundary == operation and not mutated:
            if mutated_file == "package.json":
                manifest = json.loads((project / "package.json").read_bytes())
                manifest["dependencies"]["renderer"] = "9.9.9"
                (project / "package.json").write_text(json.dumps(manifest))
            elif pnpm:
                lock = yaml.safe_load((project / lock_name).read_bytes())
                lock["packages"] = {"renderer@9.9.9": {}}
                (project / lock_name).write_text(yaml.safe_dump(lock))
            else:
                (project / lock_name).write_text(
                    json.dumps(
                        {
                            "lockfileVersion": 3,
                            "packages": {"node_modules/renderer": {"version": "9.9.9"}},
                        }
                    )
                )
            mutated = True
            return subprocess.CompletedProcess(command, exit_code, stdout, "")
        return subprocess.CompletedProcess(command, 0, stdout, "")

    monkeypatch.setattr(subprocess, "run", invoke)
    report = prepare(project)

    assert mutated
    for name, content in files.items():
        assert (project / name).read_bytes() == content
    assert "restored" in report
    if operation in {"frozen", "build"}:
        assert "## Production build\n\nPassed." not in report
    if operation == "final-audit":
        assert "## Remaining advisories\n\nAudit unavailable" in report


@pytest.mark.parametrize("fixture_name", ["npm_project", "pnpm_project"])
@pytest.mark.parametrize("container", [None, [], {}])
def test_audit_missing_or_inconsistent_advisory_evidence_is_unavailable(
    request, monkeypatch, fixture_name, container
):
    project = request.getfixturevalue(fixture_name)
    key = "advisories" if fixture_name == "pnpm_project" else "vulnerabilities"
    response = {"metadata": {"vulnerabilities": {"high": 1}}}
    if container is not None:
        response[key] = container

    def invoke(command, *, cwd, **kwargs):
        return subprocess.CompletedProcess(command, 1, json.dumps(response), "")

    monkeypatch.setattr(subprocess, "run", invoke)
    data = audit(project)
    assert isinstance(data, str) and "Audit unavailable" in data
    for formatter in (format_remaining_audit, format_audit):
        assert "Audit unavailable" in formatter(data, {})
        assert "No known vulnerabilities" not in formatter(data, {})


@pytest.mark.parametrize("fixture_name", ["npm_project", "pnpm_project"])
@pytest.mark.parametrize(
    "counts",
    [None, {}, {"unexpected": 1}, {"total": -1}, {"total": True}, {"total": 1}],
)
def test_invalid_counts_cannot_be_reported_as_a_clean_audit(
    request, monkeypatch, fixture_name, counts
):
    project = request.getfixturevalue(fixture_name)
    response = {
        "metadata": {"vulnerabilities": counts},
        "advisories" if fixture_name == "pnpm_project" else "vulnerabilities": {},
    }
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, **kwargs: subprocess.CompletedProcess(
            command, 0, json.dumps(response), ""
        ),
    )
    result = audit(project)
    assert isinstance(result, str) and "Audit unavailable" in result
    assert "No known vulnerabilities" not in format_remaining_audit(result, {})


def test_pnpm_counts_require_advisory_evidence():
    assert not audit_module["counts_match_details"]({"total": 0}, {}, "pnpm")


def test_security_fix_preserves_preexisting_broad_exclusions(pnpm_project):
    workspace = pnpm_project / "pnpm-workspace.yaml"
    policy = yaml.safe_load(workspace.read_bytes())
    policy["minimumReleaseAgeExclude"].append("legacy")
    workspace.write_text(yaml.safe_dump(policy))
    snapshot = audit_module["valid_snapshot"](pnpm_project)
    lockfile = pnpm_project / "pnpm-lock.yaml"
    lock = yaml.safe_load(lockfile.read_bytes())
    lock["packages"]["renderer@1.0.1"] = {}
    lockfile.write_text(yaml.safe_dump(lock))
    policy["minimumReleaseAgeExclude"].append("renderer@1.0.1")
    workspace.write_text(yaml.safe_dump(policy))
    notes = []
    assert not audit_module["restore_invalid_state"](
        pnpm_project, snapshot, notes, "Security fix", security_fix=True
    )
    assert yaml.safe_load(workspace.read_bytes()) == policy
    assert not notes


@pytest.mark.parametrize("exclusions", ["renderer@1.0.1", [None]])
def test_snapshot_rejects_malformed_release_age_exclusions(pnpm_project, exclusions):
    workspace = pnpm_project / "pnpm-workspace.yaml"
    policy = yaml.safe_load(workspace.read_bytes())
    policy["minimumReleaseAgeExclude"] = exclusions
    workspace.write_text(yaml.safe_dump(policy))
    assert audit_module["valid_snapshot"](pnpm_project) is None
