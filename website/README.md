# Documentation site

Dependency vulnerabilities follow the
[best-effort maintenance policy](../.github/dependency-audit.md).

The Docusaurus site is published at
<https://hydra-ecosystem.github.io/omegaconf/>. Its navigation starts with
ordinary configs, then covers interpolation and resolvers before structured
configs. It includes task pages, an API overview, and generated symbol details
for two versions: 2.3.1 at `/omegaconf/docs/` and the current 2.4 prerelease at
`/omegaconf/docs/next/`.

Use Node 24 (recorded in `.node-version`) and the pnpm version pinned in
`package.json`. From the repository root, install the Python generator and site
packages:

```sh
.venv/bin/python -m pip install -r website/requirements.txt
cd website
corepack enable
corepack pnpm install --frozen-lockfile
corepack pnpm run build
```

The pnpm workspace policy delays new package releases by 10 days, blocks exotic
dependency sources, and requires explicit dependency build-script approvals.
Exact-version exceptions preserve already-locked dependencies during migration;
future versions remain subject to the delay. Security overrides live in
`pnpm-workspace.yaml`.

The generated API pages are versioned snapshots. To regenerate or check the
current 2.4 page from this checkout, run from `website/`:

```sh
../.venv/bin/python scripts/generate_api.py --source .. --version 2.4.0rc1 --output docs/reference/python-api/omegaconf.md
../.venv/bin/python scripts/generate_api.py --source .. --version 2.4.0rc1 --output docs/reference/python-api/omegaconf.md --check
```

The frozen 2.3 page was generated from the PyPI `omegaconf==2.3.1` source
distribution, SHA-256 `e5e7de64aeebeddaf8e6d3f7a783b32ac2a01c0fbd9c878012caecb891a1f42a`.
To check it, download and unpack that release outside this repository, then
point `--source` at the unpacked `omegaconf-2.3.1` directory, with
`--version 2.3.1` and
`--output versioned_docs/version-2.3/reference/python-api/omegaconf.md --check`.
The generator checks the source version so a later checkout cannot silently
replace the 2.3 API.

## Example and API checks

CI runs selected examples directly from the Markdown pages and checks both
generated API snapshots before building or deploying the site. It watches
Python source and validation dependencies as well as website changes.

The selected pages cover the first config, merging, interpolation, YAML
conversion, structured configs, custom resolvers, and the 2.4 tuple migration.
Each page runs in its own process; its example blocks share Python state.
Displayed output is compared exactly, with ordinary doctest directives such
as `# doctest: +ELLIPSIS` available when necessary. Failures name the version,
page, and source line.

Run these commands from the repository root, using a Python 3.10 environment:

```sh
.venv/bin/python -m pip install -e . -r website/requirements.txt pytest attrs
.venv/bin/python website/scripts/test_examples.py --docs-version next
.venv/bin/python -m pytest tests/test_website_examples.py -q
version=$(sed -n 's/^__version__ = "\(.*\)"/\1/p' omegaconf/version.py)
.venv/bin/python website/scripts/generate_api.py \
  --source . --version "$version" \
  --output website/docs/reference/python-api/omegaconf.md --check
```

Run 2.3 checks in a separate environment to prevent importing the current
checkout. Download the source archive with the following commands, verify
its SHA-256 against the value above, and then unpack it:

```sh
docs23_dir=$(mktemp -d)
python3.10 -m venv "$docs23_dir/venv"
"$docs23_dir/venv/bin/python" -m pip install \
  'omegaconf==2.3.1' -r website/requirements.txt
"$docs23_dir/venv/bin/python" -m pip download \
  --no-deps --no-binary=:all: 'omegaconf==2.3.1' --dest "$docs23_dir"
shasum -a 256 "$docs23_dir/omegaconf-2.3.1.tar.gz"
tar -xzf "$docs23_dir/omegaconf-2.3.1.tar.gz" -C "$docs23_dir"
"$docs23_dir/venv/bin/python" website/scripts/test_examples.py \
  --docs-version 2.3
"$docs23_dir/venv/bin/python" website/scripts/generate_api.py \
  --source "$docs23_dir/omegaconf-2.3.1" --version 2.3.1 \
  --output website/versioned_docs/version-2.3/reference/python-api/omegaconf.md \
  --check
```

The runner rejects a mismatched installed OmegaConf version. The API generator
also checks the source version. `--check` fails on drift without rewriting the
committed page; regenerate deliberately with the same command minus `--check`.
The generator requirements pin Black because griffe2md uses it to wrap signatures.

To run one page, add `--page path/to/page.md`. Python fences on selected pages
must contain `>>>` examples. Use `python doctest-setup` for plain Python setup
that later blocks need, or `python doctest-skip` to explicitly exclude a block
that is not intended to execute. Line-highlighting metadata remains supported.
Add pages to `PAGES` in `scripts/test_examples.py` to expand coverage.

The local search plugin builds separate indexes for the stable and prerelease
routes. GitHub Actions builds pull requests and publishes changes from `main`
to GitHub Pages. Redirects, canonical-link cutover, and final reader review are
still pending; Read the Docs remains the canonical documentation until those
steps are complete.
