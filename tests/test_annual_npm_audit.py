import json
import runpy
import subprocess
import sys
import time
from pathlib import Path

import pytest

audit_module = runpy.run_path(
    str(Path(__file__).parents[1] / ".github/scripts/annual_npm_audit.py")
)
prepare = audit_module["prepare"]
audit = audit_module["audit"]
format_audit = audit_module["format_audit"]
run = audit_module["run"]
main = audit_module["main"]


@pytest.fixture
def npm_project(tmp_path):
    manifest = {
        "dependencies": {"renderer": "1.0.0", "local-plugin": "file:../plugin"},
        "overrides": {"transitive": "2.0.0"},
        "peerDependencies": {"react": "^19.0.0"},
    }
    (tmp_path / "package.json").write_text(json.dumps(manifest) + "\n")
    (tmp_path / "package-lock.json").write_text('{"lockfileVersion": 3}\n')
    return tmp_path


def fake_npm(
    monkeypatch,
    *,
    resolution=0,
    install=0,
    build=0,
    lookup=0,
    lookup_output='"2.0.0"',
    audit_error=False,
    audit_fix=0,
):
    commands = []

    def invoke(command, *, cwd, **kwargs):
        args = command[4:]
        commands.append(args)
        stdout = ""
        code = 0
        if args[0] == "view":
            stdout = lookup_output
            code = lookup
        elif args[0] == "install":
            (cwd / "package-lock.json").write_text('{"candidate": true}\n')
            code = resolution
        elif args[0] == "ci":
            code = install
        elif args[:2] == ["run", "build"]:
            code = build
        elif args[:2] == ["audit", "fix"]:
            code = audit_fix
        elif args[:2] == ["audit", "--json"]:
            code = 1
            stdout = json.dumps(
                {"error": {"code": "ENETUNREACH"}}
                if audit_error
                else {
                    "metadata": {"vulnerabilities": {"high": 1, "total": 1}},
                    "vulnerabilities": {
                        "transitive": {
                            "severity": "high",
                            "range": "<=2.0.0",
                            "fixAvailable": False,
                        }
                    },
                }
            )
        return subprocess.CompletedProcess(command, code, stdout, "")

    monkeypatch.setattr(subprocess, "run", invoke)
    return commands


def test_upgrade_keeps_manual_constraints_and_reports_unfixed_findings(
    npm_project, monkeypatch
):
    commands = fake_npm(monkeypatch)
    report = prepare(npm_project)
    manifest = json.loads((npm_project / "package.json").read_text())
    assert manifest["dependencies"]["renderer"] == "2.0.0"
    assert manifest["dependencies"]["local-plugin"] == "file:../plugin"
    assert manifest["overrides"] == {"transitive": "2.0.0"}
    assert manifest["peerDependencies"] == {"react": "^19.0.0"}
    assert "high: 1, total: 1" in report
    assert "npm fix candidate not offered by npm" in report
    assert "## Production build\n\nPassed." in report
    assert "does not certify" in report
    assert "--force" not in [arg for command in commands for arg in command]


def test_failed_resolution_restores_original_files(npm_project, monkeypatch):
    original = {
        name: (npm_project / name).read_bytes()
        for name in ("package.json", "package-lock.json")
    }
    commands = fake_npm(monkeypatch, resolution=1)
    report = prepare(npm_project)
    for name, content in original.items():
        assert (npm_project / name).read_bytes() == content
    assert "from the initial security fix attempt" in report
    assert "No other direct dependency upgrades resolved" in report
    assert sum(command[:2] == ["audit", "fix"] for command in commands) == 1


def test_security_fixes_run_first_and_survive_failed_stable_upgrade(
    npm_project, monkeypatch
):
    commands = fake_npm(monkeypatch, resolution=1)
    invoke = subprocess.run
    security_lock = '{"packages": {"node_modules/transitive": {"version": "2.1.0"}}}\n'

    def fix(command, **kwargs):
        result = invoke(command, **kwargs)
        if command[4:6] == ["audit", "fix"]:
            (npm_project / "package-lock.json").write_text(security_lock)
        return result

    monkeypatch.setattr(subprocess, "run", fix)
    report = prepare(npm_project)
    assert commands[1][:2] == ["audit", "fix"]
    assert (npm_project / "package-lock.json").read_text() == security_lock
    assert (
        json.loads((npm_project / "package.json").read_text())["dependencies"][
            "renderer"
        ]
        == "1.0.0"
    )
    assert "Stable upgrade resolution failed" in report


