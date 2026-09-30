# Documentation site

The Docusaurus site is published at
<https://hydra-ecosystem.github.io/omegaconf/>. Its navigation starts with
ordinary configs, then covers interpolation and resolvers before structured
schemas. It includes task pages, an API overview, and generated symbol details
for two versions: 2.3.1 at `/omegaconf/docs/` and the current 2.4 prerelease at
`/omegaconf/docs/next/`.

From the repository root, install the pinned Python generator and site packages:

```sh
.venv/bin/python -m pip install -r website/requirements.txt
cd website
npm ci
npm run build
```

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

The copy-and-paste examples in every hand-written Markdown page are tested
directly from their source files. Run the 2.4 examples from the repository
root (the generated symbol pages are excluded):

```sh
find website/docs -name '*.md' ! -path '*/reference/python-api/*' -print0 \
  | xargs -0 .venv/bin/python -m doctest
```

Run the 2.3 examples with the working directory set to an unpacked
`omegaconf==2.3.1` source distribution, using absolute paths to
`website/versioned_docs/version-2.3/`. That source requires
`antlr4-python3-runtime==4.9.*`. Testing 2.3 pages against the current
checkout would miss version-specific mistakes. For example:

```sh
find /absolute/path/to/website/versioned_docs/version-2.3 -name '*.md' \
  ! -path '*/reference/python-api/*' -print0 \
  | xargs -0 python -m doctest
```

The local search plugin builds separate indexes for the stable and prerelease
routes. GitHub Actions builds pull requests and publishes changes from `main`
to GitHub Pages. Redirects, canonical-link cutover, and final reader review are
still pending; Read the Docs remains the canonical documentation until those
steps are complete.
