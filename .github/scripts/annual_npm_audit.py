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


def audit(directory: Path, *, deadline: float | None = None) -> str:
    result = run(directory, "audit", "--json", "--audit", deadline=deadline)
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return f"Audit unavailable (exit {result.returncode})."
    counts = data.get("metadata", {}).get("vulnerabilities")
    if result.returncode not in (0, 1) or data.get("error") or counts is None:
        return f"Audit unavailable (exit {result.returncode})."
    summary = ", ".join(f"{level}: {count}" for level, count in counts.items())
    findings = []
    for name, vulnerability in data.get("vulnerabilities", {}).items():
        candidate = vulnerability.get("fixAvailable")
        fix = "available" if candidate else "not available"
        if isinstance(candidate, dict) and candidate.get("isSemVerMajor"):
            fix = "requires breaking changes; manual review"
        findings.append(
            f"- {name}: {vulnerability['severity']}; affected range "
            f"`{vulnerability['range']}`; npm fix candidate {fix}."
        )
    return summary + ("\n\n" + "\n".join(findings) if findings else "")


def prepare(directory: Path) -> Path:
    # Leave time in the 60-minute job to write and upload a partial report.
    deadline = time.monotonic() + 45 * 60
    manifest_path = directory / "package.json"
    lock_path = directory / "package-lock.json"
    original_manifest = manifest_path.read_text()
    original_lock = lock_path.read_bytes()
    manifest = json.loads(original_manifest)
    before = audit(directory, deadline=deadline)
    changes = []
    notes = []

    # Preserve overrides and peer constraints for a maintainer to review.
    for section in ("dependencies", "devDependencies", "optionalDependencies"):
        for name, current in manifest.get(section, {}).items():
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
                changes.append(f"- {name}: `{current}` → `{latest}`")

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
        manifest_path.write_text(original_manifest)
        lock_path.write_bytes(original_lock)
        notes.append(
            "Upgrade resolution failed; restored the original manifest and lockfile."
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
    if time.monotonic() >= deadline:
        notes.append(
            "The shared 45-minute npm time budget was exhausted; remaining commands were skipped."
        )
    report = directory / "DEPENDENCY-AUDIT.md"
    report.write_text(
        "# Annual npm dependency audit\n\n"
        f"Run: {datetime.now(timezone.utc).isoformat()}\n\n"
        "This is a best-effort upgrade drive. Remaining vulnerabilities are accepted "
        "between annual reviews; this report does not certify that the project is "
        "free of vulnerabilities. Review compatibility and validation before merging.\n\n"
        "## Proposed direct dependency upgrades\n\n"
        + ("\n".join(changes) or "No direct dependency upgrades resolved.")
        + "\n\n## Audit results\n\n"
        "npm counts affected package entries, including propagated findings in "
        "parent packages. These are not counts of distinct advisories or "
        "demonstrated exploit paths. Fix candidates can require manual migrations.\n\n"
        f"Before: {before}\n\nAfter: {after}\n\n"
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
    print(report.read_text())
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", default="website")
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
    prepare(directory)


if __name__ == "__main__":
    main()
