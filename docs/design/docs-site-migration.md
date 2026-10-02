---
status: Draft
updated: 2026-09-30
summary: Rebuild the OmegaConf user documentation around reader tasks while migrating from Sphinx/Read the Docs to Docusaurus.
---

# OmegaConf documentation site

## Goal

Replace the Sphinx/Read the Docs site with a dedicated Docusaurus site and use
the move to make the documentation easier to learn and navigate. Preserve the
accuracy, API coverage, tested examples, and useful links of the existing
documentation. This is a documentation migration, not a change to OmegaConf's
behavior.

This document is the design stage. The site, content conversion, hosting, and
redirects belong to a subsequent implementation stage.

## Current state

The user-facing source is `docs/source/`, linked from `README.md`. Its seven
content pages are organized mainly by source file rather than by reader task:

| Page | Approximate size | Current role |
| --- | ---: | --- |
| `usage.rst` | 1,231 lines | Installation, creation, access, interpolation, merging, flags, utilities |
| `structured_config.rst` | 852 lines | Introductory and advanced structured config behavior |
| `custom_resolvers.rst` | 575 lines | Custom and built-in resolvers |
| `grammar.rst` | 258 lines | Interpolation language reference |
| `tuple_migration.rst` | 103 lines | Migration to tuple behavior in 2.4 |
| `yaml_aliases.rst` | 55 lines | YAML alias expansion limit |
| `api_reference.rst` | 30 lines | `OmegaConf`, utility functions, and `MISSING` via autodoc |

`nox -s docs` builds HTML with warnings treated as errors and runs Sphinx
doctests. The source contains 115 `doctest` directives, shared `testsetup`
blocks, tabs, RST cross-references, and included YAML files. The notebook
tutorial has a separate `nbval` check in `noxfile.py`. Moving text alone would
silently drop example execution and some cross-link guarantees.

## Content architecture proposal

The first prototype divided content by form (Concepts, Guides, Reference). That
forced a reader to jump between sections to complete a topic. The replacement
should organize explanations and examples by capability, after a short common
foundation. Teach interpolation in ordinary configs before introducing schemas;
typed interpolation behavior then builds on both topics.

| Section | Reader's question | Content boundary |
| --- | --- | --- |
| Start | How do I get a useful config running? | Install and one short, runnable first config. Introduce only the operations the example uses. |
| Work with configs | How do I create, inspect, change, combine, and exchange ordinary configs? | Container model, access and mutation, required/missing values, merge rules, YAML and Python conversion. Put CLI overrides, flags, and debugging recipes near the operations they use. Explain `None` as a value, without introducing typed optional fields. |
| Derive values | How do I refer to other values or compute them? | Node interpolation, relative/nested paths, lazy versus eager resolution, built-in and custom resolver calls. Put environment-input recipes here. Explain the shared expression syntax, while giving node references and resolvers distinct pages. |
| Define a schema | How do I declare and validate typed config data? | Structured configs, field types and defaults, optional fields, runtime validation and conversion, applying a schema to external input. Explain how typed fields validate interpolation results after both ideas are established. `Optional[T]` follows structured fields; it is not a synonym for `MISSING`. |
| Reference | What is the exact syntax or API contract? | Generated Python API, supported-type matrix, interpolation grammar, and precise operation options. Lookup pages do not repeat the learning narrative. |
| Upgrade | What changes when I adopt a newer release? | One 2.3-to-2.4 guide covering breaking changes and required updates, with collapsed tuple migration examples. |

The main reading path is **Start → Work with configs → Derive values → Define
a schema**. Interpolation and schemas can be used independently; this order
teaches plain-config behavior before its interaction with typed fields. Task
recipes live beside their underlying topic. Reference supports direct entry
from search. Within a section, introduce a term at its first use and move
advanced cases after a working basic example. Each page should answer one
reader question. Put two topics together only when they share a rule the
reader needs to understand at the same time.

Format multi-field and nested config examples over multiple lines so their
structure is visible. Show YAML as YAML rather than an escaped string when the
example is teaching its contents.

The landing page should show a short value proposition, a runnable example,
and direct routes for new users, existing users upgrading, and readers looking
for API details. The API reference can have its own navigation without
overwhelming the learning path.

### Proposed reading order

This is an outline of reader questions, not a commitment to one page per line.
Page boundaries should follow the explanation needed to answer each question.

1. **Start:** install; create, read, change, and merge one small config.
2. **Work with configs:** what containers and values are; how to access and
   update them; what missing means; how merges choose values; how to load,
   save, and export data.
