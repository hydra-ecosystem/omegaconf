"""Prepare stable releases and reconcile publication without uploading to PyPI."""

import argparse
import ast
import hashlib
import json
import os
import re
import tarfile
import time
import urllib.error
import urllib.request
import zipfile
from email.parser import Parser
from pathlib import Path
from typing import Any
from urllib.parse import quote

from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version

PACKAGES = {
    "omegaconf": "omegaconf/version.py",
    "omegaconf-pydevd": "subprojects/omegaconf-pydevd/version.py",
}


def request_json(
    url: str, *, method: str = "GET", payload: Any = None, github: bool = False
) -> Any:
    headers = {"Accept": "application/json", "User-Agent": "omegaconf-release"}
    if github:
        headers["Authorization"] = f"Bearer {os.environ['GH_TOKEN']}"
        headers["X-GitHub-Api-Version"] = "2022-11-28"
    data = None if payload is None else json.dumps(payload).encode()
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read()
            return json.loads(body) if body else None
    except urllib.error.HTTPError as error:
        if error.code == 404 and method == "GET":
            return None
        raise


def github_api(state: dict[str, Any], path: str, **kwargs: Any) -> Any:
    return request_json(
        f"https://api.github.com/repos/{state['repository']}/{path}".rstrip("/"),
        github=True,
        **kwargs,
    )


def read_version(path: Path) -> str:
    for node in ast.parse(path.read_text()).body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "__version__" for t in node.targets
        ):
            return str(ast.literal_eval(node.value))
    raise RuntimeError(f"No __version__ in {path}")


def release_notes(text: str, version: str) -> str:
    for entry in re.split(r"(?m)^## ", text)[1:]:
        heading, _, body = entry.partition("\n")
        if (
            re.fullmatch(re.escape(version) + r" \(\d{4}-\d{2}-\d{2}\)", heading)
            and body.strip()
        ):
            return body.strip() + "\n"
    raise RuntimeError(f"NEWS.md has no release notes for {version}")


def pypi_releases(package: str) -> dict[str, Any]:
    data = request_json(f"https://pypi.org/pypi/{package}/json")
    if data is None:
        raise RuntimeError(f"Cannot find existing PyPI project {package}")
    return data["releases"]


def inspect_versions(releases: dict[str, Any], target: Version) -> tuple[bool, str]:
    published = False
    on_line = []
    for raw_version, files in releases.items():
        try:
            version = Version(raw_version)
        except InvalidVersion:
            continue
        if version == target:
            published = True
        if files and version.release[:2] == target.release[:2]:
            on_line.append(version)
    return published, str(max(on_line)) if on_line else "none"


def summary(text: str) -> None:
    print(text)
    if path := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(path, "a") as output:
            output.write(text + "\n")


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2) + "\n")


