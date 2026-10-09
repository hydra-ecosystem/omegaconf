import io
import json
import sys
import tarfile
import urllib.error
import urllib.request
import zipfile
from email.message import Message
from pathlib import Path
from unittest.mock import Mock

import pytest
import yaml
from packaging.version import Version

from build_helpers import release_workflow as release

COMMIT = "a" * 40
VERSION = "2.4.0"


def prepared_release(state: dict, **changes: object) -> dict:
    release = {
        "tag_name": state["tag"],
        "target_commitish": state["commit"],
        "name": f"OmegaConf {state['version']}",
        "body": state["notes"],
        "draft": True,
        "prerelease": False,
        "assets": [],
        "html_url": "https://github.com/release",
    }
    release.update(changes)
    return release


@pytest.fixture
def bundle(tmp_path: Path) -> tuple[Path, Path]:
    dist = tmp_path / "dist"
    dist.mkdir()
    for package in release.PACKAGES:
        name = package.replace("-", "_")
        metadata = f"Metadata-Version: 2.1\nName: {package}\nVersion: {VERSION}\n"
        with zipfile.ZipFile(dist / f"{name}-{VERSION}-py3-none-any.whl", "w") as wheel:
            wheel.writestr(f"{name}-{VERSION}.dist-info/METADATA", metadata)
        with tarfile.open(dist / f"{name}-{VERSION}.tar.gz", "w:gz") as sdist:
            member = tarfile.TarInfo(f"{name}-{VERSION}/PKG-INFO")
            member.size = len(metadata.encode())
            sdist.addfile(member, io.BytesIO(metadata.encode()))
    path = tmp_path / "state.json"
    release.save_state(
        path,
        {
            "repository": "hydra-ecosystem/omegaconf",
            "commit": COMMIT,
            "version": VERSION,
            "tag": f"v{VERSION}",
            "notes": "Release notes\n",
            "files": release.artifact_manifest(dist, VERSION),
            "release_id": 123,
            "release_target_commitish": COMMIT,
            "tag_created": True,
        },
    )
    return path, dist


@pytest.mark.parametrize(
    "versions,target,expected",
    [
        (
            {"2.4.0.dev9": [1], "2.4.0.dev18": [1], "2.3.6": [1]},
            "2.4.0",
            (False, "2.4.0.dev18"),
        ),
        ({"2.3.6": [1], "2.4.0.dev18": [1]}, "2.3.7", (False, "2.3.6")),
        ({"2.4.0rc1": [1], "2.4.0.dev18": [1]}, "2.4.0", (False, "2.4.0rc1")),
        ({"2.4.0": [1], "2.4.0rc1": [1]}, "2.4.1", (False, "2.4.0")),
        ({"2.4": [], "invalid": [1], "2.3.6": [1]}, "2.4.0", (True, "none")),
    ],
)
def test_pypi_version_comparison(versions: dict, target: str, expected: tuple) -> None:
    assert release.inspect_versions(versions, Version(target)) == expected


def test_notes_include_only_requested_release() -> None:
    text = "## 2.4.0 (2026-10-09)\n\nFinal notes\n### Features\nNew feature\n## 2.4.0rc1 (2026-09-28)\nOld notes\n"
    assert (
        release.release_notes(text, VERSION)
        == "Final notes\n### Features\nNew feature\n"
    )
    with pytest.raises(RuntimeError, match="no release notes"):
        release.release_notes(text, "2.4.1")


def test_request_json_builds_authenticated_json_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Response:
        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def read(self) -> bytes:
            return b'{"ok": true}'

    requests = []
    monkeypatch.setenv("GH_TOKEN", "secret")
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda request, timeout: requests.append((request, timeout)) or Response(),
    )
    assert release.request_json(
        "https://example.test/api",
        method="POST",
        payload={"ready": True},
        github=True,
    ) == {"ok": True}
    request, timeout = requests[0]
    assert timeout == 30
    assert request.method == "POST"
    assert request.data == b'{"ready": true}'
    assert request.headers["Authorization"] == "Bearer secret"
    assert request.headers["Content-type"] == "application/json"