def test_audit_reports_advisory_links_versions_and_severity_order():
    data = {
        "metadata": {"vulnerabilities": {"critical": 1, "high": 1}},
        "vulnerabilities": {
            "parent": {
                "severity": "high",
                "range": "<=3.0.0",
                "fixAvailable": False,
                "nodes": ["node_modules/parent"],
                "via": ["transitive"],
            },
            "transitive": {
                "severity": "critical",
                "range": "<2.1.0",
                "fixAvailable": True,
                "nodes": [
                    "node_modules/transitive",
                    "node_modules/parent/node_modules/transitive",
                ],
                "via": [
                    {
                        "title": "Example advisory",
                        "url": "https://github.com/advisories/GHSA-example",
                        "severity": "critical",
                        "range": "<2.1.0",
                    }
                ],
            },
        },
    }
    lock = {
        "packages": {
            "node_modules/parent": {"version": "3.0.0"},
            "node_modules/transitive": {"version": "2.0.0"},
            "node_modules/parent/node_modules/transitive": {"version": "1.0.0"},
        }
    }
    report = format_audit(data, lock)
    assert report.index("**transitive**") < report.index("**parent**")
    assert "locked versions `1.0.0, 2.0.0`" in report
    assert "[Example advisory](https://github.com/advisories/GHSA-example)" in report
    assert "Depends on affected `transitive`" in report


@pytest.mark.parametrize("after_audit_error", [False, True])
def test_report_distinguishes_security_changes_from_other_stable_upgrades(
    npm_project, monkeypatch, after_audit_error
):
    lock = {"packages": {"node_modules/transitive": {"version": "2.0.0"}}}
    (npm_project / "package-lock.json").write_text(json.dumps(lock))
    fake_npm(monkeypatch)
    invoke = subprocess.run
    audits = 0

    def fix(command, **kwargs):
        nonlocal audits
        result = invoke(command, **kwargs)
        if command[4] == "install" or command[4:6] == ["audit", "fix"]:
            lock["packages"]["node_modules/transitive"]["version"] = "2.1.0"
            (npm_project / "package-lock.json").write_text(json.dumps(lock))
        if command[4:6] == ["audit", "--json"]:
            audits += 1
            data = json.loads(result.stdout)
            if audits == 1:
                data["vulnerabilities"]["transitive"]["nodes"] = [
                    "node_modules/transitive"
                ]
            else:
                data = (
                    {"error": {"code": "ENETUNREACH"}}
                    if after_audit_error
                    else {
                        "metadata": {"vulnerabilities": {"total": 0}},
                        "vulnerabilities": {},
                    }
                )
            result.stdout = json.dumps(data)
        return result

    monkeypatch.setattr(subprocess, "run", fix)
    report = prepare(npm_project)
    security, stable = report.split("## Other stable dependency upgrades")
    assert "transitive: `2.0.0` → `2.1.0`" in security
    assert "renderer: `1.0.0` → `2.0.0`" in stable
    assert "renderer: `1.0.0` → `2.0.0`" not in security
    if after_audit_error:
        assert "fix unconfirmed" in security
        assert "no longer reported by npm" not in security
    else:
        assert "no longer reported by npm" in security
        assert "No known vulnerabilities reported by npm" in report
    assert not (npm_project / "DEPENDENCY-AUDIT.md").exists()


@pytest.mark.parametrize("still_affected", [False, True])
def test_security_report_tracks_hoisted_dependency_versions(
    npm_project, monkeypatch, still_affected
):
    old_node = "node_modules/parent/node_modules/transitive"
    new_node = "node_modules/transitive"
    (npm_project / "package-lock.json").write_text(
        json.dumps({"packages": {old_node: {"version": "2.0.0"}}})
    )
    fake_npm(monkeypatch)
    invoke = subprocess.run
    audits = 0

    def hoist(command, **kwargs):
        nonlocal audits
        result = invoke(command, **kwargs)
        if command[4] == "install" or command[4:6] == ["audit", "fix"]:
            (npm_project / "package-lock.json").write_text(
                json.dumps({"packages": {new_node: {"version": "2.1.0"}}})
            )
        if command[4:6] == ["audit", "--json"]:
            audits += 1
            data = json.loads(result.stdout)
            if audits == 1 or still_affected:
                data["vulnerabilities"]["transitive"]["nodes"] = [
                    old_node if audits == 1 else new_node
                ]
            else:
                data = {
                    "metadata": {"vulnerabilities": {"total": 0}},
                    "vulnerabilities": {},
                }
            result.stdout = json.dumps(data)
        return result

    monkeypatch.setattr(subprocess, "run", hoist)
    report = prepare(npm_project)
    changes = report.split("### Before")[0]
    status = "still reported by npm" if still_affected else "no longer reported by npm"
    assert f"transitive: `2.0.0` → `2.1.0`; {status}." in changes
    assert "not recorded in lockfile" not in changes