def plan(source: Path, version: str, commit: str, repository: str, path: Path) -> None:
    if not re.fullmatch(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", version):
        raise RuntimeError("Stable releases require an X.Y.Z version")
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise RuntimeError("Release commit must be a full SHA")
    target = Version(version)
    rows, already_published = [], []
    for package, version_path in PACKAGES.items():
        actual = read_version(source / version_path)
        if actual != version:
            raise RuntimeError(f"{package}: expected {version}, source has {actual}")
        exists, latest = inspect_versions(pypi_releases(package), target)
        rows.append(
            f"| {package} | {latest} | {version} | {'yes' if exists else 'no'} |"
        )
        if exists:
            already_published.append(package)
    summary(
        f"## Release plan\n\nCommit: `{commit}`\n\n"
        "| Package | Latest published on this line | Proposed | Already published |\n"
        "| --- | --- | --- | --- |\n" + "\n".join(rows)
    )
    if already_published:
        raise RuntimeError(
            f"{version} already published: {', '.join(already_published)}"
        )
    save_state(
        path,
        {
            "repository": repository,
            "commit": commit,
            "version": version,
            "tag": f"v{version}",
            "notes": release_notes((source / "NEWS.md").read_text(), version),
        },
    )


def artifact_manifest(dist: Path, version: str) -> list[dict[str, str]]:
    files = []
    formats: dict[str, set[str]] = {package: set() for package in PACKAGES}
    for path in sorted(dist.iterdir()):
        if path.name.endswith(".whl"):
            kind = "wheel"
            with zipfile.ZipFile(path) as archive:
                names = [
                    n for n in archive.namelist() if n.endswith(".dist-info/METADATA")
                ]
                if len(names) != 1:
                    raise RuntimeError(f"Invalid wheel metadata: {path}")
                metadata = archive.read(names[0]).decode()
        elif path.name.endswith(".tar.gz"):
            kind = "sdist"
            with tarfile.open(path, "r:gz") as archive:
                members = [
                    m
                    for m in archive.getmembers()
                    if m.name.count("/") == 1 and m.name.endswith("/PKG-INFO")
                ]
                if len(members) != 1:
                    raise RuntimeError(f"Invalid sdist metadata: {path}")
                stream = archive.extractfile(members[0])
                if stream is None:
                    raise RuntimeError(f"Invalid sdist metadata: {path}")
                metadata = stream.read().decode()
        else:
            raise RuntimeError(f"Unexpected distribution: {path}")
        headers = Parser().parsestr(metadata)
        package = canonicalize_name(headers.get("Name", ""))
        if package not in PACKAGES or headers.get("Version") != version:
            raise RuntimeError(f"Unexpected package/version in {path}")
        if kind in formats[package]:
            raise RuntimeError(f"Duplicate {kind} for {package}")
        formats[package].add(kind)
        files.append(
            {
                "package": package,
                "filename": path.name,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    if any(kinds != {"wheel", "sdist"} for kinds in formats.values()):
        raise RuntimeError("Require one wheel and one sdist for each package")
    return files


def check_workflows(path: Path) -> None:
    state = json.loads(path.read_text())
    default_branch = github_api(state, "")["default_branch"]
    default_commit = github_api(state, f"commits/{quote(default_branch, safe='')}")[
        "sha"
    ]

    def workflow_tree(commit: str) -> str | None:
        entries = github_api(state, f"contents/.github?ref={commit}") or []
        return next(
            (
                entry["sha"]
                for entry in entries
                if entry["path"] == ".github/workflows" and entry["type"] == "dir"
            ),
            None,
        )

    if workflow_tree(state["commit"]) != workflow_tree(default_commit):
        raise RuntimeError(
            f"Release workflow files differ from {default_branch}. Before any PyPI upload, "
            "sync ALL .github/workflows files onto the release branch and restart preparation "
            "from the new commit. If anything already reached PyPI, preserve the release "
            "commit/tag and finish GitHub publication manually; do not upload again."
        )
    summary(f"Workflow files match {default_branch} ({default_commit}).")


def tag_commit(state: dict[str, Any]) -> str | None:
    ref = github_api(state, f"git/ref/tags/{state['tag']}")
    if ref is None:
        return None
    obj = ref["object"]
    while obj["type"] == "tag":
        obj = github_api(state, f"git/tags/{obj['sha']}")["object"]
    if obj["type"] != "commit":
        raise RuntimeError("Release tag does not identify a commit")
    return obj["sha"]


def draft(path: Path, dist: Path) -> None:
    state = json.loads(path.read_text())
    state["files"] = artifact_manifest(dist, state["version"])
    # The tag lookup endpoint returns published releases only; include existing drafts.
    page = 1
    while True:
        releases = github_api(state, f"releases?per_page=100&page={page}")
        if any(release["tag_name"] == state["tag"] for release in releases):
            raise RuntimeError(f"GitHub Release {state['tag']} already exists")
        if len(releases) < 100:
            break
        page += 1
    before = tag_commit(state)
    if before is not None and before != state["commit"]:
        raise RuntimeError("Existing tag points to a different commit")
    state["tag_created"] = False
    save_state(path, state)
    if before is None:
        github_api(
            state,
            "git/refs",
            method="POST",
            payload={"ref": f"refs/tags/{state['tag']}", "sha": state["commit"]},
        )
        state["tag_created"] = True
        save_state(path, state)
    release = github_api(
        state,
        "releases",
        method="POST",
        payload={
            "tag_name": state["tag"],
            "target_commitish": state["commit"],
            "name": f"OmegaConf {state['version']}",
            "body": state["notes"],
            "draft": True,
            "prerelease": False,
        },
    )
    state["release_id"] = release["id"]
    state["release_target_commitish"] = release.get("target_commitish", state["commit"])
    save_state(path, state)
    summary(
        f"\n## Ready for approval\n\nDraft: {release['html_url']}\n\n"
        "Approving `pypi-publish` uploads both packages, then publishes this draft.\n\n"
        "| Artifact | SHA-256 |\n| --- | --- |\n"
        + "\n".join(f"| {f['filename']} | `{f['sha256']}` |" for f in state["files"])
    )


def publication_state(state: dict[str, Any]) -> str:
    remote: dict[str, dict[str, str]] = {}
    duplicate = False
    for package in PACKAGES:
        release = request_json(
            f"https://pypi.org/pypi/{package}/{state['version']}/json"
        )
        files: dict[str, str] = {}
        if release is not None:
            for file in release["urls"]:
                filename = file["filename"]
                if filename in files:
                    duplicate = True
                files[filename] = file["digests"]["sha256"]
        remote[package] = files
    if not any(remote.values()):
        return "empty"
    expected = {package: {} for package in PACKAGES}
    for file in state["files"]:
        expected[file["package"]][file["filename"]] = file["sha256"]
    if not duplicate and remote == expected:
        return "complete"
    return "partial"


def checked_release(state: dict[str, Any]) -> dict[str, Any] | None:
    release = github_api(state, f"releases/{state['release_id']}")
    if release is not None:
        if release.get("tag_name") != state["tag"]:
            raise RuntimeError("GitHub Release changed; refusing automated recovery")
        if (
            release.get("target_commitish")
            != state.get("release_target_commitish", state["commit"])
            or release.get("name") != f"OmegaConf {state['version']}"
            or release.get("body") != state["notes"]
            or release.get("prerelease") is not False
            or release.get("assets")
        ):
            raise RuntimeError(
                "Prepared GitHub Release changed; refusing automated recovery"
            )
    actual = tag_commit(state)
    if actual is not None and actual != state["commit"]:
        raise RuntimeError("Release tag changed; refusing automated recovery")
    return release


def cleanup(state: dict[str, Any]) -> None:
    release = checked_release(state)
    if release is not None:
        if not release["draft"]:
            raise RuntimeError("Refusing to delete a published GitHub Release")
    owned_tag = (
        github_api(state, f"git/ref/tags/{state['tag']}")
        if state["tag_created"]
        else None
    )
    if owned_tag is not None and (
        owned_tag["object"]["type"] != "commit"
        or owned_tag["object"]["sha"] != state["commit"]
    ):
        raise RuntimeError("Release tag changed; refusing automated recovery")
    if release is not None:
        github_api(state, f"releases/{state['release_id']}", method="DELETE")
    if owned_tag is not None:
        github_api(state, f"git/refs/tags/{state['tag']}", method="DELETE")
    summary(
        "No artifacts published to PyPI. Removed this run's draft and newly created tag, if present."
    )


def reconcile(path: Path, upload_outcome: str) -> None:
    state = json.loads(path.read_text())
    # Allow the index to converge; uncertain results never authorize deletion.
    observed = set()
    for attempt in range(6):
        try:
            result = publication_state(state)
        except (urllib.error.URLError, TimeoutError, RuntimeError, KeyError):
            result = "unknown"
        observed.add(result)
        if result == "complete":
            summary("All expected artifacts and SHA-256 digests are verified on PyPI.")
            return
        if attempt < 5:
            time.sleep(5)
    if observed == {"empty"} and upload_outcome == "failure":
        cleanup(state)
        raise RuntimeError(
            "PyPI publication failed with no artifacts uploaded; start a fresh run"
        )
    raise RuntimeError(
        f"PyPI checks did not establish complete publication ({', '.join(sorted(observed))}); "
        "preserving draft/tag and artifacts for manual recovery"
    )


def finalize(path: Path) -> None:
    state = json.loads(path.read_text())
    if publication_state(state) != "complete":
        raise RuntimeError(
            "All expected artifacts must be verified on PyPI before publishing the draft"
        )
    release = checked_release(state)
    if release is None:
        raise RuntimeError("Prepared GitHub Release is missing")
    if tag_commit(state) != state["commit"]:
        raise RuntimeError("Prepared release tag is missing or changed")
    if release["draft"]:
        release = github_api(
            state,
            f"releases/{state['release_id']}",
            method="PATCH",
            payload={"draft": False, "make_latest": "true"},
        )
    summary(f"Published GitHub Release: {release['html_url']}")


def verify(path: Path, dist: Path) -> None:
    state = json.loads(path.read_text())
    if artifact_manifest(dist, state["version"]) != state["files"]:
        raise RuntimeError("Artifacts differ from the prepared manifest")
    release = checked_release(state)
    if (
        release is None
        or not release["draft"]
        or release.get("prerelease") is not False
        or tag_commit(state) != state["commit"]
    ):
        raise RuntimeError("Prepared draft/tag is missing or already published")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=["plan", "check-workflows", "draft", "verify", "reconcile", "finalize"],
    )
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--source", type=Path, default=Path("."))
    parser.add_argument("--dist", type=Path)
    parser.add_argument("--version")
    parser.add_argument("--commit")
    parser.add_argument("--upload-outcome", choices=["success", "failure"])
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY"))
    args = parser.parse_args()
    if args.action == "plan":
        if not all([args.version, args.commit, args.repository]):
            parser.error("plan requires --version, --commit, and --repository")
        plan(args.source, args.version, args.commit, args.repository, args.state)
    elif args.action == "check-workflows":
        check_workflows(args.state)
    elif args.action in {"draft", "verify"}:
        if args.dist is None:
            parser.error(f"{args.action} requires --dist")
        if args.action == "draft":
            draft(args.state, args.dist)
        else:
            verify(args.state, args.dist)
    elif args.action == "reconcile":
        if args.upload_outcome is None:
            parser.error("reconcile requires --upload-outcome")
        reconcile(args.state, args.upload_outcome)
    else:
        finalize(args.state)


if __name__ == "__main__":  # pragma: no cover
    main()