@pytest.mark.parametrize(
    "status,method,expected",
    [
        (404, "GET", None),
        (500, "GET", urllib.error.HTTPError),
        (404, "POST", urllib.error.HTTPError),
    ],
)
def test_request_json_handles_only_missing_get_resources(
    monkeypatch: pytest.MonkeyPatch,
    status: int,
    method: str,
    expected: object,
) -> None:
    error = urllib.error.HTTPError(
        "https://example.test", status, "error", Message(), None
    )
    monkeypatch.setattr(urllib.request, "urlopen", Mock(side_effect=error))
    if expected is None:
        assert release.request_json("https://example.test", method=method) is None
    else:
        with pytest.raises(urllib.error.HTTPError):
            release.request_json("https://example.test", method=method)


def test_github_api_and_empty_response(monkeypatch: pytest.MonkeyPatch) -> None:
    call = Mock(return_value=None)
    monkeypatch.setattr(release, "request_json", call)
    state = {"repository": "owner/repo"}
    assert release.github_api(state, "releases/1", method="DELETE") is None
    call.assert_called_once_with(
        "https://api.github.com/repos/owner/repo/releases/1",
        github=True,
        method="DELETE",
    )


def test_read_version_requires_a_version_assignment(tmp_path: Path) -> None:
    path = tmp_path / "version.py"
    path.write_text("VERSION = '2.4.0'\n")
    with pytest.raises(RuntimeError, match="No __version__"):
        release.read_version(path)


def test_pypi_releases_requires_an_existing_project(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(release, "request_json", lambda _: None)
    with pytest.raises(RuntimeError, match="Cannot find existing PyPI project"):
        release.pypi_releases("missing")


def test_pypi_releases_returns_project_versions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(release, "request_json", lambda _: {"releases": {VERSION: []}})
    assert release.pypi_releases("omegaconf") == {VERSION: []}


def test_summary_writes_the_github_step_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    release.summary("## Ready")
    assert summary.read_text() == "## Ready\n"


@pytest.mark.parametrize("already", [None, "omegaconf", "omegaconf-pydevd"])
def test_preparation_checks_both_packages_and_reports_latest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    already: str | None,
) -> None:
    for version_path in release.PACKAGES.values():
        path = tmp_path / version_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f'__version__ = "{VERSION}"\n')
    (tmp_path / "NEWS.md").write_text("## 2.4.0 (2026-10-09)\n\nFinal\n")
    calls = []

    def pypi(package: str) -> dict:
        calls.append(package)
        return {"2.4.0.dev18": [1], **({VERSION: [1]} if package == already else {})}

    monkeypatch.setattr(release, "pypi_releases", pypi)
    output = tmp_path / "state.json"
    if already:
        with pytest.raises(RuntimeError, match=f"already published: {already}"):
            release.plan(tmp_path, VERSION, COMMIT, "hydra-ecosystem/omegaconf", output)
        assert not output.exists()
    else:
        release.plan(tmp_path, VERSION, COMMIT, "hydra-ecosystem/omegaconf", output)
        assert json.loads(output.read_text())["commit"] == COMMIT
    assert calls == list(release.PACKAGES)
    assert "2.4.0.dev18" in capsys.readouterr().out


def test_preparation_rejects_wrong_source_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(release, "read_version", lambda path: "2.4.0rc1")
    with pytest.raises(RuntimeError, match="source has 2.4.0rc1"):
        release.plan(tmp_path, VERSION, COMMIT, "repo", tmp_path / "state.json")


@pytest.mark.parametrize("version,commit", [("2.4.0rc1", COMMIT), (VERSION, "abc")])
def test_plan_rejects_invalid_target(tmp_path: Path, version: str, commit: str) -> None:
    with pytest.raises(RuntimeError):
        release.plan(tmp_path, version, commit, "repo", tmp_path / "state.json")


def test_manifest_requires_both_artifact_formats(bundle: tuple[Path, Path]) -> None:
    _, dist = bundle
    next(dist.glob("*.whl")).unlink()
    with pytest.raises(RuntimeError, match="one wheel and one sdist"):
        release.artifact_manifest(dist, VERSION)


