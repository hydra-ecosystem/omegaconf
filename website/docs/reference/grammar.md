---
title: Interpolation grammar
description: Syntax for node and resolver interpolation, arguments, and escaping.
---

OmegaConf parses interpolation strings with an ANTLR grammar. The
[lexer](https://github.com/hydra-ecosystem/omegaconf/blob/main/omegaconf/grammar/OmegaConfGrammarLexer.g4)
and [parser](https://github.com/hydra-ecosystem/omegaconf/blob/main/omegaconf/grammar/OmegaConfGrammarParser.g4)
are the authoritative definitions. This page summarizes the forms readers
write in configs.

## Interpolation strings

`${server.port}` is a node interpolation. `${oc.env:HOME}` is a resolver
interpolation that calls the `oc.env` resolver. Either may occupy the whole
value or appear inside a string interpolation, as in `https://${host}:${port}`.
A node interpolation occupying the whole value retains the referenced value's
type; string interpolation produces a string.

## Node references

Paths accept dots and brackets: `${host}`, `${servers[0].port}`, and
`${[some.key]}` are examples. A leading dot makes the path relative to the
current container; additional leading dots move up the tree. Nested
interpolations can select a path dynamically, as in
`${plans[${selected_plan}]}`.

In 2.4, escape a literal dot, bracket, or colon within a key name with a
backslash. `${a\.b}` addresses the key `a.b`; `${a.b}` addresses `b` under
`a`. Use two backslashes for a literal backslash in the key. Escapes are
interpreted once when resolving the path.

Key-path escaping is separate from escaping an interpolation. Here the
backslash makes the dot part of one key name:

```python
>>> from omegaconf import OmegaConf
>>> cfg = OmegaConf.create({"a.b": 10, "ref": r"${a\.b}"})
>>> cfg.ref
10

```

## Resolver arguments

`${name:arg1,arg2}` calls a resolver. Arguments are comma separated and can
be quoted strings, lists, dictionaries, primitives, or nested
interpolations. Examples include `${oc.select:path,default}` and
`${oc.decode:'[a, b]'}`. Empty arguments remain accepted for compatibility,
but are deprecated.

### Element types

Quoted strings may contain punctuation and nested interpolations. In an
unquoted argument, only a subset of punctuation is allowed; quote a complex
argument instead. `null`, `true`, and `false` are case-insensitive keywords.
`None` is an ordinary string in this grammar; use `null` for Python `None`.
Numbers may be integers or floats, including exponent notation, infinity,
and NaN. Dictionary keys in resolver arguments cannot be quoted strings or
interpolations.

| Argument | Value passed to the resolver |
| --- | --- |
| `42`, `true`, `null` | `int`, `bool`, `None` |
| `'42'` | String `"42"` |
| `[1, 2]`, `{a: 1}` | Python list or dict |
| `${other}` | Resolved value of another node |

### Punctuation lookup

Resolver arguments use punctuation either as text or as grammar delimiters.
This table covers the cases where quoting or escaping changes the parse:

| Context | May appear directly | Quote or backslash-escape |
| --- | --- | --- |
| Unquoted string | Slash, hyphen, backslash, plus, dot, dollar, percent, asterisk, at sign, question mark, pipe, colon, and interior spaces | `, [ ] { } ( ) =`, leading/trailing spaces, and tabs |
| Quoted string | All punctuation except the matching quote | The matching quote and `\${` when `${` must remain text |
| Dictionary key in a resolver argument | Unquoted text; escape punctuation as needed | Quotes and interpolations are not allowed as keys |
| Node key path | Dots and brackets separate path components; `=` may be literal | In 2.4, escape `.`, `[`, `]`, `:`, or `\` when it belongs to the key; `=` may also be escaped |

For unquoted arguments, quoting and backslash escaping are two ways to keep a
delimiter as text. Backslash escaping is also available for parentheses and
equals signs, which otherwise are not valid unquoted characters:

```python
>>> from omegaconf import OmegaConf
>>> OmegaConf.register_resolver("capture_grammar_docs", lambda *args: args)
>>> cfg = OmegaConf.create({
...     "bare": r"${capture_grammar_docs:/-+.$%*@?|:}",
...     "escaped": r"${capture_grammar_docs:a\,b,\[x\],left\=right,\(group\)}",
...     "quoted": '${capture_grammar_docs:"a,b","[x]","left=right"}',
...     "mapping": r"${capture_grammar_docs:{a\:b: 1, x\,y: 2}}",
... })
>>> cfg.bare
('/-+.$%*@?|:',)
>>> cfg.escaped
('a,b', '[x]', 'left=right', '(group)')
>>> cfg.quoted
('a,b', '[x]', 'left=right')
>>> cfg.mapping
({'a:b': 1, 'x,y': 2},)

```

Quoted and unquoted `???` both produce missing values when stored in a
config. For compatibility, a direct `???` resolver argument still reaches
the resolver as text. In 2.4, use `\???` for literal text `???`; a missing
node interpolated into an argument raises before the resolver is called.

## Escaping

### Escaping in interpolation strings

Use `\${` to keep interpolation syntax as literal text. To put a backslash
immediately before a real interpolation, escape that backslash as `\\${`.

These examples separate an escaped interpolation from a backslash followed
by a real interpolation:

```python
>>> from omegaconf import OmegaConf
>>> cfg = OmegaConf.create({
...     "dir": "tmp",
...     "literal": r"\${dir}",
...     "with_slash": r"C:\\${dir}",
... })
>>> cfg.literal
'${dir}'
>>> cfg.with_slash
'C:\\tmp'

```

### Escaping in unquoted strings

In unquoted resolver arguments, backslash also escapes punctuation such as
commas and brackets. Leading or trailing whitespace must be escaped to
preserve it; a quoted argument is usually clearer.

```python
>>> cfg = OmegaConf.create({"text": r"${oc.decode: \ hi u \  }"})
>>> cfg.text
' hi u  '

```

### Escaping in quoted strings

Within quoted arguments, escape a quote matching the surrounding quote type.
An interpolation nested inside the quoted argument parses its own quotes;
those do not need another level of escaping.

```python
>>> cfg = OmegaConf.create({
...     "a:b": 10,
...     "key": "a:b",
...     "selected": "${oc.select:'${key}'}",
... })
>>> cfg.selected
10

```

For the behavior of resolved values, see [node interpolation](../concepts/interpolation)
and [resolver interpolation](../concepts/resolvers).
