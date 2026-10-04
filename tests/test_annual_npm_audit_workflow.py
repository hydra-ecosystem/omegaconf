import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

WORKFLOW = yaml.safe_load(
    (Path(__file__).parents[1] / ".github/workflows/annual-npm-audit.yml").read_text()
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
    elif args[0] == 'diff':
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
    (tmp_path / "annual-npm-audit-pr.md").write_text(
        "## Security findings and fixes\n\n$(never-execute)\n"
    )

    def invoke(**overrides):
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
            "HAS_CHANGES": "1",
            "PUSH_STATUS": "0",
            "PR_NUMBER": "",
            "PR_LIST_JSON": json.dumps(
                [{"number": int(number), "isCrossRepository": False}] if number else []
            ),
            **overrides,
        }
        result = subprocess.run(
            ["bash", "-c", PUBLISH["run"]],
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

    return invoke


@pytest.mark.parametrize("same_repository", [False, True])
def test_publisher_ignores_fork_pr_with_matching_branch(publisher, same_repository):
    pull_requests = [{"number": 67, "isCrossRepository": True}]
    if same_repository:
        pull_requests.append({"number": 42, "isCrossRepository": False})
    result, commands = publisher(PR_LIST_JSON=json.dumps(pull_requests))
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
    result, commands = publisher(
        EXPECTED_HEAD="previous-head" if existing else "",
        PR_NUMBER="42" if existing else "",
    )
    assert result.returncode == 0, result.stderr
    branch = "maintenance/annual-npm-audit"
    assert [
        "git",
        "add",
        "--",
        "docs/site/package.json",
        "docs/site/package-lock.json",
    ] in commands
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
    assert (tmp_path / "annual-npm-audit-pr.md").read_text() == (
        "## Security findings and fixes\n\n$(never-execute)\n\n"
        "Review validation before merging.\n"
    )


@pytest.mark.parametrize(
    "overrides,expected_status", [({"HAS_CHANGES": "0"}, 0), ({"PUSH_STATUS": "1"}, 1)]
)
def test_publisher_does_not_open_pr_without_successful_push(
    publisher, overrides, expected_status
):
    result, commands = publisher(**overrides)
    assert result.returncode == expected_status
    assert not any(
        command[:2] == ["gh", "pr"] and command[2] in ("create", "edit", "ready")
        for command in commands
    )


def test_no_dependency_changes_updates_existing_report_without_commit(
    publisher, tmp_path
):
    result, commands = publisher(HAS_CHANGES="0", PR_NUMBER="42")
    assert result.returncode == 0, result.stderr
    assert any(command[:4] == ["gh", "pr", "edit", "42"] for command in commands)
    assert not any(
        command[:2] in (["git", "commit"], ["git", "push"]) for command in commands
    )
    assert (
        "existing PR branch was left unchanged"
        in (tmp_path / "annual-npm-audit-pr.md").read_text()
    )


def test_workflow_uses_only_github_owned_actions():
    for job in WORKFLOW["jobs"].values():
        for step in job["steps"]:
            if "uses" in step:
                assert step["uses"].startswith("actions/")
