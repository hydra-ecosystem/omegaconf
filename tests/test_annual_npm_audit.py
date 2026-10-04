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
    report = prepare(npm_project).read_text()
    manifest = json.loads((npm_project / "package.json").read_text())
    assert manifest["dependencies"]["renderer"] == "2.0.0"
    assert manifest["dependencies"]["local-plugin"] == "file:../plugin"
    assert manifest["overrides"] == {"transitive": "2.0.0"}
    assert manifest["peerDependencies"] == {"react": "^19.0.0"}
    assert "high: 1, total: 1" in report
    assert "npm fix candidate not available" in report
    assert "## Production build\n\nPassed." in report
    assert "does not certify" in report
    assert "--force" not in [arg for command in commands for arg in command]


def test_failed_resolution_restores_original_files(npm_project, monkeypatch):
    original = {
        name: (npm_project / name).read_bytes()
        for name in ("package.json", "package-lock.json")
    }
    commands = fake_npm(monkeypatch, resolution=1)
    report = prepare(npm_project).read_text()
    for name, content in original.items():
        assert (npm_project / name).read_bytes() == content
    assert "restored the original" in report
    assert "No direct dependency upgrades resolved" in report
    assert not any(command[:2] == ["audit", "fix"] for command in commands)


@pytest.mark.parametrize("install,build", [(1, 0), (0, 1)])
def test_failed_validation_still_produces_an_honest_report(
    npm_project, monkeypatch, install, build
):
    commands = fake_npm(monkeypatch, install=install, build=build)
    report = prepare(npm_project).read_text()
    assert "failed" in report.lower()
    assert "## Production build\n\nPassed." not in report
    if install:
        assert ["run", "build"] not in commands


def test_registry_failure_does_not_claim_an_upgrade(npm_project, monkeypatch):
    fake_npm(monkeypatch, lookup=1)
    report = prepare(npm_project).read_text()
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
    assert "requires breaking changes; manual review" in audit(npm_project)


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
    report = prepare(npm_project).read_text()
    manifest = json.loads((npm_project / "package.json").read_text())
    assert manifest["dependencies"]["renderer"] == "1.0.0"
    assert "Could not look up renderer" in report


@pytest.mark.parametrize("exit_code", [1, 2])
def test_failed_audit_fix_preserves_validation_and_reports_error(
    npm_project, monkeypatch, exit_code
):
    fake_npm(monkeypatch, audit_fix=exit_code)
    report = prepare(npm_project).read_text()
    assert f"Automatic audit fix returned exit {exit_code}" in report
    assert "## Production build\n\nPassed." in report


def test_shared_time_budget_stops_commands_and_writes_partial_report(
    npm_project, monkeypatch
):
    commands = fake_npm(monkeypatch)
    clock = iter([0, 0, 2700])
    monkeypatch.setattr(audit_module["time"], "monotonic", lambda: next(clock, 2700))
    report = prepare(npm_project).read_text()
    assert commands == [["audit", "--json", "--audit"]]
    assert "Could not look up renderer" in report
    assert "Not run: npm ci failed (exit 124)." in report
    assert "After: Audit unavailable (exit 124)." in report
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
    monkeypatch.setattr(sys, "argv", ["annual-npm-audit", "--directory", directory])
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2
    assert "relative npm project path" in capsys.readouterr().err


@pytest.mark.parametrize("missing", ["package.json", "package-lock.json"])
def test_cli_requires_manifest_and_lockfile(npm_project, monkeypatch, capsys, missing):
    (npm_project / missing).unlink()
    monkeypatch.chdir(npm_project)
    monkeypatch.setattr(sys, "argv", ["annual-npm-audit", "--directory", "."])
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2
    assert "must contain package.json and package-lock.json" in capsys.readouterr().err


def test_cli_entrypoint_prepares_selected_project(npm_project, monkeypatch):
    fake_npm(monkeypatch)
    monkeypatch.chdir(npm_project)
    monkeypatch.setattr(sys, "argv", ["annual-npm-audit", "--directory", "."])
    runpy.run_path(audit_module["__file__"], run_name="__main__")
    assert (npm_project / "DEPENDENCY-AUDIT.md").is_file()
    manifest = json.loads((npm_project / "package.json").read_text())
    assert manifest["dependencies"]["renderer"] == "2.0.0"
