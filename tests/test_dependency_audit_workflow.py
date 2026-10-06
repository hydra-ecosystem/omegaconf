# Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

WORKFLOW = yaml.safe_load(
    (Path(__file__).parents[1] / ".github/workflows/dependency-audit.yml").read_text()
)
VERIFY = next(
    step
    for step in WORKFLOW["jobs"]["pull-request"]["steps"]
    if step.get("name") == "Verify audit dependency state"
)
PUBLISH = WORKFLOW["jobs"]["pull-request"]["steps"][-1]


@pytest.fixture
def publisher(tmp_path):
    mock_cli = tmp_path / "mock-cli"
    mock_cli.write_text(
        f"#!{sys.executable}\n"
        r"""import json
import os
import subprocess
import sys
from pathlib import Path

tool = Path(sys.argv[0]).name
args = sys.argv[1:]
with open(os.environ['COMMAND_LOG'], 'a') as log:
    log.write(json.dumps([tool, *args]) + '\n')
if tool == 'git':
    if args[0] == 'rev-parse':
        head = os.environ['EXPECTED_HEAD']
        if not head:
            sys.exit(1)
        print(head)
    elif args[0] == 'cat-file':
        if os.environ['AUDIT_COMMIT_AVAILABLE'] != '1':
            sys.exit(1)
        print(os.environ['AUDIT_SHA'])
    elif args[0] == 'fetch':
        setting = 'FETCH_STATUS' if args[-1] == os.environ['AUDIT_SHA'] else 'BASE_FETCH_STATUS'
        sys.exit(int(os.environ[setting]))
    elif args[0] == 'checkout':
        sys.exit(int(os.environ['CHECKOUT_STATUS']))
    elif args[0] == 'diff':
        if '--cached' in args:
            sys.exit(int(os.environ['HAS_CHANGES']))
        if '--quiet' in args:
            sys.exit(int(os.environ['DEPENDENCY_DIFF_STATUS']))
        sys.exit(int(os.environ['HAS_CHANGES']))
    elif args[0] == 'push':
        sys.exit(int(os.environ['PUSH_STATUS']))
elif args[:2] == ['pr', 'list']:
    result = subprocess.run(['jq', args[args.index('--jq') + 1]],
                            input=os.environ['PR_LIST_JSON'], text=True,
                            capture_output=True, check=True)
    print(result.stdout, end='')
"""
    )
    mock_cli.chmod(0o755)
    for tool in ("git", "gh"):
        (tmp_path / tool).symlink_to(mock_cli)
    (tmp_path / "dependency-audit-pr.md").write_text(
        "## Security findings and fixes\n\n$(never-execute)\n"
    )

    def run_step(step, **overrides):
        number = overrides.get("PR_NUMBER", "")
        env = {
            **os.environ,
            "PATH": f"{tmp_path}:{os.environ['PATH']}",
            "COMMAND_LOG": str(tmp_path / "commands.jsonl"),
            "RUNNER_TEMP": str(tmp_path),
            "NPM_PROJECT": "docs/site",
            "BASE_BRANCH": "main",
            "PR_BRANCH": PUBLISH["env"]["PR_BRANCH"],
            "PR_TITLE": PUBLISH["env"]["PR_TITLE"],
            "PR_FOOTER": "Review validation before merging.",
            "EXPECTED_HEAD": "",
            "AUDIT_SHA": "audit-sha",
            "AUDIT_COMMIT_AVAILABLE": "1",
            "FETCH_STATUS": "0",
            "BASE_FETCH_STATUS": "0",
            "CHECKOUT_STATUS": "0",
            "DEPENDENCY_DIFF_STATUS": "0",
            "HAS_CHANGES": "1",
            "PUSH_STATUS": "0",
            "PR_NUMBER": "",
            "PR_LIST_JSON": json.dumps(
                [{"number": int(number), "isCrossRepository": False}] if number else []
            ),
            **overrides,
        }
        result = subprocess.run(
            ["bash", "-c", step["run"]],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
        )
        commands = [
            json.loads(line)
            for line in (tmp_path / "commands.jsonl").read_text().splitlines()
        ]
        return result, commands

    def invoke(**overrides):
        return run_step(PUBLISH, **overrides)

    def verify(**overrides):
        return run_step(VERIFY, **overrides)

    return SimpleNamespace(publish=invoke, verify=verify)


