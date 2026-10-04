import runpy
import subprocess
import sys
from pathlib import Path

import pytest

EXAMPLES = runpy.run_path(
    str(Path(__file__).parents[1] / "website" / "scripts" / "test_examples.py")
)
run_page = EXAMPLES["run_page"]


def test_page_context_and_markdown_fences(tmp_path: Path) -> None:
    page = tmp_path / "page.md"
    page.write_text(
        "Prose with >>> is not executable.\n"
        "```text\n>>> raise RuntimeError\n```\n"
        "```python doctest-setup\nvalue = 20\n```\n"
        "```python {1}\n>>> value += 1\n```\n"
        "~~~~python-repl\n>>> value * 2\n42\n~~~~\n"
        "```python doctest-skip\nraise RuntimeError\n```\n"
        "```python\n>>> raise ValueError('expected')\n"
        "Traceback (most recent call last):\n...\nValueError: expected\n```\n"
    )
    result = run_page(page, "next")
    assert result.failed == 0
    assert result.attempted == 3


def test_bad_output_reports_version_page_and_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    page = tmp_path / "wrong.md"
    page.write_text("Heading\n\n```python\n>>> 1 + 1\n3\n```\n")
    assert run_page(page, "2.3").failed == 1
    output = capsys.readouterr().out
    assert str(page) in output
    assert "line 4" in output
    assert "OmegaConf 2.3" in output
    assert "Expected:\n    3\nGot:\n    2" in output


def test_globals_do_not_leak_between_pages(tmp_path: Path) -> None:
    first = tmp_path / "first.md"
    first.write_text("```python\n>>> value = 42\n```\n")
    second = tmp_path / "second.md"
    second.write_text("```python\n>>> 'value' in globals()\nFalse\n```\n")
    assert run_page(first, "next").failed == 0
    assert run_page(second, "next").failed == 0


def test_bad_output_fails_command(tmp_path: Path) -> None:
    page = tmp_path / "wrong.md"
    page.write_text("```python\n>>> 1 + 1\n3\n```\n")
    result = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).parents[1] / "website/scripts/test_examples.py"),
            "--docs-version",
            "next",
            "--page",
            str(page),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "1 examples, 1 failures" in result.stdout


def test_wrong_runtime_version_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["test_examples.py", "--docs-version", "2.3"])
    with pytest.raises(SystemExit) as error:
        EXAMPLES["main"]()
    assert error.value.code == 2


@pytest.mark.parametrize(
    "markdown, message",
    [
        ("```python\n>>> 1\n1\n", "unclosed code fence"),
        ("```python\nvalue = 1\n```\n", "needs >>> prompts"),
        ("No examples here", "no runnable examples"),
    ],
)
def test_accidentally_untested_page_fails(
    tmp_path: Path, markdown: str, message: str
) -> None:
    page = tmp_path / "empty.md"
    page.write_text(markdown)
    with pytest.raises(ValueError, match=message):
        run_page(page, "next")
