import json
import runpy
import subprocess
from pathlib import Path

import pytest
import yaml

audit_module = runpy.run_path(
    str(Path(__file__).parents[1] / ".github/scripts/annual_npm_audit.py")
)
format_remaining_audit = audit_module["format_remaining_audit"]
prepare = audit_module["prepare"]
audit = audit_module["audit"]


@pytest.fixture
def npm_project(tmp_path):
    (tmp_path / "package.json").write_text(
        json.dumps({"dependencies": {"renderer": "1.0.0"}})
    )
    (tmp_path / "package-lock.json").write_text('{"lockfileVersion": 3}')
    return tmp_path


def test_remaining_summary_deduplicates_propagated_advisories():
    advisory = {
        "title": "Nested pattern exhaustion",
        "url": "https://github.com/advisories/GHSA-example",
        "severity": "high",
        "range": "<=3.0.3",
    }
    data = {
        "metadata": {"vulnerabilities": {"high": 3, "total": 3}},
        "vulnerabilities": {
            "braces": {
                "nodes": ["node_modules/braces"],
                "via": [advisory, advisory],
            },
            "micromatch": {"via": ["braces"]},
            "docusaurus": {"via": ["micromatch"]},
        },
    }
    lock = {"packages": {"node_modules/braces": {"version": "3.0.3"}}}

    report = format_remaining_audit(data, lock)

    assert report.count("https://github.com/advisories/GHSA-example") == 1
    assert "braces@3.0.3" in report
    assert "high: 3, total: 3" in report
    assert "not distinct advisory counts" in report
    assert "docusaurus" not in report


def test_remaining_summary_prioritizes_severity():
    data = {
        "metadata": {"vulnerabilities": {"low": 1, "critical": 1, "total": 2}},
        "vulnerabilities": {
            name: {
                "via": [
                    {
                        "title": name,
                        "url": f"https://github.com/advisories/{name}",
                        "severity": severity,
                        "range": "*",
                    }
                ]
            }
            for name, severity in (("low-issue", "low"), ("urgent", "critical"))
        },
    }

    report = format_remaining_audit(data, {})

    assert report.index("[urgent]") < report.index("[low-issue]")


@pytest.mark.parametrize("phase", ["frozen", "build", "final-audit"])
@pytest.mark.parametrize(
    ("project_name", "filename"),
    [
        ("npm_project", "package.json"),
        ("npm_project", "package-lock.json"),
        ("pnpm_project", "package.json"),
        ("pnpm_project", "pnpm-lock.yaml"),
        ("pnpm_project", "pnpm-workspace.yaml"),
    ],
)
def test_validation_restores_valid_mutations(
    request, monkeypatch, project_name, filename, phase
):
    project = request.getfixturevalue(project_name)
    package_manager = "pnpm" if project_name == "pnpm_project" else "npm"
    package_files = [
        "package.json",
        "pnpm-lock.yaml" if package_manager == "pnpm" else "package-lock.json",
    ]
    if package_manager == "pnpm":
        package_files.append("pnpm-workspace.yaml")
    proposal = {}
    audit_calls = 0

    def mutate():
        proposal.update({name: (project / name).read_bytes() for name in package_files})
        path = project / filename
        if path.suffix == ".json":
            content = json.loads(path.read_bytes())
            content["validationMutation"] = phase
            path.write_text(json.dumps(content))
        else:
            content = yaml.safe_load(path.read_bytes())
            content["validationMutation"] = phase
            path.write_text(yaml.safe_dump(content))

    def invoke(command, *, cwd, **kwargs):
        nonlocal audit_calls
        args = command[5:] if package_manager == "pnpm" else command[4:]
        stdout, code = "", 0
        if args[0] == "view":
            stdout = '"2.0.0"'
        elif args[:2] == ["audit", "--json"]:
            audit_calls += 1
            stdout = json.dumps(
                {"metadata": {"vulnerabilities": {"total": 0}}, "vulnerabilities": {}}
            )
            if phase == "final-audit" and audit_calls == 2:
                mutate()
        elif args[:2] in (["audit", "fix"], ["audit", "--fix=update"]):
            pass
        elif args == (
            ["install", "--frozen-lockfile"]
            if package_manager == "pnpm"
            else ["ci", "--no-audit"]
        ):
            if phase == "frozen":
                mutate()
        elif args == ["run", "build"]:
            if phase == "build":
                mutate()
        return subprocess.CompletedProcess(command, code, stdout, "")

    monkeypatch.setattr(subprocess, "run", invoke)

    report = prepare(project)

    assert proposal
    assert all(
        (project / name).read_bytes() == content for name, content in proposal.items()
    )
    assert "changed the package manifest, lockfile, or workspace policy" in report
    if phase == "final-audit":
        assert f"Audit unavailable: {package_manager} changed package files" in report
    else:
        assert "validation failed" in report
        assert "Passed." not in report


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
                "blockExoticSubdeps": True,
                "strictDepBuilds": True,
                "allowBuilds": {"core-js": False},
                "overrides": {"other": "3.0.0"},
            }
        )
    )
    return tmp_path