@pytest.mark.parametrize("same_repository", [False, True])
def test_publisher_ignores_fork_pr_with_matching_branch(publisher, same_repository):
    pull_requests = [{"number": 67, "isCrossRepository": True}]
    if same_repository:
        pull_requests.append({"number": 42, "isCrossRepository": False})
    result, commands = publisher.publish(PR_LIST_JSON=json.dumps(pull_requests))
    assert result.returncode == 0, result.stderr
    assert not any("67" in command for command in commands)
    if same_repository:
        assert any(command[:4] == ["gh", "pr", "edit", "42"] for command in commands)
        assert not any(command[:3] == ["gh", "pr", "create"] for command in commands)
    else:
        assert any(command[:3] == ["gh", "pr", "create"] for command in commands)
        assert not any(command[:3] == ["gh", "pr", "edit"] for command in commands)


@pytest.mark.parametrize("existing", [False, True])
def test_publisher_creates_or_updates_one_regular_pr(publisher, tmp_path, existing):
    result, commands = publisher.publish(
        EXPECTED_HEAD="previous-head" if existing else "",
        PR_NUMBER="42" if existing else "",
    )
    assert result.returncode == 0, result.stderr
    branch = "maintenance/dependency-audit"
    assert [
        "git",
        "add",
        "--",
        "docs/site/package.json",
    ] in commands
    assert [
        "git",
        "add",
        "--",
        "docs/site/pnpm-lock.yaml",
        "docs/site/pnpm-workspace.yaml",
    ] in commands
    assert len([command for command in commands if command[:2] == ["git", "add"]]) == 2
    push = next(command for command in commands if command[:2] == ["git", "push"])
    expected_head = "previous-head" if existing else ""
    assert push == [
        "git",
        "push",
        f"--force-with-lease=refs/heads/{branch}:{expected_head}",
        "origin",
        f"HEAD:refs/heads/{branch}",
    ]
    pr_write = next(
        command
        for command in commands
        if command[:2] == ["gh", "pr"] and command[2] in ("create", "edit")
    )
    if existing:
        assert pr_write[:4] == ["gh", "pr", "edit", "42"]
    else:
        assert pr_write[:3] == ["gh", "pr", "create"]
        assert "--draft" not in pr_write
        assert pr_write[pr_write.index("--head") + 1] == branch
        assert pr_write[pr_write.index("--base") + 1] == "main"
    assert not any(command[:3] == ["gh", "pr", "ready"] for command in commands)
    assert (tmp_path / "dependency-audit-pr.md").read_text() == (
        "## Security findings and fixes\n\n$(never-execute)\n\n"
        "Review validation before merging.\n"
    )


@pytest.mark.parametrize(
    "overrides,expected_status", [({"HAS_CHANGES": "0"}, 0), ({"PUSH_STATUS": "1"}, 1)]
)
def test_publisher_does_not_open_pr_without_successful_push(
    publisher, overrides, expected_status
):
    result, commands = publisher.publish(**overrides)
    assert result.returncode == expected_status
    assert not any(
        command[:2] == ["gh", "pr"] and command[2] in ("create", "edit", "ready")
        for command in commands
    )


def test_no_dependency_changes_updates_existing_report_without_commit(
    publisher, tmp_path
):
    result, commands = publisher.publish(HAS_CHANGES="0", PR_NUMBER="42")
    assert result.returncode == 0, result.stderr
    assert any(command[:4] == ["gh", "pr", "edit", "42"] for command in commands)
    assert not any(
        command[:2] in (["git", "commit"], ["git", "push"]) for command in commands
    )
    assert (
        "existing PR branch was left unchanged"
        in (tmp_path / "dependency-audit-pr.md").read_text()
    )


def test_publisher_stops_before_publication_when_dependency_state_is_stale(publisher):
    result, commands = publisher.verify(DEPENDENCY_DIFF_STATUS="1")
    assert result.returncode == 1
    assert "changed since audit-sha" in result.stdout
    assert not any(command[:2] == ["git", "add"] for command in commands)
    assert not any(
        command[:2] in (["git", "commit"], ["git", "push"]) for command in commands
    )
    assert not any(command[0] == "gh" for command in commands)


