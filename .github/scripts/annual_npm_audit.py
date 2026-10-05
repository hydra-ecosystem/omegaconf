"""Prepare a best-effort npm upgrade and report for one documentation project."""

import argparse
import json
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path


def run(
    directory: Path, *args: str, deadline: float | None = None
) -> subprocess.CompletedProcess[str]:
    command = ["npm", *args]
    timeout = min(900, deadline - time.monotonic()) if deadline is not None else 900
    if timeout <= 0:
        return subprocess.CompletedProcess(
            command, 124, "", "Annual audit time budget exhausted."
        )
    # GNU timeout owns the process group and kills npm and lifecycle/build children.
    result = subprocess.run(
        ["timeout", "--signal=KILL", f"{timeout}s", *command],
        cwd=directory,
        capture_output=True,
        text=True,
    )
    if result.returncode in (-9, 137):
        result = subprocess.CompletedProcess(
            command, 124, result.stdout, result.stderr + "\nCommand timed out."
        )
    print(f"npm {' '.join(args)}: exit {result.returncode}")
    if result.returncode:
        print(result.stdout)
        print(result.stderr)
    return result


def audit(directory: Path, *, deadline: float | None = None) -> dict | str:
    result = run(
        directory,
        "audit",
        "--json",
        "--audit",
        "--package-lock-only",
        deadline=deadline,
    )
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return f"Audit unavailable (exit {result.returncode})."
    counts = data.get("metadata", {}).get("vulnerabilities")
    if result.returncode not in (0, 1) or data.get("error") or counts is None:
        return f"Audit unavailable (exit {result.returncode})."
    return data


def versions(lock: dict, vulnerability: dict) -> str:
    packages = lock.get("packages", {})
    found = {
        packages[node]["version"]
        for node in vulnerability.get("nodes", [])
        if node in packages and "version" in packages[node]
    }
    return ", ".join(sorted(found)) or "not recorded in lockfile"


def format_audit(data: dict | str, lock: dict) -> str:
    if isinstance(data, str):
        return data
    summary = ", ".join(
        f"{level}: {count}"
        for level, count in data["metadata"]["vulnerabilities"].items()
    )
    findings = []
    severity_order = {"critical": 0, "high": 1, "moderate": 2, "low": 3, "info": 4}
    for name, vulnerability in sorted(
        data.get("vulnerabilities", {}).items(),
        key=lambda item: (severity_order.get(item[1]["severity"], 5), item[0]),
    ):
        candidate = vulnerability.get("fixAvailable")
        fix = "available" if candidate else "not offered by npm"
        if isinstance(candidate, dict):
            fix = f"`{candidate['name']}@{candidate.get('version', 'unspecified')}`"
            if candidate.get("isSemVerMajor"):
                fix += "; requires breaking changes; manual review"
        findings.append(
            f"- **{name}**: {vulnerability['severity']}; locked versions "
            f"`{versions(lock, vulnerability)}`; affected range "
            f"`{vulnerability['range']}`; npm fix candidate {fix}."
        )
        for via in vulnerability.get("via", []):
            if isinstance(via, dict):
                findings.append(
                    f"  - [{via['title']}]({via['url']}); "
                    f"{via['severity']}; affected range `{via['range']}`."
                )
            else:
                findings.append(f"  - Depends on affected `{via}` (see its entry).")
    return (
        summary
        + "\n\n"
        + (
            "\n".join(findings)
            if findings
            else "No known vulnerabilities reported by npm."
        )
    )