@pytest.mark.parametrize("failure", [None, "stable", "policy", "frozen"])
def test_pnpm_security_first_and_policy_restoration(pnpm_project, monkeypatch, failure):
    commands = []
    fixes = 0
    workspace = pnpm_project / "pnpm-workspace.yaml"
    lockfile = pnpm_project / "pnpm-lock.yaml"

    def invoke(command, *, cwd, **kwargs):
        nonlocal fixes
        assert command[3:5] == ["corepack", "pnpm"]
        args = command[5:]
        commands.append(args)
        stdout, code = "", 0
        if args[:2] == ["audit", "--json"]:
            stdout = json.dumps(
                {
                    "metadata": {"vulnerabilities": {"high": 1}},
                    "advisories": {
                        "123": {
                            "module_name": "renderer",
                            "severity": "high",
                            "title": "Render bug",
                            "url": "https://github.com/advisories/GHSA-render",
                            "vulnerable_versions": "<1.0.1",
                            "patched_versions": ">=1.0.1",
                            "findings": [
                                {"version": "1.0.0" if fixes == 0 else "1.0.1"}
                            ],
                        }
                    },
                }
            )
        elif args[:2] == ["audit", "--fix=update"]:
            fixes += 1
            policy = yaml.safe_load(workspace.read_text())
            policy["minimumReleaseAgeExclude"] = ["renderer@1.0.1"]
            workspace.write_text(yaml.safe_dump(policy))
            locked = yaml.safe_load(lockfile.read_text())
            locked["packages"] = {"renderer@1.0.1": {}}
            lockfile.write_text(yaml.safe_dump(locked))
            if failure == "policy" and fixes == 1:
                workspace.write_text("[")
                code = 124
        elif args[0] == "view":
            stdout = '"2.0.0"'
        elif args[0] == "install" and "--lockfile-only" in args:
            if failure == "stable":
                workspace.write_text("[")
                lockfile.unlink()
                code = 1
        elif args == ["install", "--frozen-lockfile"] and failure == "frozen":
            (cwd / "package.json").write_text("{")
        return subprocess.CompletedProcess(command, code, stdout, "")

    monkeypatch.setattr(subprocess, "run", invoke)
    report = prepare(pnpm_project)
    policy = yaml.safe_load(workspace.read_text())
    assert policy["minimumReleaseAge"] == 14400
    assert policy["blockExoticSubdeps"] and policy["strictDepBuilds"]
    assert policy["allowBuilds"] == {"core-js": False}
    assert policy["overrides"] == {"other": "3.0.0"}
    assert commands.index(["audit", "--fix=update", "--ignore-scripts"]) < next(
        i for i, args in enumerate(commands) if args[0] == "view"
    )
    assert "--force" not in str(commands)
    assert "pnpm" in report and "Render bug" in report
    assert "Registry advisory counts" in report
    assert "Full before/after pnpm audit" in report
    if failure == "stable":
        assert policy["minimumReleaseAgeExclude"] == ["renderer@1.0.1"]
        assert "renderer: `^1.0.0` → `2.0.0`" not in report
        assert "renderer: `1.0.0` → `1.0.1`" in report
    if failure == "policy":
        assert "restored" in report and "exit 124" in report
    if failure == "frozen":
        assert "Not run: pnpm frozen install failed" in report
        assert ["run", "build"] not in commands
    else:
        assert ["run", "build"] in commands
        assert ["run", "test:security-patches"] not in commands


def test_pnpm_shared_workspace_is_rejected(pnpm_project):
    (pnpm_project / "pnpm-workspace.yaml").write_text("packages: ['.', '../other']\n")
    with pytest.raises(ValueError, match="one deployment"):
        prepare(pnpm_project)


@pytest.mark.parametrize(
    ("project_name", "other_lock"),
    [("npm_project", "pnpm-lock.yaml"), ("pnpm_project", "package-lock.json")],
)
def test_snapshot_rejects_mixed_package_managers(request, project_name, other_lock):
    project = request.getfixturevalue(project_name)
    (project / other_lock).write_text("{}")
    assert audit_module["valid_snapshot"](project) is None