3. **Derive values:** how node references work; relative and nested paths;
   what a resolver call is; built-in and custom resolvers; when resolution
   happens and what `OmegaConf.resolve()` changes.
4. **Define a schema:** how a dataclass or `attrs` class becomes a config;
   which field types and defaults are supported; when a field may be `None`;
   how validation and conversion work, including interpolation results; how
   to validate external data.

Task recipes and reference pages are linked from the relevant point in a
section, not inserted as prerequisites. For example, link to the grammar
reference after the first working interpolation example, and to the
supported-type matrix after the first structured config example. The exact
sidebar and URL changes follow review of this outline.

### Visual direction for the representative pages

Use a simple orange OmegaConf mark as the brand anchor, with a small config-tree
cue inspired by the OmegaFlow family logo. Pair white surfaces with dark ink
text and restrained orange highlights; keep the same hierarchy and contrast
in dark mode. Use system typefaces and local assets so
the site does not depend on external fonts or images. The home page should
put the purpose, a short working example, and clear stable/prerelease routes
in the first view. The first-config guide should have a visible learning path,
short steps, and code that remains readable on narrow screens.

The Python API needs an entry page organized by task, with links into generated
symbol details beneath `reference/python-api`. Generated signatures, parameters,
and warnings should have clear visual separation, while method headings remain
deep-linkable and searchable. Validate these three representative pages at
desktop and mobile widths before converting the remaining content.

### Implemented page tree

The WIP site uses the capability sections above. Existing page IDs stay in
place during this navigation change so current links remain valid; the paths
still contain `concepts/` and `guides/` until the redirect plan is ready.
Docusaurus adds the appropriate version route below `/docs/`.

| Section | Page IDs |
| --- | --- |
| Start | `get-started/install`, `get-started/first-config` |
| Work with configs | `concepts/configs-and-values`, `concepts/missing-values`, `guides/merge`, `guides/load-and-save`, `guides/command-line`, `guides/flags`, `guides/debugging` |
| Interpolation and resolvers | `concepts/interpolation`, `concepts/resolvers`, `reference/built-in-resolvers`, `guides/custom-resolvers` |
| Define a schema | `concepts/structured-configs`, `concepts/field-types`, `concepts/optional-fields`, `guides/schema-validation` |
| Reference | `reference/python-api`, `reference/operations`, `reference/types`, `reference/conversion`, `reference/grammar`, `reference/yaml-alias-limits` |
| Upgrade | `migration/2.4` |

`concepts/field-types` teaches container, Enum, and union annotations before
optional fields, with `Literal` added in 2.4. `reference/types` remains the
exact support matrix.

The generated Python API is part of the same versioned docs tree. It may emit
several pages beneath `reference/python-api`, but does not get an independent
version selector.

The Sphinx source-heading inventory and draft legacy-link map are below. Page
destinations reflect the WIP site, but old anchor coverage still needs a full
audit. Keep the old pages available while new destinations and redirects are
checked.

### Source-heading ownership

Every current substantive heading has a destination below, grouped when
adjacent headings share it. Former page titles become navigation
labels rather than separate pages. During conversion, record the old page and
anchor next to each resulting page/anchor and test the links that matter. The
title, overview, and indices in
`index.rst` become the new landing page; Docusaurus supplies its own search
and navigation rather than copying the Sphinx indices.