def prepare(directory: Path) -> str:
    # Leave time in the 60-minute job to write and upload a partial report.
    deadline = time.monotonic() + 45 * 60
    manifest_path = directory / "package.json"
    lock_path = directory / "package-lock.json"
    before_lock = json.loads(lock_path.read_text())
    before = audit(directory, deadline=deadline)
    affected = before.get("vulnerabilities", {}) if isinstance(before, dict) else {}
    changes = []
    notes = []

    # Give compatible security fixes the first use of the shared time budget.
    fixed = run(
        directory,
        "audit",
        "fix",
        "--package-lock-only",
        "--ignore-scripts",
        "--audit",
        deadline=deadline,
    )
    if fixed.returncode:
        notes.append(
            f"Initial security fix returned exit {fixed.returncode}; remaining findings "
            "or a tool error require manual review."
        )
    # Preserve those fixes if the wider stable-version upgrade cannot resolve.
    security_manifest = manifest_path.read_text()
    security_lock = lock_path.read_bytes()
    manifest = json.loads(security_manifest)

    # Preserve overrides and peer constraints for a maintainer to review.
    for section in ("dependencies", "devDependencies", "optionalDependencies"):
        for name, current in sorted(
            manifest.get(section, {}).items(),
            key=lambda item: (item[0] not in affected, item[0]),
        ):
            if not re.fullmatch(r"[~^]?\d+\.\d+\.\d+", current):
                notes.append(
                    f"Retained {name} specifier `{current}` for manual review."
                )
                continue
            result = run(
                directory,
                "view",
                f"{name}@latest",
                "version",
                "--json",
                deadline=deadline,
            )
            try:
                latest = json.loads(result.stdout)
            except json.JSONDecodeError:
                latest = None
            if result.returncode or not isinstance(latest, str):
                notes.append(f"Could not look up {name}; retained `{current}`.")
                continue
            if latest != current.lstrip("~^"):
                manifest[section][name] = latest
                changes.append((name, f"- {name}: `{current}` → `{latest}`"))

    if changes:
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    lock = run(
        directory,
        "install",
        "--package-lock-only",
        "--ignore-scripts",
        "--no-audit",
        deadline=deadline,
    )
    if lock.returncode:
        manifest_path.write_text(security_manifest)
        lock_path.write_bytes(security_lock)
        notes.append(
            "Stable upgrade resolution failed; restored the manifest and lockfile "
            "from the initial security fix attempt."
        )
        changes = []
    else:
        # Keep fixes within the proposed manifest constraints; never use --force.
        fixed = run(
            directory,
            "audit",
            "fix",
            "--package-lock-only",
            "--ignore-scripts",
            "--audit",
            deadline=deadline,
        )
        if fixed.returncode:
            notes.append(
                f"Automatic audit fix returned exit {fixed.returncode}; remaining findings "
                "or a tool error require manual review."
            )

    install = run(directory, "ci", "--no-audit", deadline=deadline)
    if install.returncode:
        build_status = f"Not run: npm ci failed (exit {install.returncode})."
    else:
        build = run(directory, "run", "build", deadline=deadline)
        build_status = (
            "Passed."
            if build.returncode == 0
            else f"Failed (exit {build.returncode}); manual repair required."
        )
    after = audit(directory, deadline=deadline)
    after_lock = json.loads(lock_path.read_text())
    after_affected = after.get("vulnerabilities", {}) if isinstance(after, dict) else {}
    security_changes = []
    reported_changes = set()
    for name, vulnerability in affected.items():
        old = versions(before_lock, vulnerability)
        current = after_affected.get(name)
        if current is None:
            current = {
                "nodes": [
                    node
                    for node, package in after_lock.get("packages", {}).items()
                    if node == f"node_modules/{name}"
                    or node.endswith(f"/node_modules/{name}")
                    or package.get("name") == name
                ]
            }
        new = versions(after_lock, current)
        if old != new:
            status = "after audit unavailable; fix unconfirmed"
            if isinstance(after, dict):
                status = (
                    "still reported by npm"
                    if name in after.get("vulnerabilities", {})
                    else "no longer reported by npm"
                )
            security_changes.append(f"- {name}: `{old}` → `{new}`; {status}.")
            reported_changes.add(name)
    security_changes.extend(
        line
        for name, line in changes
        if name in affected and name not in reported_changes
    )
    if time.monotonic() >= deadline:
        notes.append(
            "The shared 45-minute npm time budget was exhausted; remaining commands were skipped."
        )
    return (
        "# Annual npm dependency audit\n\n"
        f"Project: `{directory}`\n\n"
        f"Run: {datetime.now(timezone.utc).isoformat()}\n\n"
        "This is a best-effort upgrade drive. Remaining vulnerabilities are accepted "
        "between annual reviews; this report does not certify that the project is "
        "free of vulnerabilities. Review compatibility and validation before merging.\n\n"
        "## Security findings and fixes\n\n"
        "### Changes to affected dependencies\n\n"
        + (
            "\n".join(security_changes)
            or "No upgrades to affected dependencies resolved."
        )
        + "\n\n"
        "npm counts affected package entries, including propagated findings in "
        "parent packages. These are not counts of distinct advisories or "
        "demonstrated exploit paths. Fix candidates can require manual migrations.\n\n"
        f"### Before\n\n{format_audit(before, before_lock)}\n\n"
        f"### After\n\n{format_audit(after, after_lock)}\n\n"
        "## Other stable dependency upgrades\n\n"
        + (
            "\n".join(line for name, line in changes if name not in affected)
            or "No other direct dependency upgrades resolved."
        )
        + "\n\n"
        f"## Production build\n\n{build_status}\n\n"
        "## Remaining work\n\n"
        "Review retained overrides and peer constraints, transitive dependency fixes, "
        "and any major-version migration requirements. Build and installation logs "
        "are available in the workflow run.\n\n"
        + (
            "\n".join(f"- {note}" for note in notes)
            or "No additional tool errors recorded."
        )
        + "\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", default="website")
    parser.add_argument(
        "--report", type=Path, required=True, help="Temporary output for the PR body"
    )
    args = parser.parse_args()
    directory = Path(args.directory)
    if (
        directory.is_absolute()
        or ".." in directory.parts
        or not re.fullmatch(r"[A-Za-z0-9_./-]+", args.directory)
    ):
        parser.error("directory must be a relative npm project path without '..'")
    if (
        not (directory / "package.json").is_file()
        or not (directory / "package-lock.json").is_file()
    ):
        parser.error("directory must contain package.json and package-lock.json")
    report = prepare(directory)
    args.report.write_text(report)
    print(report)


if __name__ == "__main__":
    main()