def test_manifest_rejects_invalid_wheel_metadata(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    with zipfile.ZipFile(dist / "invalid.whl", "w") as wheel:
        wheel.writestr("payload.txt", "no metadata")
    with pytest.raises(RuntimeError, match="Invalid wheel metadata"):
        release.artifact_manifest(dist, VERSION)


def test_manifest_rejects_invalid_sdist_metadata(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    with tarfile.open(dist / "invalid.tar.gz", "w:gz"):
        pass
    with pytest.raises(RuntimeError, match="Invalid sdist metadata"):
        release.artifact_manifest(dist, VERSION)


def test_manifest_rejects_sdist_without_extractable_metadata(
    bundle: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    _, dist = bundle
    original = tarfile.TarFile.extractfile
    monkeypatch.setattr(tarfile.TarFile, "extractfile", lambda *_: None)
    with pytest.raises(RuntimeError, match="Invalid sdist metadata"):
        release.artifact_manifest(dist, VERSION)
    monkeypatch.setattr(tarfile.TarFile, "extractfile", original)


@pytest.mark.parametrize("filename", ["unexpected.txt", "omegaconf-extra.whl"])
def test_manifest_rejects_unexpected_or_duplicate_distributions(
    bundle: tuple[Path, Path], filename: str
) -> None:
    _, dist = bundle
    source = next(dist.glob("*.whl"))
    target = dist / filename
    target.write_bytes(source.read_bytes())
    pattern = (
        "Unexpected distribution" if filename.endswith(".txt") else "Duplicate wheel"
    )
    with pytest.raises(RuntimeError, match=pattern):
        release.artifact_manifest(dist, VERSION)


def test_manifest_rejects_wrong_package_version(bundle: tuple[Path, Path]) -> None:
    _, dist = bundle
    wheel = next(dist.glob("*.whl"))
    replacement = dist / "wrong-package.whl"
    with zipfile.ZipFile(replacement, "w") as archive:
        archive.writestr(
            "wrong.dist-info/METADATA",
            "Metadata-Version: 2.1\nName: unrelated\nVersion: 9.9.9\n",
        )
    wheel.unlink()
    with pytest.raises(RuntimeError, match="Unexpected package/version"):
        release.artifact_manifest(dist, VERSION)


@pytest.mark.parametrize(
    "mode", ["empty", "partial", "complete", "wrong-hash", "extra", "duplicate"]
)
def test_publication_classification(
    bundle: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    path, _ = bundle
    state = json.loads(path.read_text())

    def pypi(url: str) -> dict | None:
        package = url.split("/")[-3]
        files = [f for f in state["files"] if f["package"] == package]
        if mode == "empty" or (mode == "partial" and package == "omegaconf-pydevd"):
            return None
        response = {
            "urls": [
                {
                    "filename": f["filename"],
                    "digests": {
                        "sha256": "wrong" if mode == "wrong-hash" else f["sha256"]
                    },
                }
                for f in files
            ]
        }
        if mode == "extra" and package == "omegaconf":
            response["urls"].append(
                {"filename": "unexpected.whl", "digests": {"sha256": "extra"}}
            )
        if mode == "duplicate" and package == "omegaconf":
            response["urls"].append(response["urls"][0])
        return response

    monkeypatch.setattr(release, "request_json", pypi)
    assert release.publication_state(state) == (
        "partial" if mode in {"wrong-hash", "extra", "duplicate"} else mode
    )


@pytest.mark.parametrize("result", ["empty", "partial", "unknown", "complete"])
def test_reconciliation_deletes_only_confirmed_empty_publication(
    bundle: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch, result: str
) -> None:
    path, _ = bundle
    cleanup = Mock()
    monkeypatch.setattr(release, "cleanup", cleanup)
    monkeypatch.setattr(release.time, "sleep", lambda _: None)
    probe = Mock(return_value=result)
    if result == "unknown":
        probe.side_effect = urllib.error.URLError("network unavailable")
    monkeypatch.setattr(release, "publication_state", probe)
    if result == "complete":
        release.reconcile(path, "failure")
    else:
        with pytest.raises(
            RuntimeError, match="fresh run" if result == "empty" else "preserving"
        ):
            release.reconcile(path, "failure")
    assert cleanup.call_count == (1 if result == "empty" else 0)


def test_reconciliation_waits_for_index_convergence(
    bundle: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    path, _ = bundle
    probe = Mock(side_effect=["empty", "partial", "complete"])
    cleanup = Mock()
    monkeypatch.setattr(release, "publication_state", probe)
    monkeypatch.setattr(release, "cleanup", cleanup)
    monkeypatch.setattr(release.time, "sleep", lambda _: None)
    release.reconcile(path, "failure")
    assert probe.call_count == 3
    cleanup.assert_not_called()


@pytest.mark.parametrize("first", ["partial", "unknown", "empty"])
def test_ambiguous_or_successful_upload_never_rolls_back(
    bundle: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch, first: str
) -> None:
    path, _ = bundle
    cleanup = Mock()
    probe = Mock(side_effect=[first, "empty", "empty", "empty", "empty", "empty"])
    monkeypatch.setattr(release, "publication_state", probe)
    monkeypatch.setattr(release, "cleanup", cleanup)
    monkeypatch.setattr(release.time, "sleep", lambda _: None)
    with pytest.raises(RuntimeError, match="preserving"):
        release.reconcile(path, "success" if first == "empty" else "failure")
    cleanup.assert_not_called()


@pytest.mark.parametrize("existing_tag", [False, True])
def test_draft_pins_the_commit_and_tracks_only_its_own_tag(
    bundle: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch, existing_tag: bool
) -> None:
    path, dist = bundle
    state = json.loads(path.read_text())
    del state["release_id"]
    release.save_state(path, state)
    monkeypatch.setattr(
        release, "tag_commit", lambda _: COMMIT if existing_tag else None
    )
    calls = []

    def api(state: dict, endpoint: str, **kwargs: object) -> object:
        calls.append((endpoint, kwargs))
        if endpoint.startswith("releases?"):
            return []
        if endpoint == "git/refs":
            return {"object": {"sha": COMMIT}}
        assert endpoint == "releases"
        return {
            "id": 456,
            "html_url": "https://github.com/draft",
            "target_commitish": "release-branch",
        }

    monkeypatch.setattr(release, "github_api", api)
    release.draft(path, dist)
    state = json.loads(path.read_text())
    assert state["release_id"] == 456
    assert state["release_target_commitish"] == "release-branch"
    assert state["tag_created"] is (not existing_tag)
    assert any(endpoint == "git/refs" for endpoint, _ in calls) is (not existing_tag)
    payload = calls[-1][1]["payload"]
    assert payload == {
        "tag_name": f"v{VERSION}",
        "target_commitish": COMMIT,
        "name": f"OmegaConf {VERSION}",
        "body": "Release notes\n",
        "draft": True,
        "prerelease": False,
    }


def test_draft_paginates_release_listing_and_rejects_replaced_tag(
    bundle: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    path, dist = bundle
    page = [{"tag_name": f"v1.0.{i}"} for i in range(100)]
    calls = []

    def api(state: dict, endpoint: str, **kwargs: object) -> object:
        calls.append(endpoint)
        if endpoint.endswith("page=1"):
            return page
        return []

    monkeypatch.setattr(release, "github_api", api)
    monkeypatch.setattr(release, "tag_commit", lambda _: "b" * 40)
    with pytest.raises(RuntimeError, match="different commit"):
        release.draft(path, dist)
    assert calls == ["releases?per_page=100&page=1", "releases?per_page=100&page=2"]


def test_tag_commit_handles_missing_annotated_and_non_commit_tags(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = {"tag": "v2.4.0"}
    monkeypatch.setattr(release, "github_api", Mock(return_value=None))
    assert release.tag_commit(state) is None

    monkeypatch.setattr(
        release,
        "github_api",
        Mock(
            side_effect=[
                {"object": {"type": "tag", "sha": "b" * 40}},
                {"object": {"type": "commit", "sha": COMMIT}},
            ]
        ),
    )
    assert release.tag_commit(state) == COMMIT

    monkeypatch.setattr(
        release,
        "github_api",
        Mock(return_value={"object": {"type": "tree", "sha": "b" * 40}}),
    )
    with pytest.raises(RuntimeError, match="does not identify a commit"):
        release.tag_commit(state)


def test_checked_release_rejects_changed_tag_name(
    bundle: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    path, _ = bundle
    state = json.loads(path.read_text())
    monkeypatch.setattr(
        release,
        "github_api",
        Mock(return_value=prepared_release(state, tag_name="v9.9.9")),
    )
    with pytest.raises(RuntimeError, match="GitHub Release changed"):
        release.checked_release(state)


def test_checked_release_uses_retained_create_response_target(
    bundle: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    path, _ = bundle
    state = json.loads(path.read_text())
    state["release_target_commitish"] = "release-branch"
    release_response = prepared_release(state, target_commitish="release-branch")

    def api(_: dict, resource: str, **__: object) -> object:
        if resource == "releases/123":
            return release_response
        return {"object": {"type": "commit", "sha": COMMIT}}

    monkeypatch.setattr(release, "github_api", api)
    assert release.checked_release(state) == release_response


def test_preexisting_draft_blocks_duplicate_creation(
    bundle: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    path, dist = bundle
    api = Mock(return_value=[{"tag_name": f"v{VERSION}", "draft": True}])
    monkeypatch.setattr(release, "github_api", api)
    with pytest.raises(RuntimeError, match="already exists"):
        release.draft(path, dist)
    assert api.call_count == 1
    assert api.call_args.kwargs == {}


@pytest.mark.parametrize("owned", [False, True])
def test_cleanup_preserves_preexisting_tags(
    bundle: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch, owned: bool
) -> None:
    path, _ = bundle
    state = json.loads(path.read_text())
    state["tag_created"] = owned
    monkeypatch.setattr(
        release, "checked_release", lambda _: {"draft": True, "body": state["notes"]}
    )
    monkeypatch.setattr(release, "tag_commit", lambda _: COMMIT)
    api = Mock(return_value={"object": {"type": "commit", "sha": COMMIT}})
    monkeypatch.setattr(release, "github_api", api)
    release.cleanup(state)
    deletes = [
        call for call in api.call_args_list if call.kwargs.get("method") == "DELETE"
    ]
    assert [call.args[1] for call in deletes] == ["releases/123"] + (
        [f"git/refs/tags/v{VERSION}"] if owned else []
    )


@pytest.mark.parametrize("published,edited", [(True, False), (False, True)])
def test_cleanup_preserves_published_or_edited_release(
    bundle: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    published: bool,
    edited: bool,
) -> None:
    path, _ = bundle
    state = json.loads(path.read_text())
    release_response = prepared_release(state, draft=not published)
    if edited:
        release_response["body"] = "Edited"

    def api(_: dict, resource: str, **__: object) -> object:
        if resource == "releases/123":
            return release_response
        return {"object": {"type": "commit", "sha": COMMIT}}

    monkeypatch.setattr(release, "github_api", api)
    with pytest.raises(RuntimeError):
        release.cleanup(state)


def test_replaced_annotated_tag_blocks_cleanup(
    bundle: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    path, _ = bundle
    state = json.loads(path.read_text())
    monkeypatch.setattr(release, "tag_commit", lambda _: COMMIT)
    api = Mock(
        side_effect=lambda _, resource, **kwargs: (
            prepared_release(state)
            if resource == "releases/123"
            else {"object": {"type": "tag", "sha": "b" * 40}}
        )
    )
    monkeypatch.setattr(release, "github_api", api)
    with pytest.raises(RuntimeError, match="tag changed"):
        release.cleanup(state)
    assert not any(call.kwargs.get("method") == "DELETE" for call in api.call_args_list)


def test_changed_tag_blocks_cleanup(
    bundle: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    path, _ = bundle
    api = Mock(return_value=prepared_release(json.loads(path.read_text())))
    monkeypatch.setattr(release, "github_api", api)
    monkeypatch.setattr(release, "tag_commit", lambda _: "b" * 40)
    with pytest.raises(RuntimeError, match="tag changed"):
        release.cleanup(json.loads(path.read_text()))
    assert not any(call.kwargs.get("method") == "DELETE" for call in api.call_args_list)


@pytest.mark.parametrize(
    "field,value",
    [
        ("target_commitish", "b" * 40),
        ("name", "Edited release"),
        ("body", "Edited notes\n"),
        ("prerelease", True),
        ("assets", [{"name": "unexpected.zip"}]),
    ],
)
def test_cleanup_preserves_changed_prepared_release_fields(
    bundle: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: object,
) -> None:
    path, _ = bundle
    state = json.loads(path.read_text())
    api = Mock(return_value=prepared_release(state, **{field: value}))
    monkeypatch.setattr(release, "github_api", api)
    with pytest.raises(RuntimeError, match="Prepared GitHub Release changed"):
        release.cleanup(state)
    assert not any(call.kwargs.get("method") == "DELETE" for call in api.call_args_list)


def test_verify_rejects_changed_prepared_release_before_upload(
    bundle: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    path, dist = bundle
    state = json.loads(path.read_text())
    monkeypatch.setattr(
        release, "github_api", Mock(return_value=prepared_release(state, name="Edited"))
    )
    with pytest.raises(RuntimeError, match="Prepared GitHub Release changed"):
        release.verify(path, dist)


def test_finalize_rejects_changed_prepared_release_before_publication(
    bundle: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    path, _ = bundle
    state = json.loads(path.read_text())
    monkeypatch.setattr(release, "publication_state", lambda _: "complete")
    monkeypatch.setattr(
        release,
        "github_api",
        Mock(return_value=prepared_release(state, assets=[{"name": "manual.zip"}])),
    )
    with pytest.raises(RuntimeError, match="Prepared GitHub Release changed"):
        release.finalize(path)


@pytest.mark.parametrize("already_published", [False, True])
def test_finalization_retries_only_github_publication(
    bundle: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch, already_published: bool
) -> None:
    path, _ = bundle
    monkeypatch.setattr(release, "publication_state", lambda _: "complete")
    state = json.loads(path.read_text())
    github_release = prepared_release(state, draft=not already_published)
    monkeypatch.setattr(release, "checked_release", lambda _: github_release)
    monkeypatch.setattr(release, "tag_commit", lambda _: COMMIT)
    api = Mock(return_value=github_release)
    monkeypatch.setattr(release, "github_api", api)
    release.finalize(path)
    assert api.call_count == (0 if already_published else 1)
    if not already_published:
        assert api.call_args.kwargs == {
            "method": "PATCH",
            "payload": {"draft": False, "make_latest": "true"},
        }


def test_finalization_requires_both_packages(
    bundle: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    path, _ = bundle
    monkeypatch.setattr(release, "publication_state", lambda _: "partial")
    api = Mock()
    monkeypatch.setattr(release, "github_api", api)
    with pytest.raises(RuntimeError, match="All expected artifacts"):
        release.finalize(path)
    api.assert_not_called()


def test_finalization_requires_the_prepared_release(
    bundle: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    path, _ = bundle
    monkeypatch.setattr(release, "publication_state", lambda _: "complete")
    monkeypatch.setattr(release, "checked_release", lambda _: None)
    with pytest.raises(RuntimeError, match="Prepared GitHub Release is missing"):
        release.finalize(path)


@pytest.mark.parametrize(
    "release_changes",
    [{"draft": False}, {"draft": True, "prerelease": True}],
)
def test_verify_rejects_a_published_or_prerelease_draft(
    bundle: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    release_changes: dict[str, object],
) -> None:
    path, dist = bundle
    state = json.loads(path.read_text())
    checked = prepared_release(state, **release_changes)
    monkeypatch.setattr(release, "checked_release", lambda _: checked)
    monkeypatch.setattr(release, "tag_commit", lambda _: COMMIT)
    with pytest.raises(RuntimeError, match="Prepared draft/tag"):
        release.verify(path, dist)


def test_finalization_preserves_draft_when_tag_is_missing(
    bundle: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    path, _ = bundle
    monkeypatch.setattr(release, "publication_state", lambda _: "complete")
    monkeypatch.setattr(release, "tag_commit", lambda _: None)
    api = Mock(return_value=prepared_release(json.loads(path.read_text())))
    monkeypatch.setattr(release, "github_api", api)
    with pytest.raises(RuntimeError, match="tag is missing"):
        release.finalize(path)
    assert not any(call.kwargs.get("method") == "PATCH" for call in api.call_args_list)


def test_retained_artifact_tampering_blocks_upload(
    bundle: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    path, dist = bundle
    wheel = next(dist.glob("*.whl"))
    with zipfile.ZipFile(wheel, "a") as archive:
        archive.writestr("unexpected.txt", "modified after preparation")
    api = Mock()
    monkeypatch.setattr(release, "github_api", api)
    with pytest.raises(RuntimeError, match="differ from"):
        release.verify(path, dist)
    api.assert_not_called()


def test_workflow_approval_and_retry_boundaries() -> None:
    workflow = yaml.load(
        Path(".github/workflows/publish.yml").read_text(), Loader=yaml.BaseLoader
    )
    assert set(workflow["on"]) == {"workflow_dispatch"}
    jobs = workflow["jobs"]
    assert "environment" not in jobs["prepare"]
    assert jobs["pypi-publish"]["environment"] == "pypi-publish"
    assert jobs["pypi-publish"]["permissions"] == {
        "contents": "read",
        "id-token": "write",
    }
    assert jobs["pypi-publish"]["outputs"] == {
        "upload-outcome": "${{ steps.upload.outcome }}"
    }
    assert jobs["github-release"]["needs"] == "pypi-publish"
    assert not any(
        "gh-action-pypi-publish" in step.get("uses", "")
        for step in jobs["github-release"]["steps"]
    )
    upload = next(
        step for step in jobs["pypi-publish"]["steps"] if step.get("id") == "upload"
    )
    assert upload["continue-on-error"] == "true"
    reconcile = next(
        step
        for step in jobs["github-release"]["steps"]
        if "reconcile actual pypi" in step.get("name", "").lower()
    )
    assert reconcile["env"]["UPLOAD_OUTCOME"] == (
        "${{ needs.pypi-publish.outputs.upload-outcome }}"
    )
    assert not any(
        "reconcile" in step.get("run", "") for step in jobs["pypi-publish"]["steps"]
    )
    assert jobs["prepare"]["permissions"] == {"contents": "write"}


@pytest.mark.parametrize(
    "argv,action",
    [
        (
            [
                "plan",
                "--state",
                "state",
                "--version",
                VERSION,
                "--commit",
                COMMIT,
                "--repository",
                "repo",
            ],
            "plan",
        ),
        (["draft", "--state", "state", "--dist", "dist"], "draft"),
        (["verify", "--state", "state", "--dist", "dist"], "verify"),
        (["reconcile", "--state", "state", "--upload-outcome", "failure"], "reconcile"),
        (["finalize", "--state", "state"], "finalize"),
    ],
)
def test_cli_dispatches_each_action(
    monkeypatch: pytest.MonkeyPatch, argv: list[str], action: str
) -> None:
    calls = []
    monkeypatch.setattr(sys, "argv", ["release_workflow", *argv])
    monkeypatch.setattr(release, action, lambda *args: calls.append(args))
    release.main()
    assert calls


@pytest.mark.parametrize(
    "argv,message",
    [
        (["plan", "--state", "state"], "plan requires"),
        (["draft", "--state", "state"], "draft requires"),
        (["reconcile", "--state", "state"], "reconcile requires"),
    ],
)
def test_cli_rejects_missing_action_arguments(
    monkeypatch: pytest.MonkeyPatch, argv: list[str], message: str
) -> None:
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    monkeypatch.setattr(sys, "argv", ["release_workflow", *argv])
    with pytest.raises(SystemExit):
        release.main()
