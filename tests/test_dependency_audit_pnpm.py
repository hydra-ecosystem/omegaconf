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


def test_workflow_limits_credentials_and_calls_one_pinned_integration():
    root = Path(__file__).parents[1]
    workflow = yaml.safe_load(
        (root / ".github/workflows/dependency-audit.yml").read_text()
    )
    assert workflow["permissions"] == {"contents": "read"}
    auditor, publisher = workflow["jobs"]["audit"], workflow["jobs"]["pull-request"]
    assert auditor["permissions"] == {"contents": "read", "issues": "write"}
    assert "secrets" not in auditor
    assert publisher["permissions"] == {"contents": "write", "pull-requests": "write"}
    assert auditor["uses"].rsplit("@", 1)[1] == publisher["uses"].rsplit("@", 1)[1]
    assert auditor["uses"].split("@", 1)[0].endswith("/node-audit.yml")
    assert publisher["uses"].split("@", 1)[0].endswith("/node-publish.yml")
    assert (
        publisher["with"]["validation-passed"]
        == "${{ needs.audit.outputs.validation_passed }}"
    )
    assert set(publisher["secrets"]) == {"app-private-key"}
    deploy = yaml.safe_load((root / ".github/workflows/deploy-docs.yml").read_text())
    events = deploy.get("on", deploy.get(True))
    for event in ("push", "pull_request"):
        assert ".github/node-maintenance.json" in events[event]["paths"]
        assert ".github/workflows/dependency-audit.yml" in events[event]["paths"]
