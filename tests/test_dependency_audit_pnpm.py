import json
from pathlib import Path

import yaml


def test_workspace_classifies_platform_specific_build_scripts():
    root = Path(__file__).parents[1]
    config = json.loads((root / ".github/node-maintenance.json").read_text())
    policy = yaml.safe_load(
        (root / config["directory"] / "pnpm-workspace.yaml").read_text()
    )
    assert policy["strictDepBuilds"] is True
    assert policy["allowBuilds"]["fsevents"] is False


def test_workflow_calls_coordinator_with_expected_permissions_and_filtered_pushes():
    root = Path(__file__).parents[1]
    workflow = yaml.safe_load(
        (root / ".github/workflows/dependency-audit.yml").read_text()
    )
    assert workflow["permissions"] == {"contents": "read"}
    assert set(workflow["jobs"]) == {"maintenance"}
    coordinator = workflow["jobs"]["maintenance"]
    assert coordinator["uses"] == (
        "hydra-ecosystem/github-actions/.github/workflows/node-maintenance.yml@v2"
    )
    assert coordinator["permissions"] == {
        "contents": "write",
        "pull-requests": "write",
        "issues": "write",
        "actions": "read",
        "checks": "read",
    }
    assert coordinator["with"]["audit-kind"] == "${{ inputs.audit-kind || 'auto' }}"
    assert (
        coordinator["with"]["app-client-id"] == "${{ vars.NODE_AUDIT_APP_CLIENT_ID }}"
    )
    assert coordinator["secrets"] == {
        "app-private-key": "${{ secrets.NODE_AUDIT_APP_PRIVATE_KEY }}"
    }
    events = workflow.get("on", workflow.get(True))
    assert events["push"] == {
        "branches": ["main"],
        "paths": [
            "**/pnpm-lock.yaml",
            "**/package-lock.json",
            ".github/node-maintenance.json",
            "**/.nvmrc",
            "**/.node-version",
        ],
    }
    assert workflow["concurrency"] == {
        "group": "dependency-audit",
        "cancel-in-progress": False,
        "queue": "max",
    }
    repair = yaml.safe_load(
        (root / ".github/workflows/dependency-repair.yml").read_text()
    )
    assert repair["permissions"] == {"contents": "read"}
    events = repair.get("on", repair.get(True))
    assert set(events) == {"workflow_dispatch"}
    inputs = {
        "request-id",
        "pull-request",
        "expected-head",
        "expected-base",
        "selections",
    }
    assert set(events["workflow_dispatch"]["inputs"]) == inputs
    for specification in events["workflow_dispatch"]["inputs"].values():
        assert specification["required"] is True
        assert specification["type"] == "string"
    assert set(repair["jobs"]) == {"repair"}
    caller = repair["jobs"]["repair"]
    assert caller["uses"] == (
        "hydra-ecosystem/github-actions/.github/workflows/node-repair.yml@v2"
    )
    assert caller["permissions"] == {
        "contents": "write",
        "pull-requests": "write",
        "actions": "read",
        "checks": "read",
    }
    assert caller["with"] == {
        name: "${{ inputs['" + name + "'] }}" for name in inputs - {"selections"}
    } | {"selections": "${{ inputs.selections }}"}
    deploy = yaml.safe_load((root / ".github/workflows/deploy-docs.yml").read_text())
    events = deploy.get("on", deploy.get(True))
    for event in ("push", "pull_request"):
        assert ".github/node-maintenance.json" in events[event]["paths"]
        assert ".github/workflows/dependency-audit.yml" in events[event]["paths"]
