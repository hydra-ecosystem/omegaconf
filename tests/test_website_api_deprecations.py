import runpy
from pathlib import Path

add_deprecation_notices = runpy.run_path(
    str(Path(__file__).parents[1] / "website" / "scripts" / "generate_api.py")
)["add_deprecation_notices"]


def test_runtime_deprecation_is_shown_without_a_docstring() -> None:
    source = '''
class OmegaConf:
    def register_resolver(name, resolver):
        warnings.warn(dedent("""
            register_resolver() is deprecated.
            See https://example.com/migration for migration instructions.
        """))
'''
    rendered = """## `OmegaConf`

### `register_resolver`

```python
register_resolver(name, resolver)
```

### `resolve`

Resolve interpolations.
"""
    result = add_deprecation_notices(rendered, source)
    assert "> **Deprecated:** register_resolver() is deprecated." in result
    assert "https://example.com/migration" in result
    assert "register_resolver(name, resolver)" in result
    assert result.split("### `resolve`")[1] == rendered.split("### `resolve`")[1]


def test_existing_docstring_notice_is_not_duplicated() -> None:
    source = """
def register_new_resolver():
    warnings.warn("register_new_resolver() is deprecated.")
"""
    rendered = """### `register_new_resolver`

Deprecated since version 2.4. Use `register_resolver()` instead.
"""
    assert add_deprecation_notices(rendered, source) == rendered


def test_other_warnings_do_not_deprecate_a_function() -> None:
    source = """
def register_resolver():
    warnings.warn("A config key is deprecated.")

def deprecated():
    warnings.warn("The old config key is deprecated.")
"""
    rendered = "## `register_resolver`\n\n## `deprecated`\n"
    assert add_deprecation_notices(rendered, source) == rendered