def test_security_report_lists_affected_direct_upgrade_once(npm_project, monkeypatch):
    node = "node_modules/renderer"
    (npm_project / "package-lock.json").write_text(
        json.dumps({"packages": {node: {"version": "1.0.0"}}})
    )
    fake_npm(monkeypatch)
    invoke = subprocess.run

    def upgrade(command, **kwargs):
        result = invoke(command, **kwargs)
        if command[4] == "install":
            (npm_project / "package-lock.json").write_text(
                json.dumps({"packages": {node: {"version": "2.0.0"}}})
            )
        if command[4:6] == ["audit", "--json"]:
            data = json.loads(result.stdout)
            vulnerability = data["vulnerabilities"].pop("transitive")
            vulnerability["nodes"] = [node]
            data["vulnerabilities"]["renderer"] = vulnerability
            result.stdout = json.dumps(data)
        return result

    monkeypatch.setattr(subprocess, "run", upgrade)
    report = prepare(npm_project)
    changes = report.split("### Before")[0]
    assert changes.count("- renderer:") == 1
    assert "renderer: `1.0.0` → `2.0.0`; still reported by npm." in changes


@pytest.mark.parametrize("install,build", [(1, 0), (0, 1)])
def test_failed_validation_still_produces_an_honest_report(
    npm_project, monkeypatch, install, build
):
    commands = fake_npm(monkeypatch, install=install, build=build)
    report = prepare(npm_project)
    assert "failed" in report.lower()
    assert "## Production build\n\nPassed." not in report
    if install:
        assert ["run", "build"] not in commands


def test_registry_failure_does_not_claim_an_upgrade(npm_project, monkeypatch):
    fake_npm(monkeypatch, lookup=1)
    report = prepare(npm_project)
    manifest = json.loads((npm_project / "package.json").read_text())
    assert manifest["dependencies"]["renderer"] == "1.0.0"
    assert "Could not look up renderer" in report


def test_audit_error_is_not_reported_as_zero_vulnerabilities(npm_project, monkeypatch):
    fake_npm(monkeypatch, audit_error=True)
    assert audit(npm_project) == "Audit unavailable (exit 1)."


def test_breaking_fix_candidate_is_flagged_for_manual_review(npm_project, monkeypatch):
    data = {
        "metadata": {"vulnerabilities": {"high": 1}},
        "vulnerabilities": {
            "renderer": {
                "severity": "high",
                "range": "<=1.0.0",
                "fixAvailable": {"name": "renderer", "isSemVerMajor": True},
            }
        },
    }

    def invoke(command, **kwargs):
        return subprocess.CompletedProcess(command, 1, json.dumps(data), "")

    monkeypatch.setattr(subprocess, "run", invoke)
    assert "requires breaking changes; manual review" in format_audit(
        audit(npm_project), {}
    )


@pytest.mark.parametrize("exit_code", [-9, 137])
def test_command_timeout_is_recorded_for_best_effort_reporting(
    npm_project, monkeypatch, exit_code
):
    def timeout(command, **kwargs):
        return subprocess.CompletedProcess(command, exit_code, "partial output", "")

    monkeypatch.setattr(subprocess, "run", timeout)
    result = run(npm_project, "view", "renderer@latest", "version", "--json")
    assert result.returncode == 124
    assert result.stdout == "partial output"
    assert "timed out" in result.stderr


def test_malformed_audit_response_is_unavailable(npm_project, monkeypatch):
    def invoke(command, **kwargs):
        return subprocess.CompletedProcess(command, 1, "not JSON", "")

    monkeypatch.setattr(subprocess, "run", invoke)
    assert audit(npm_project) == "Audit unavailable (exit 1)."


def test_malformed_registry_response_retains_dependency(npm_project, monkeypatch):
    fake_npm(monkeypatch, lookup_output="not JSON")
    report = prepare(npm_project)
    manifest = json.loads((npm_project / "package.json").read_text())
    assert manifest["dependencies"]["renderer"] == "1.0.0"
    assert "Could not look up renderer" in report


@pytest.mark.parametrize("exit_code", [1, 2])
def test_failed_audit_fix_preserves_validation_and_reports_error(
    npm_project, monkeypatch, exit_code
):
    fake_npm(monkeypatch, audit_fix=exit_code)
    report = prepare(npm_project)
    assert f"Automatic audit fix returned exit {exit_code}" in report
    assert "## Production build\n\nPassed." in report


def test_shared_time_budget_stops_commands_and_writes_partial_report(
    npm_project, monkeypatch
):
    commands = fake_npm(monkeypatch)
    clock = iter([0, 0, 2700])
    monkeypatch.setattr(audit_module["time"], "monotonic", lambda: next(clock, 2700))
    report = prepare(npm_project)
    assert commands == [["audit", "--json", "--audit", "--package-lock-only"]]
    assert "Could not look up renderer" in report
    assert "Not run: npm frozen install failed (exit 124)" in report
    assert "### After\n\nAudit unavailable (exit 124)." in report
    assert "time budget was exhausted" in report