| Source | Current heading(s) | Destination page ID |
| --- | --- | --- |
| `usage.rst` | Installation | `get-started/install` |
| `usage.rst` | Creating; From a dictionary; Access | `get-started/first-config` |
| `usage.rst` | Empty; From a list; From a tuple; Access and manipulation; Manipulation | `concepts/configs-and-values` |
| `usage.rst` | From a YAML file; From a YAML string; Serialization; YAML flow style; Save/Load YAML file; Save/Load pickle file | `guides/load-and-save` |
| `usage.rst` | From a dot-list; From command line arguments | `guides/command-line` |
| `usage.rst` | From structured config | `concepts/structured-configs` |
| `usage.rst` | Default values | `concepts/configs-and-values` |
| `usage.rst` | Mandatory values | `concepts/missing-values` |
| `usage.rst` | Hashing | `reference/operations` |
| `usage.rst` | Variable interpolation; Config node interpolation; Nested interpolation | `concepts/interpolation` |
| `usage.rst` | Resolvers | `concepts/resolvers` |
| `usage.rst` | Built-in resolvers | `reference/built-in-resolvers` |
| `usage.rst` | Merging configurations; OmegaConf.merge(); Missing values in merge(); Union operator; OmegaConf.unsafe_merge() | `guides/merge` |
| `usage.rst` | Configuration flags; Read-only flag; Struct flag | `guides/flags` |
| `usage.rst` | Utility functions; OmegaConf.to_container; Using throw_on_missing; Using structured_config_mode; OmegaConf.structural_equality; OmegaConf.to_object; OmegaConf.resolve | `reference/operations` |
| `usage.rst` | OmegaConf.select; OmegaConf.can_select; OmegaConf.update; Key path escaping; OmegaConf.masked_copy; OmegaConf.is_missing; OmegaConf.is_interpolation; OmegaConf.{is_config, is_dict, is_list, is_tuple, is_sequence}; OmegaConf.missing_keys | `reference/operations` |
| `usage.rst` | Debugger integration | `guides/debugging` |
| `structured_config.rst` | Introduction; Static type checker support; Nesting structured configs | `concepts/structured-configs` |
| `structured_config.rst` | Simple types; Literal types; Lists; Tuples; Dictionaries; Nested dict and list annotations; Unions; Unions of container types | `reference/types` |
| `structured_config.rst` | Runtime type validation and conversion; Interpolations | `reference/conversion` |
| `structured_config.rst` | Other special features | `concepts/structured-configs` |
| `structured_config.rst` | Mandatory missing values | `concepts/missing-values` |
| `structured_config.rst` | Optional fields | `concepts/optional-fields` |
| `structured_config.rst` | Frozen classes | `guides/flags` |
| `structured_config.rst` | Merging with other configs; Using Metadata to Ignore Fields | `guides/schema-validation` |
| `custom_resolvers.rst` | Custom resolvers; Resolver annotation validation; Clearing/removing resolvers; clear_resolvers; clear_resolver | `guides/custom-resolvers` |
| `custom_resolvers.rst` | Built-in resolvers; oc.env; oc.create; oc.deprecated; oc.coerce; oc.decode; oc.select; oc.dict.{keys,value} | `reference/built-in-resolvers` |
| `grammar.rst` | Interpolation strings; Interpolation types; Element types; Escaped characters; Escaping in interpolation strings; Escaping in unquoted strings; Escaping in quoted strings | `reference/grammar` |
| `tuple_migration.rst` | What changed; Choosing the intended sequence type; Checking sequence types; Migration checklist | `migration/2.4#tuple-inputs-no-longer-become-mutable-lists` |
| `yaml_aliases.rst` | YAML Alias Limits; Details | `reference/yaml-alias-limits` |
| `api_reference.rst` | The OmegaConf API; module-level utilities; MISSING | `reference/python-api` |

The 2.4 upgrade guide describes breaking changes and contains collapsed
tuple migration examples. The old `migration/2.4-tuples` route redirects to
that section. `docs/notebook/Tutorial.ipynb` remains a separate linked tutorial
and retains its existing `nbval` check initially. The five small YAML source
files included by the RST pages move with their examples.

Avoid duplicating canonical rules across sections. For example, explain
conversion behavior once in Reference, then link to it from the
structured config and resolver guides. Examples may repeat only when needed
to make a task self-contained.

### Legacy documentation links

This inventory maps explicit anchors in the current Sphinx source to planned
Docusaurus destinations. It is not a redirect configuration: the new pages
still need a completeness review and the redirects have not been tested.
Keep the old Read the Docs pages live until the matching new pages and
redirects have been checked. Ordinary headings are assigned in the
source-heading ownership table above.

The current development docs use `/en/latest/`. Stable 2.3 links use
`/en/2.3_branch/`; their destinations will use `/docs/` until 2.4 becomes the
stable version. The table below maps the current 2.4 content under
`/docs/next/`. Before cutover, compare the 2.3 Sphinx anchors against its own
source; 2.4-only topics cannot be redirected into 2.3 documentation.

