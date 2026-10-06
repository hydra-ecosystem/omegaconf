# Documentation dependency maintenance

Dependency vulnerabilities in the designated Docusaurus npm project are accepted
between maintenance reviews, at all severities. Each deployment receives
best-effort dependency upgrade drives at its configured cadence or on demand.
These findings do not trigger out-of-cycle remediation. This is an accepted-risk
policy, not a claim that every
advisory is incorrect or that the build environment is immune to compromise.
Dependencies outside the designated documentation project retain their existing
security policy.

## Dependency umbrella PR

The `Documentation dependency audit` workflow runs on January 30 at 02:00 UTC and
can also be run manually. It updates one fixed branch,
`maintenance/dependency-audit`, so reruns update an existing umbrella PR.

The helper supports npm and pnpm. OmegaConf uses its pinned pnpm toolchain.
It first attempts compatible security fixes without `--force`, using pnpm's
`audit --fix=update --audit-level info` rather than adding blanket security overrides.
When that command leaves findings, it regenerates the lockfile within the
existing manifest constraints using isolated temporary module metadata. This
avoids pnpm restoring vulnerable pins during automatic peer resolution without
removing the project's installed dependencies. The regeneration also disables
pnpm's optimistic repeat-install shortcut, which can restore the stale lockfile.
Failed regeneration restores the
preceding security-fix proposal.
JSON audit reports also use `--audit-level info`, so informational advisories
remain visible alongside every higher severity.
It then proposes the latest stable direct dependencies, including major versions,
resolves the lockfile, retries compatible security fixes, and tries installation
and the project's `build` script.
Overrides, peer constraints, and nonstandard version specifiers remain for
manual review. An unsuccessful stable upgrade resolution restores the files from
the initial security fix attempt, preserving those fixes and pnpm workspace
policy together. Security fixes may add exact patched-version release-age
exceptions; the 10-day rule remains in force for future releases.
Every command preserves the complete workspace policy. Only an individual
security-fix command may add exact-version release-age exceptions for packages
newly present across that invocation's complete normalized lockfile package set.
Existing exclusions must remain, including when pnpm combines exact versions
with `||`; previously installed versions and versions introduced by an earlier
stable resolution do not qualify. Unused new exact-version exceptions are
removed while preserving resolved dependency changes; broad new rules or other
policy mutations are rejected. Rejected changes restore the manifest,
lockfile, and workspace together and identify the offending operation.
Validation restores the frozen proposal if installation, build, or audit changes
its manifest, lockfile, or workspace policy, and reports the failure explicitly.
Version lookups also preserve the exact package-file bytes.
Unresolved findings and failed installation/build checks are reported explicitly;
they do not prevent creation of a PR with dependency changes.

The PR body contains the audit report. Security-related changes and before/after
findings appear first, including locked versions, severity, affected ranges,
and advisory links. Other stable dependency upgrades follow. Remaining findings
are grouped by distinct advisory; full before/after chains are collapsed.
The report distinguishes propagated findings in parent packages from the
underlying advisories; package counts are not distinct advisory counts or proof
of exploitable paths. An npm fix candidate is not a guarantee that a published
fix exists for every advisory.
Each pnpm advisory retains its own affected versions; the combined severity and
ranges describe the package summary only. Missing, malformed, or inconsistent
advisory counts and details are reported as unavailable audit evidence, including
in the full findings, rather than as a clean audit.
Patch publication is checked against registry versions. The report distinguishes
unpublished patch ranges, published patches blocked by existing parent dependency
constraints, and metadata that could not be verified. A registry's claimed patched
range alone is not proof that a patch was released.

The report is also available in the Actions run summary and as an artifact. Its
temporary file lives in the runner's temporary directory and is never committed
to the npm project or the repository.
If there are no dependency changes, an existing umbrella PR receives the updated
report without a commit or push. If none exists, no new PR is opened; the report
remains in the Actions run summary and artifact.
An updated report explicitly notes when the existing PR branch was left unchanged.