def test_publisher_stops_when_dependency_comparison_fails(publisher):
    result, commands = publisher.verify(DEPENDENCY_DIFF_STATUS="2")
    assert result.returncode == 1
    assert "Unable to compare" in result.stdout
    assert not any(command[:2] == ["git", "add"] for command in commands)
    assert not any(command[0] == "gh" for command in commands)


def test_publisher_stops_when_triggering_revision_cannot_be_fetched(publisher):
    result, commands = publisher.verify(AUDIT_COMMIT_AVAILABLE="0", FETCH_STATUS="1")
    assert result.returncode == 1
    assert "Unable to fetch the triggering audit revision" in result.stdout
    assert ["git", "fetch", "--no-tags", "origin", "audit-sha"] in commands
    assert not any(command[:2] == ["git", "add"] for command in commands)


def test_publisher_stops_when_triggering_revision_remains_unresolved(publisher):
    result, commands = publisher.verify(AUDIT_COMMIT_AVAILABLE="0", FETCH_STATUS="0")
    assert result.returncode == 1
    assert "could not be resolved" in result.stdout
    assert not any(command[:2] == ["git", "add"] for command in commands)


def test_publisher_allows_unrelated_default_branch_advance(publisher):
    result, commands = publisher.verify(DEPENDENCY_DIFF_STATUS="0")
    assert result.returncode == 0, result.stderr
    assert commands[:2] == [
        ["git", "fetch", "--no-tags", "origin", "main:refs/remotes/origin/main"],
        ["git", "checkout", "--detach", "refs/remotes/origin/main"],
    ]
    assert any(command[:3] == ["git", "diff", "--quiet"] for command in commands)


@pytest.mark.parametrize("failure", ["BASE_FETCH_STATUS", "CHECKOUT_STATUS"])
def test_publisher_stops_when_default_branch_refresh_fails(publisher, failure):
    result, commands = publisher.verify(**{failure: "2"})
    assert result.returncode == 2
    assert not any(command[:2] == ["git", "diff"] for command in commands)
    assert not any(command[0] == "gh" for command in commands)


def test_both_jobs_start_at_the_same_immutable_revision():
    for job in ("audit", "pull-request"):
        checkout = WORKFLOW["jobs"][job]["steps"][0]
        assert checkout["with"]["ref"] == "${{ github.sha }}"
    assert (
        VERIFY["env"]["BASE_BRANCH"] == "${{ github.event.repository.default_branch }}"
    )
    assert (
        PUBLISH["env"]["BASE_BRANCH"] == "${{ github.event.repository.default_branch }}"
    )


def test_workflow_uses_only_github_owned_actions():
    text = (
        Path(__file__).parents[1] / ".github/workflows/dependency-audit.yml"
    ).read_text()
    pins = {
        "actions/checkout": "3d3c42e5aac5ba805825da76410c181273ba90b1",
        "actions/setup-node": "820762786026740c76f36085b0efc47a31fe5020",
        "actions/setup-python": "5fda3b95a4ea91299a34e894583c3862153e4b97",
        "actions/upload-artifact": "330a01c490aca151604b8cf639adc76d48f6c5d4",
        "actions/download-artifact": "018cc2cf5baa6db3ef3c5f8a56943fffe632ef53",
    }
    for action, pin in pins.items():
        assert f"{action}@{pin}" in text
        assert f"{pin}  # v" in text
    for job in WORKFLOW["jobs"].values():
        for step in job["steps"]:
            if "uses" in step:
                assert step["uses"].startswith("actions/")


def test_dependency_state_check_precedes_artifact_download():
    steps = WORKFLOW["jobs"]["pull-request"]["steps"]
    verify_index = steps.index(VERIFY)
    download_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("uses", "").startswith("actions/download-artifact@")
    )
    assert verify_index < download_index
    assert VERIFY["env"]["AUDIT_SHA"] == "${{ github.sha }}"
    assert "git add" not in VERIFY["run"]