| Old `/en/latest/` path and anchor | Planned new `/docs/next/` path and anchor |
| --- | --- |
| `usage.html#creating` | `get-started/first-config` |
| `usage.html#save-and-load-pickle-file` | `guides/load-and-save#pickle` |
| `usage.html#interpolation` | `concepts/interpolation` |
| `usage.html#config-node-interpolation` | `concepts/interpolation` |
| `usage.html#nested-interpolation` | `concepts/interpolation#nested-references` |
| `usage.html#resolvers` | `concepts/resolvers` |
| `usage.html#read-only-flag` | `guides/flags#read-only` |
| `usage.html#struct-flag` | `guides/flags#struct` |
| `usage.html#keypath-escaping` | `reference/operations#key-paths` |
| `structured_config.html#structured-configs` | `concepts/structured-configs` |
| `structured_config.html#simple-types` | `reference/types#primitive-types` |
| `structured_config.html#structured-config-conversion` | `reference/conversion` |
| `structured_config.html#nesting-structured-configs` | `concepts/structured-configs#nested-structured-configs` |
| `structured_config.html#literal-types` | `reference/types#literal` |
| `structured_config.html#lists` | `reference/types#lists` |
| `structured_config.html#tuples` | `reference/types#tuples` |
| `structured_config.html#dictionaries` | `reference/types#dictionaries` |
| `structured_config.html#nested-dict-and-list-annotations` | `reference/types#nested-containers` |
| `structured_config.html#union-types` | `reference/types#unions` |
| `structured_config.html#other-special-features` | `concepts/structured-configs` |
| `structured_config.html#mandatory-missing-values` | `concepts/missing-values` |
| `structured_config.html#optional-fields` | `concepts/optional-fields` |
| `custom_resolvers.html#custom-resolvers` | `guides/custom-resolvers` |
| `custom_resolvers.html#oc-env` | `reference/built-in-resolvers#ocenv` |
| `custom_resolvers.html#oc-create` | `reference/built-in-resolvers#occreate` |
| `custom_resolvers.html#oc-deprecated` | `reference/built-in-resolvers#ocdeprecated` |
| `custom_resolvers.html#oc-coerce` | `reference/built-in-resolvers#occoerce` |
| `custom_resolvers.html#oc-decode` | `reference/built-in-resolvers#ocdecode` |
| `custom_resolvers.html#oc-select` | `reference/built-in-resolvers#ocselect` |
| `custom_resolvers.html#oc-dict-keys-values` | `reference/built-in-resolvers#ocdictkeys-and-ocdictvalues` |
| `custom_resolvers.html#clearing-resolvers` | `guides/custom-resolvers#remove-resolvers` |
| `custom_resolvers.html#clear-resolvers` | `guides/custom-resolvers#clear-all` |
| `custom_resolvers.html#clear-resolver` | `guides/custom-resolvers#clear-one` |
| `grammar.html#interpolation-strings` | `reference/grammar#interpolation-strings` |
| `grammar.html#element-types` | `reference/grammar#element-types` |
| `grammar.html#escaping-in-interpolation-strings` | `reference/grammar#escaping-in-interpolation-strings` |
| `tuple_migration.html#tuple-migration-24` | `migration/2.4#tuple-inputs-no-longer-become-mutable-lists` |
| `yaml_aliases.html#yaml-aliases` | `reference/yaml-alias-limits` |

Sphinx also generates anchors from every heading and API symbol, including
`api_reference.html#omegaconf.OmegaConf`-style links. Those need a second
inventory against the built HTML and generated API page. Redirecting a whole
old page to one new page would lose the meaning of deep links because the old
pages split across multiple destinations.

## Site and API generation

Use Docusaurus 3 and its docs content plugin for hand-written Markdown/MDX.
Keep the site source in this repository under `website/` so the content,
generated API input, and OmegaConf code can be reviewed together.
Generate Python API pages as a build input, then render those pages through
Docusaurus. The first candidate, `haystack-pydoc-tools`, was rejected in the
prototype: rendering all members failed on imported aliases, while filtering
to documented members omitted much of the 2.3 API and `MISSING`.

The prototype must verify coverage of the public surface in the current
`api_reference.rst`: all documented `OmegaConf` members, `II`, `SI`,
`flag_override`, `open_dict`, `read_write`, and `MISSING`. Inspect rendered
signatures, docstrings, type annotations, anchors, and links, including whether
undocumented but public members are accidentally filtered out. Include methods
with real Sphinx-style docstrings such as `OmegaConf.create()` and
`OmegaConf.clear_resolver()`; compare their rendered parameter fields, warnings,
and literals with the current API page. The public API is small enough to
convert those docstrings to the chosen generator's supported format where
needed. If that still cannot produce a sound reference, evaluate another
maintained generator before writing a custom one.

