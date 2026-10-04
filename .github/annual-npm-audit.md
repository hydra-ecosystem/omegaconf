# Annual documentation dependency maintenance

Dependency vulnerabilities in the designated Docusaurus npm project are accepted
between annual maintenance reviews, at all severities. Each deployment receives
one best-effort dependency upgrade drive per year. These findings do not trigger
out-of-cycle remediation. This is an accepted-risk policy, not a claim that every
advisory is incorrect or that the build environment is immune to compromise.
Dependencies outside the designated documentation project retain their existing
security policy.

## Annual umbrella PR

The `Annual npm dependency audit` workflow runs on January 30 at 02:00 UTC and
can also be run manually. It updates one fixed branch,
`maintenance/annual-npm-audit`, so reruns update an existing umbrella PR.

The npm audit script proposes the latest stable direct dependencies, including
major versions, resolves the lockfile, attempts compatible transitive fixes
without `--force`, and tries installation and the project's `build` script.
Overrides, peer constraints, and nonstandard version specifiers remain for
manual review. An unsuccessful upgrade resolution restores the original files.
Unresolved findings and failed installation/build checks are reported explicitly;
they do not prevent creation of a draft PR. The timestamped
`DEPENDENCY-AUDIT.md` ensures an audit-only PR is possible even with no upgrades.

The audit job has read-only repository permissions. A separate job publishes only
the manifest, lockfile, and report. Upgrades are never merged automatically.
The workflow uses only GitHub-owned actions; the runner's Git and GitHub CLI
create or update the draft PR without a third-party PR action.
The audit does not certify that every vulnerability has been fixed. Normal PR
validation and human review are still required before merging.

## GitHub activation

The workflow becomes scheduled after it reaches the default branch. In
**Settings → Actions → General → Workflow permissions**, enable **Allow GitHub
Actions to create and approve pull requests**. The workflow requests PR creation
permission but does not approve PRs. GitHub may require a maintainer to approve
validation workflows on its generated PRs.

For dormant public repositories, GitHub can disable scheduled workflows after
60 days without repository activity. Re-enable the workflow or use its manual
trigger during the annual review. See
[GitHub's scheduling behavior](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

To suppress alerts and notifications before they are sent, create an enabled
repository-level rule under **Settings → Advanced Security → Dependabot rules**:

- Name: `Annual documentation dependency maintenance`
- Ecosystem: `npm`
- Manifest path: `website/package-lock.json`
- All severities, both scopes, and any patch availability
- Action: dismiss indefinitely

This rule applies to existing and future matching alerts. Dismissed alerts remain
available for review and can reopen when advisory metadata changes. The annual
`npm audit` examines the lockfile independently of GitHub dismissal state.
GitHub's documented custom-rule setup uses the settings UI; its public Dependabot
REST API supports individual alert dismissal, not creation of these rules.

The scoped `ignore` entry in `dependabot.yml` suppresses automatic update PRs for
this npm project. Its required schedule does not schedule security updates.
The project's `.npmrc` disables routine npm installation audit messages; explicit
`npm audit --audit` remains available during annual review.

## Reuse in other repositories

Copy `.github/scripts/annual_npm_audit.py` and
`.github/workflows/annual-npm-audit.yml`. Change the workflow's `NPM_PROJECT`
fallback to your npm project directory and choose its annual cron date. The
project must have `package.json`, `package-lock.json`, and an npm `build` script.
The script requires Python, npm, and GNU `timeout`, which is included in the
workflow's Ubuntu runner. Timed-out commands terminate their process group,
including npm lifecycle and build children.

For a manual run, leave `directory` empty to use the workflow's configured
`NPM_PROJECT` fallback, or enter a directory to override it for that run.

Apply this policy to that deployment, add `audit=false` to its project-local
`.npmrc`, and merge the relevant `ignore` entry into its existing Dependabot
configuration. Create the suppression rule using that project's exact lockfile
path and enable workflow PR creation. Other repositories and dependency
ecosystems are not changed by copying the implementation.

After activation, trigger the workflow manually once in each project for its
initial upgrade drive; subsequent scheduled runs occur annually on January 30.

Run an audit locally with:

```sh
python3 .github/scripts/annual_npm_audit.py --directory website
```

This command modifies the selected manifest and lockfile and installs and builds
dependencies. Use an isolated checkout when evaluating upgrade candidates.
