# Website coverage against Read the Docs

Status: content audit, 2026-09-30. This is the cutover checklist for the
Docusaurus content, alongside [the site design](docs-site-migration.md). It
compares `website/docs/` with the current 2.4 `legacy/rtd/source/` and
`website/versioned_docs/version-2.3/` with the
[published 2.3 RTD documentation](https://omegaconf.readthedocs.io/en/2.3_branch/).
The 2.3 examples are checked with the 2.3.1 source distribution, because
current checkout behavior must not be used to verify an older version.

This audit separates material that is sufficiently documented for the new
site from gaps that would materially improve a reader's ability to use or
understand OmegaConf. “Sufficiently documented” means the rule and a useful
example or lookup path exist in the correct version. It does not require
copying repetitive RTD examples or formal grammar productions. A generated
API signature alone does not count as coverage for behavior that needs an
explanation. The existing
[source-heading ownership table](docs-site-migration.md#source-heading-ownership)
maps every 2.4 Sphinx heading to a website page; this audit checks the
behavior and examples behind those headings.

The current Sphinx usage page still says Python 3.8 is supported for 2.4;
the website follows the package's actual `>=3.10` requirement. That stale
source statement is not carried forward.

## Sufficiently documented

### OmegaConf 2.4

| Behavior and example family | Website destination | Evidence |
| --- | --- | --- |
| Installation, creation from empty/dict/list/YAML, access, defaults, mutation, supported key kinds | `get-started/*`, `concepts/configs-and-values` | Examples form one beginner path; key-type and integer-path rules are explicit. |
| Native tuple creation, immutable elements, and list-versus-tuple migration | `concepts/configs-and-values`, `reference/types`, `migration/2.4#tuple-inputs-no-longer-become-mutable-lists` | The upgrade guide has a breaking-change summary and collapsed migration examples. |
| Mandatory `???`, escaped literal `\???`, detached values, and YAML round trip | `concepts/missing-values`, `reference/operations` | Missing inspection and structural comparison distinguish missing from literal text. |
| YAML text/files/file objects, flow style, pickle, and schema loss on YAML load | `guides/load-and-save` | File-object, flow-style, and pickle examples execute. |
| Dotlist and CLI creation, escaped key paths, shell quoting | `guides/command-line`, `reference/operations` | Interpolation, API, and shell escaping are distinguished. |
| Node, relative, nested, and string interpolation; lazy versus eager resolution | `concepts/interpolation`, `reference/grammar` | Whole-node type and interpolated strings are shown separately. |
| Multi-source merge, missing source values, list replacement, union operators, unsafe merge | `guides/merge` | Worked examples cover precedence, missing values, non-mutating and in-place unions, and destructive merging. |
| Read-only and struct flags, inherited defaults, scoped overrides, frozen classes | `guides/flags`, `concepts/structured-configs` | Each flag has an example; frozen classes link to the same behavior. |
| `to_container` resolution, missing handling, all `SCMode` choices, `to_object` | `reference/operations` | The structured-instance example and `to_object` equivalence cover the choices. |
| `resolve()` materialization and custom-resolver traversal caveat | `concepts/interpolation`, `reference/operations` | Materialization and order dependence are explicit. |
| `select`, `can_select`, `update`, merge versus replace, `force_add`, interpolation paths | `reference/operations` | Missing/default, alias-update, and replacement behavior have examples. |
| Key-path escaping, integer dictionary keys, literal delimiters | `reference/operations`, `reference/grammar`, `guides/command-line` | Interpolation and CLI paths are distinguished. |
| `masked_copy`, `missing_keys`, `structural_equality`, node/container inspection, hashing | `reference/operations` | Missing and structural examples supplement the generated signatures. |
| Structured creation, duck typing, nesting, static typing, unknown fields | `concepts/structured-configs` | The introductory schema example remains short and leads into field types. |
| Primitive, Enum, Literal, list, dict, nested container, tuple, optional annotations | `concepts/field-types`, `reference/types`, `concepts/optional-fields` | Nested mutation and Enum text conversion have examples. |
| Union branch selection, ambiguous typed containers, structured branches, YAML type loss | `reference/types`, `reference/conversion` | Typed-container and structured-branch examples cover disambiguation. |
| Assignment conversion warning, explicit update, resolver-result validation, typed interpolation | `reference/conversion` | Resolver and destination checks are explained separately. |
| Missing/optional distinction, frozen schemas, schema merge, ignored metadata | `concepts/missing-values`, `concepts/optional-fields`, `guides/flags`, `guides/schema-validation` | Each rule appears where the corresponding task is taught. |
| Custom resolver registration, names, nested arguments, context, caching, removal | `guides/custom-resolvers` | Context parameters, cache keys, and resolver removal have examples. |
| Resolver annotation-validation modes and failures | `guides/custom-resolvers` | Executable examples cover a successful call, an argument mismatch in `"error"` mode, and the registration fallback in `"warn"` mode. |
| `oc.env`, `oc.create`, `oc.deprecated`, `oc.coerce`, `oc.decode`, `oc.select`, dict views | `reference/built-in-resolvers` | Each resolver has an example or precise type/import guidance. |
| Interpolation syntax, punctuation, and the three escaping contexts | `reference/grammar` | A lookup table and executable ambiguous cases supplement the authoritative lexer and parser. |
| YAML alias expansion limits and configuration | `reference/yaml-alias-limits` | Thresholds, precedence, and recursive-alias rejection are covered. |
| Public `OmegaConf` methods, module helpers, `MISSING` | `reference/python-api/omegaconf` | The API is generated from 2.4 source with a task-based entry page. |

### OmegaConf 2.3

The published RTD branch identifies itself as 2.3.0 documentation; the
website's stable version and executable API snapshot use 2.3.1. New 2.4 rules
are not projected backward.

| Published behavior | Website destination | Evidence |
| --- | --- | --- |
| Installation, creation, access, missing values, interpolation, flags | Corresponding start/concept/guide pages | The shorter reading path preserves the principal rules. |
| Multi-source merge, list replacement, missing source values, unsafe merge | `guides/merge` | Version-correct examples cover each 2.3 behavior; union operators point to 2.4. |
| YAML load/save, `to_container` modes, `to_object`, pickle | `guides/load-and-save`, `reference/operations` | Examples run with 2.3.1 and retain the Python 3.6 pickle limitation. |
| `select`, `update`, `masked_copy`, `missing_keys` | `reference/operations` | Missing/default and merge-versus-replace behavior have examples. |
| Structured simple, nested, container, Enum, union, optional, ignored fields | `concepts/field-types`, `reference/types`, `guides/schema-validation` | Member-name conversion and 2.3's Enum limitation are explicit. |
| Scalar typed interpolation and the unvalidated container-interpolation exception | `reference/conversion` | The version-specific exception is explicit and tested. |
| Custom resolver registration, context parameters, caching, clearing | `guides/custom-resolvers` | Examples use 2.3's `register_new_resolver()`. |
| Built-in resolvers, including `oc.select` for a colon-containing key | `reference/built-in-resolvers` | Examples execute with 2.3.1; `oc.coerce` is not projected backward. |
| Interpolation syntax, punctuation, and escaping | `reference/grammar` | A version-correct lookup and executable ambiguous cases accompany the 2.3 grammar source. |
| Bundled PyDev.Debugger extension | `guides/debugging` | Guidance matches the extension shipped in the 2.3.1 distribution. |
| Public API | `reference/python-api/omegaconf` | The API is generated from 2.3.1 source rather than current 2.4 code. |

Arithmetic through an `eval` resolver remains intentionally excluded from both
versions. It was removed at the user's request and is not a recommended
learning example.

## Gaps worth fixing

No content gaps remain from this audit. Reopen this section when reader review
finds a task that the destination pages do not explain well enough to perform.

## Cutover gate

Local validation on 2026-09-30 passed: all hand-written Markdown doctests
for both documentation versions (2.3 examples against OmegaConf 2.3.1),
both generated-API drift checks, and the Docusaurus production build.
Formatting, lint, and static type checks also passed. This does not replace
the preview and redirect checks below.

Content is ready for reader review when the classifications above remain
accurate, version-specific doctests pass, and the site builds with broken
internal links treated as errors. Reopen a sufficiently documented row if a
reader cannot carry out the task from its destination. The separate notebook
tutorial stays under its existing validation; it is not part of the RTD
navigation tree.

The following release mechanics remain open before RTD links move:

- Complete the 2.3 and 2.4 old URL/anchor inventory, including generated
  heading and API-symbol anchors, and verify every redirect destination.
- Wire the site build, selected page examples, and generated-API drift check
  into CI for both documentation versions.
- Choose the canonical domain and hosting provider, validate a preview on
  desktop and mobile, and check versioned search and the main reader path.
- Keep RTD live for old and unmigrated versions until redirects work.