Keep generated files reproducible from pinned dependencies. The implementation
must decide whether to commit generated pages or build them in CI, with a drift
check if committed. Freeze each released version's API pages from that
version's source and never regenerate an older version from the current
checkout. Do not edit generated API pages by hand.

## Versions and URLs

Use Docusaurus versioning for the entire documentation tree, including the
generated API reference. The first launch includes 2.3 as the stable default
and a clearly labeled 2.4 prerelease version. When 2.4 is final, freeze its
docs and API pages from the 2.4 source and make it the stable default; 2.3
remains selectable. Snapshot by minor release, not every patch or release
candidate. A rebuild must never put signatures from one release beneath
another release's version label.

| Phase | Default docs route | Other version route |
| --- | --- | --- |
| Before 2.4 final | `/docs/...` serves 2.3 | `/docs/next/...` serves labeled 2.4 prerelease content |
| After 2.4 final | `/docs/...` serves 2.4 | `/docs/2.3/...` serves frozen 2.3 content |

Freeze generated API pages alongside the hand-written pages in each versioned
snapshot. The 2.3 import is generated from 2.3 source; the 2.4 prerelease is
generated from current 2.4 source and frozen when 2.4 becomes final.

Older versions can be ported to Docusaurus in a second phase. Keep their Read
the Docs pages online until each version has been migrated and its old URLs
have tested destinations. Do not retire the Read the Docs project as part of
the initial launch.

Before launch, create a source-to-destination URL and anchor map for the
versions being ported, especially README links, hard-coded links in API
docstrings, and links in release notes, issues, and Hydra documentation.
Test representative old page URLs and important deep links. Read the Docs can
redirect to an external domain; configure those redirects when a version moves,
while leaving older, unmigrated versions available there. Docusaurus redirects
only cover paths on the new site's own domain.

Host the site as the repository's GitHub Pages project site at
`https://hydra-ecosystem.github.io/omegaconf/`. Treat it as a preview until the
redirect inventory and reader review are complete; Read the Docs remains the
canonical documentation during that period. Search needs an explicit
Docusaurus integration that distinguishes documentation versions and finds
both guides and API symbols.

## Process and rollout

Review this design and its information architecture before starting the site
implementation. Use the prototype below to settle the generator, search, and
example-test choices, then update this document with those decisions before
converting the full documentation set.

1. Build a small Docusaurus prototype with a landing page, one representative
   guide, one reference page, generated API pages, and search. Inspect the
   output in a browser before converting the rest of the content. Verify
   Sphinx-style API docstrings or convert the few that need it.
   After validating the mechanics, design and review the site's visual system
   on these representative pages before using them as conversion templates.
2. Check the proposed heading ownership map against every source heading and
   record old-to-new page and anchor URLs for the versions being ported.
   Preserve critical deep links with redirects, aliases, or continued RTD pages.
3. Convert content in reader-path order: Start, Work with configs, Derive
   values, Define a schema, Reference, then Upgrade. Review examples and links
   as each section lands.
4. Keep the existing Sphinx checks working during conversion. Rely on the
   core tests for behavior, and choose a small set of copy-and-paste examples
   from the actual new pages for automated smoke checks: first config,
   structured config, interpolation/resolver, merge/serialization, and one 2.4
   migration case. The prototype must show how those rendered examples run.
   There is no requirement to port all 115 Sphinx doctests. Keep the notebook
   validation unless the notebook is deliberately retired.
5. Make the production Docusaurus build fail on broken internal links. Check
   generated API coverage and rendering, version routes, search, key redirects,
   smoke examples, and representative pages in a preview deployment.
6. Cut over the canonical links only after the new site passes those checks.
   Keep RTD available for unmigrated versions and old links. Remove Sphinx
   build machinery in a separate, reviewable cleanup after the new checks are
   in place; retire RTD only after the older-version migration and redirects.

## Acceptance criteria

- A new reader can complete the first-config path without traversing a long
  reference page.
- Every current user-facing heading has a destination in the page map, and
  the 2.4 migration guidance remains discoverable.
- The generated API reference covers at least the current explicitly documented
  public symbols, renders converted docstrings correctly, and uses the matching
  source snapshot for each version.
- Core tests pass; the selected examples from the new pages and the notebook
  have automated checks.
- Docusaurus labels and routes stable 2.3 and prerelease 2.4 correctly, with
  versioned API pages; older versions remain available on RTD until migrated.
- Important old URLs have tested destinations or remain live on RTD. An RTD
  version is not removed until its redirects to the new site work.