The audit job has read-only repository permissions. A separate job publishes only
the manifest, lockfile, and pnpm workspace policy and puts the report in the PR
body. It refuses publication if those files differ between the audit revision
and the current default branch; rerun from the current default branch in that
case. Both jobs initially check out the immutable triggering revision. Before
downloading artifacts, the publisher fetches and checks out the current default
branch, then compares the selected dependency inputs. Fetch, checkout, and
comparison failures prevent publication. Unrelated default-branch changes are
retained in the proposed branch. Audit workflow actions use reviewed full
commit SHA pins.
Upgrades are never merged automatically.
The workflow uses only GitHub-owned actions; the runner's Git and GitHub CLI
create or update the PR without a third-party PR action. New umbrella PRs are
ready for review; reruns do not change an existing PR's draft status.
The audit does not certify that every vulnerability has been fixed. Normal PR
validation and human review are still required before merging.

## GitHub activation

The workflow becomes scheduled after it reaches the default branch. In
**Settings → Actions → General → Workflow permissions**, enable **Allow GitHub
Actions to create and approve pull requests**. The workflow requests PR creation
permission but does not approve PRs. PRs created or updated with `GITHUB_TOKEN`
trigger checks that require maintainer approval. Select **Approve workflows to
run** on the PR before merging. See
[GitHub's token-triggered workflow rules](https://docs.github.com/en/actions/concepts/security/github_token#when-github_token-triggers-workflow-runs).

For dormant public repositories, GitHub can disable scheduled workflows after
60 days without repository activity. Re-enable the workflow or use its manual
trigger during the maintenance review. See
[GitHub's scheduling behavior](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

To suppress alerts and notifications before they are sent, create an enabled
repository-level rule under **Settings → Advanced Security → Dependabot rules**:

- Name: `Documentation dependency maintenance`
- Ecosystem: `npm`
- Manifest path: `website/pnpm-lock.yaml`
- All severities, both scopes, and any patch availability
- Action: dismiss indefinitely

This rule applies to existing and future matching alerts. Dismissed alerts remain
available for review and can reopen when advisory metadata changes. The explicit
`corepack pnpm audit` examines the lockfile independently of GitHub dismissal state.
GitHub's documented custom-rule setup uses the settings UI; its public Dependabot
REST API supports individual alert dismissal, not creation of these rules.

The scoped `ignore` entry in `dependabot.yml` suppresses automatic update PRs for
this npm project. Its required schedule does not schedule security updates.
The project's `.npmrc` disables routine npm installation audit messages; explicit
`npm audit --audit` and `corepack pnpm audit` remain available during maintenance review.
No pnpm advisory-ignore rules are added.

## Reuse in other repositories

Copy `.github/scripts/dependency_audit.py` and
`.github/workflows/dependency-audit.yml`. Change the workflow's `NPM_PROJECT`
value to your documentation project directory. Keep a distinct branch,
concurrency group, and artifact identity for each deployment in a repository.
The project must have `package.json`, a `build` script, and either
`package-lock.json` or `pnpm-lock.yaml` with a single-project
`pnpm-workspace.yaml`. A shared multi-project lockfile requires a scope plan.
The helper requires Python with PyYAML, the project's package manager, and GNU
`timeout`, included in the workflow's Ubuntu runner. Timed-out commands terminate
their process group, including lifecycle and build children.

Manual runs use the configured `NPM_PROJECT` and triggering revision. Scheduled
runs use the default branch. The publisher always targets the default branch
and checks that the selected dependency files still match the triggering state.
Adapting to npm also requires changing artifact, publication, and comparison
paths to `package-lock.json` and removing the pnpm workspace path.

Apply this policy to that deployment, add `audit=false` to its project-local
`.npmrc`, and merge the relevant `ignore` entry into its existing Dependabot
configuration. Create the suppression rule using that project's exact lockfile
path and enable workflow PR creation. Other repositories and dependency
ecosystems are not changed by copying the implementation.

After activation, trigger the workflow manually once in each project for its
initial upgrade drive. OmegaConf's scheduled runs remain January 30; change the
workflow cron expression when adopting a different cadence.

Run an audit locally with:

```sh
python3 .github/scripts/dependency_audit.py --directory website --report /tmp/dependency-audit-pr.md
```

This command modifies the selected manifest and lockfile and installs and builds
dependencies. It writes the report to the explicitly selected temporary path.
Use an isolated checkout when evaluating upgrade candidates.