def test_command_timeout_respects_remaining_shared_budget(npm_project, monkeypatch):
    observed = []

    def invoke(command, **kwargs):
        observed.append(command[:4])
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(subprocess, "run", invoke)
    monkeypatch.setattr(audit_module["time"], "monotonic", lambda: 100)
    run(npm_project, "ci", deadline=130)
    assert observed == [["timeout", "--signal=KILL", "30s", "npm"]]


def test_timeout_terminates_child_before_it_can_modify_files(npm_project, monkeypatch):
    marker = npm_project / "child-survived"
    actual_run = subprocess.run

    def invoke(command, **kwargs):
        return actual_run(
            [
                *command[:3],
                "sh",
                "-c",
                '(sleep 1; touch "$1") & wait',
                "sh",
                str(marker),
            ],
            **kwargs,
        )

    monkeypatch.setattr(subprocess, "run", invoke)
    result = run(npm_project, "run", "build", deadline=time.monotonic() + 0.2)
    assert result.returncode == 124
    assert not marker.exists()


@pytest.mark.parametrize("directory", ["/tmp", "../website", "website;command"])
def test_cli_rejects_unsafe_project_paths(monkeypatch, capsys, directory):
    monkeypatch.setattr(
        sys,
        "argv",
        ["annual-npm-audit", "--directory", directory, "--report", "/tmp/report"],
    )
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2
    assert "relative npm project path" in capsys.readouterr().err


@pytest.mark.parametrize("missing", ["package.json", "package-lock.json"])
def test_cli_requires_manifest_and_lockfile(npm_project, monkeypatch, capsys, missing):
    (npm_project / missing).unlink()
    monkeypatch.chdir(npm_project)
    monkeypatch.setattr(
        sys, "argv", ["annual-npm-audit", "--directory", ".", "--report", "/tmp/report"]
    )
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2
    assert (
        "valid package files for one npm or pnpm deployment" in capsys.readouterr().err
    )


def test_cli_entrypoint_prepares_selected_project(npm_project, monkeypatch):
    fake_npm(monkeypatch)
    monkeypatch.chdir(npm_project)
    report = npm_project.parent / f"{npm_project.name}-pr-body.md"
    monkeypatch.setattr(
        sys,
        "argv",
        ["annual-npm-audit", "--directory", ".", "--report", str(report)],
    )
    runpy.run_path(audit_module["__file__"], run_name="__main__")
    assert "Security findings and fixes" in report.read_text()
    assert not (npm_project / "DEPENDENCY-AUDIT.md").exists()
    manifest = json.loads((npm_project / "package.json").read_text())
    assert manifest["dependencies"]["renderer"] == "2.0.0"


@pytest.mark.parametrize("manifest", [None, "{", "[]"])
def test_manager_recovers_from_unreadable_or_invalid_manifest(tmp_path, manifest):
    if manifest is not None:
        (tmp_path / "package.json").write_text(manifest)
    assert audit_module["manager"](tmp_path) == "npm"


@pytest.mark.parametrize("filename", ["package.json", "package-lock.json"])
def test_snapshot_rejects_non_object_package_files(npm_project, filename):
    (npm_project / filename).write_text("[]")
    assert audit_module["valid_snapshot"](npm_project) is None


def test_audit_rejects_non_object_registry_response(npm_project, monkeypatch):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, 1, "[]", ""),
    )
    assert audit(npm_project) == "Audit unavailable (exit 1)."


@pytest.mark.parametrize("phase", ["initial-audit", "lookup", "stable-install"])
def test_prepare_restores_files_damaged_before_validation(
    npm_project, monkeypatch, phase
):
    fake_npm(monkeypatch)
    invoke = subprocess.run
    damaged = False

    def damage(command, **kwargs):
        nonlocal damaged
        result = invoke(command, **kwargs)
        args = command[4:]
        selected = (
            (phase == "initial-audit" and args[:2] == ["audit", "--json"])
            or (phase == "lookup" and args[0] == "view")
            or (phase == "stable-install" and args[0] == "install")
        )
        if selected and not damaged:
            (npm_project / "package-lock.json").unlink()
            damaged = True
        return result

    monkeypatch.setattr(subprocess, "run", damage)
    report = prepare(npm_project)
    assert damaged
    assert audit_module["valid_snapshot"](npm_project) is not None
    manifest = json.loads((npm_project / "package.json").read_text())
    assert manifest["overrides"] == {"transitive": "2.0.0"}
    if phase == "initial-audit":
        assert "Audit unavailable: npm left invalid package files" in report
    else:
        assert manifest["dependencies"]["renderer"] == "1.0.0"
        assert "renderer: `1.0.0` → `2.0.0`" not in report
        assert "restored" in report