- Search returns relevant guide and API results within the selected version.
- The site builds reproducibly and fails CI on broken internal links.

## Decisions to close before full migration

1. Which older documentation versions to port in the second phase, after
   stable 2.3 and incoming 2.4.
2. Visual design and review of representative pages, API search, and the
   version switcher in a preview deployment.

API drift checks and selected page examples are wired into GitHub Actions for
both versions. Validation must pass before the site build and deployment.

Close these after the remaining content and link inventory, not from
appearance alone.

## Local prototype results

The Docusaurus site lives in `website/` and is published as a GitHub Pages
project site. It builds 2.3.1 at `/docs/` and 2.4.0rc1 at `/docs/next/` from
separate versioned documentation trees. The
2.3 API page was generated from the 2.3.1 PyPI source distribution, not the
current checkout. The 2.4 page was generated from the current source. Both
pages include the `OmegaConf` members, module helpers, and `MISSING`; the 2.4
page includes `typed_list`, while the 2.3 page does not. The source-version
check in `website/scripts/generate_api.py` guards against accidental
cross-version regeneration.

The second visual pass uses a simplified vector OmegaConf mark, white surfaces,
dark ink text, restrained orange highlights, and responsive layouts. The landing
page pairs a working example with paths to config work, derived values,
schemas, API lookup, and the 2.4 preview. The
first-config guide has short numbered steps. Each version has a task-based
Python API entry page leading to generated symbol details beneath
`reference/python-api/omegaconf`; this keeps the generated detail searchable
without making it the first page a reader sees. The generated page's contents
rail shows top-level symbols to avoid listing every method. The user requested
the quieter technical-docs direction and a logo improvement; review of this
revised result is pending.

Use pinned `griffe2md`/Griffe to generate the API Markdown and commit the
versioned output. A small wrapper sets the Sphinx docstring parser, includes
members without docstrings, adds Docusaurus front matter, removes unresolved
cross-reference links, and converts the one legacy `.. warning:` block. The
wrapper's `--check` mode detects drift. `OmegaConf.create()` parameters and
`OmegaConf.clear_resolver()` warning render in the generated page. The old 2.3
source has sparse docstrings; generation keeps those signatures rather than
inventing descriptions.

Use `@easyops-cn/docusaurus-search-local` for the prototype. Its production
build emitted separate search indexes for `/docs/` and `/docs/next/`, with
guide pages and `create`/`MISSING` entries in both and `typed_list` only in
2.4. The first-config example is executed directly from each Markdown page
with Python's doctest module. The production build passed with broken internal
links and anchors configured to fail. In the user's first browser review, the
site worked but its appearance was rejected. A subsequent marketing-style
landing page was also rejected. The quieter technical-docs direction and new
logo are now implemented. The site build is validated on pull requests and
published from `main` to `https://hydra-ecosystem.github.io/omegaconf/`.
Redirects, reader review, and canonical-link cutover remain later work.

### Implementation inventory

Every proposed 2.4 page ID now has a first content pass. Both versions now
separate node interpolation from resolver calls and organize the sidebar by
capability. The `eval` arithmetic guide was removed from both versions and
the Sphinx source. The 2.3 tree has the shared topics, while 2.4-only tuple,
YAML-alias-limit, and other new behavior remain in the prerelease tree. The
new pages are intentionally shorter than the Sphinx source. The
[coverage audit](docs-site-coverage.md) separates sufficiently documented
behavior from prioritized gaps and records intentional exclusions. It also
checks the 2.3 topics against published RTD and 2.3.1 behavior instead of
inferring them from current source. Reader review and redirect verification
are still needed before replacing RTD.

The legacy link map above still needs generated heading and API-symbol anchors
before redirects can be configured. Preview review and cutover remain open.
API drift and selected-example checks now run in CI against the matching
source versions. Sphinx and RTD stay intact during this work.

## Tool references

- [Docusaurus documentation versioning](https://docusaurus.io/docs/versioning)
- [Docusaurus docs content plugin](https://docusaurus.io/docs/api/plugins/%40docusaurus/plugin-content-docs)
- [Docusaurus redirect plugin](https://docusaurus.io/docs/api/plugins/%40docusaurus/plugin-client-redirects)
- [Docusaurus search options](https://docusaurus.io/docs/search)
- [Read the Docs external redirects](https://docs.readthedocs.com/platform/latest/user-defined-redirects.html)
- [haystack-pydoc-tools](https://github.com/deepset-ai/haystack-pydoc-tools)