@pytest.mark.parametrize("rule", ["audit", "auditConfig"])
def test_pnpm_audit_refuses_advisory_ignore_rules(pnpm_project, monkeypatch, rule):
    workspace = pnpm_project / "pnpm-workspace.yaml"
    policy = yaml.safe_load(workspace.read_text())
    policy[rule] = (
        {"ignore": [123]} if rule == "audit" else {"ignoreGhsas": ["GHSA-example"]}
    )
    workspace.write_text(yaml.safe_dump(policy))
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: pytest.fail("audit must not run with hidden findings"),
    )
    assert "advisory-ignore rules would hide annual findings" in audit(pnpm_project)


@pytest.mark.parametrize(
    "advisory",
    [
        {},
        {
            "module_name": "renderer",
            "severity": "high",
            "title": "Example",
            "url": "https://github.com/advisories/GHSA-example",
            "vulnerable_versions": "<1.0.1",
            "findings": [{"version": None}],
        },
    ],
)
def test_pnpm_audit_rejects_malformed_advisories(pnpm_project, monkeypatch, advisory):
    response = json.dumps({"advisories": {"123": advisory}})
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, 1, response, ""),
    )
    assert audit(pnpm_project) == "Audit unavailable: malformed pnpm advisory response."


@pytest.mark.parametrize("reverse", [False, True])
def test_pnpm_groups_highest_severity_and_all_ranges(
    pnpm_project, monkeypatch, reverse
):
    advisories = [
        ("renderer", "low", "<1.0.1"),
        ("renderer", "critical", ">=2.0.0 <2.0.1"),
        ("other", "high", "<3.0.1"),
        ("renderer", "moderate", "<1.0.1"),
    ]
    if reverse:
        advisories.reverse()
    response = {
        "metadata": {
            "vulnerabilities": {"low": 1, "moderate": 1, "high": 1, "critical": 1}
        },
        "advisories": {
            str(index): {
                "module_name": name,
                "severity": severity,
                "title": f"{name} {severity}",
                "url": f"https://github.com/advisories/GHSA-example-{index}",
                "vulnerable_versions": affected,
                "patched_versions": "<0.0.0",
                "findings": [{"version": "1.0.0"}],
            }
            for index, (name, severity, affected) in enumerate(advisories)
        },
    }
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, **kwargs: subprocess.CompletedProcess(
            command, 1, json.dumps(response), ""
        ),
    )
    result = audit(pnpm_project)
    assert result["vulnerabilities"]["renderer"]["severity"] == "critical"
    assert result["vulnerabilities"]["renderer"]["range"] == "<1.0.1 || >=2.0.0 <2.0.1"
    assert len(result["vulnerabilities"]["renderer"]["via"]) == 3
    report = audit_module["format_audit"](result, {})
    assert report.index("**renderer**: critical") < report.index("**other**: high")
    assert "affected range `<1.0.1 || >=2.0.0 <2.0.1`" in report


def test_workspace_classifies_platform_specific_build_scripts():
    root = Path(__file__).parents[1]
    policy = yaml.safe_load((root / "website/pnpm-workspace.yaml").read_text())
    assert policy["strictDepBuilds"] is True
    assert policy["allowBuilds"]["fsevents"] is False


def test_workflow_limits_credentials_artifacts_and_publication():
    root = Path(__file__).parents[1]
    text = (root / ".github/workflows/annual-npm-audit.yml").read_text()
    workflow = yaml.safe_load(text)
    assert workflow["permissions"] == {"contents": "read"}
    audit = workflow["jobs"]["audit"]
    assert "permissions" not in audit
    assert audit["steps"][0]["with"]["persist-credentials"] is False
    publisher = workflow["jobs"]["pull-request"]
    assert publisher["permissions"] == {"contents": "write", "pull-requests": "write"}
    assert (
        publisher["steps"][0]["with"]["ref"]
        == "${{ github.event.repository.default_branch }}"
    )
    files = next(
        step["with"]["path"]
        for step in audit["steps"]
        if step.get("with", {}).get("name") == "annual-npm-dependencies"
    ).splitlines()
    assert files == [
        "${{ env.NPM_PROJECT }}/package.json",
        "${{ env.NPM_PROJECT }}/pnpm-lock.yaml",
        "${{ env.NPM_PROJECT }}/pnpm-workspace.yaml",
    ]
    shell = publisher["steps"][-1]["run"]
    assert "--body-file" in shell and "--force-with-lease=" in shell
    assert "--draft" not in shell
    assert "git add ." not in shell
    deploy = yaml.safe_load((root / ".github/workflows/deploy-docs.yml").read_text())
    # PyYAML's YAML 1.1 loader reads the GitHub 'on' key as True.
    for event in ("push", "pull_request"):
        paths = deploy[True][event]["paths"]
        assert ".github/scripts/annual_npm_audit.py" in paths
        assert ".github/workflows/annual-npm-audit.yml" in paths
