"""Run selected website examples against the installed documentation version."""

import argparse
import doctest
import re
import subprocess
import sys
from pathlib import Path

WEBSITE = Path(__file__).resolve().parents[1]
PAGES = (
    "get-started/first-config.md",
    "guides/merge.md",
    "concepts/interpolation.md",
    "guides/load-and-save.md",
    "concepts/structured-configs.md",
    "guides/custom-resolvers.md",
)


def python_blocks(markdown: str):
    """Yield Python fences, their metadata, and zero-based source line offsets."""
    fence = None
    info = ""
    content: list[str] = []
    start = 0
    for number, line in enumerate(markdown.splitlines(keepends=True)):
        if fence is None:
            match = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line.rstrip("\n"))
            if match:
                fence, info = match.groups()
                content = []
                start = number + 1
        elif re.fullmatch(rf" {{0,3}}{re.escape(fence[0])}{{{len(fence)},}}\s*", line):
            metadata = info.split()
            if metadata and metadata[0] in ("python", "python-repl"):
                yield "".join(content), metadata[1:], start
            fence = None
        else:
            content.append(line)
    if fence is not None:
        raise ValueError("unclosed code fence")


def run_page(page: Path, docs_version: str) -> doctest.TestResults:
    """Share globals between a page's blocks, comparing every displayed result."""
    namespace = {"__name__": "__main__"}
    runner = doctest.DocTestRunner()
    parser = doctest.DocTestParser()
    for content, metadata, line in python_blocks(page.read_text(encoding="utf-8")):
        if "doctest-skip" in metadata:
            continue
        if "doctest-setup" in metadata:
            exec(compile("\n" * line + content, str(page), "exec"), namespace)
            continue
        test = parser.get_doctest(
            content, namespace, f"OmegaConf {docs_version}: {page}", str(page), line
        )
        if not test.examples:
            raise ValueError(
                f"{page}:{line + 1}: Python fence needs >>> prompts, "
                "doctest-setup, or doctest-skip"
            )
        runner.run(test, clear_globs=False)
        namespace = test.globs
    result = runner.summarize()
    if not result.attempted:
        raise ValueError(f"{page}: no runnable examples")
    print(
        f"OmegaConf {docs_version}: {page}: "
        f"{result.attempted} examples, {result.failed} failures"
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docs-version", choices=("2.3", "next"), required=True)
    parser.add_argument("--page", type=Path, help="Run only this Markdown page")
    args = parser.parse_args()

    from omegaconf import __version__

    if args.docs_version == "2.3":
        expected = "2.3.1"
        root = WEBSITE / "versioned_docs" / "version-2.3"
    else:
        version_source = (WEBSITE.parent / "omegaconf" / "version.py").read_text()
        match = re.search(r'__version__\s*=\s*"([^"]+)"', version_source)
        assert match is not None
        expected = match[1]
        root = WEBSITE / "docs"
    if __version__ != expected:
        parser.error(
            f"{args.docs_version} docs require OmegaConf {expected}, "
            f"but imported {__version__}"
        )

    if args.page is not None:
        return int(run_page(args.page, args.docs_version).failed != 0)

    pages = list(PAGES)
    if args.docs_version == "next":
        pages.append("migration/2.4.md")
    failed = False
    for page in pages:
        # A separate process also isolates resolver registrations and imports.
        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--docs-version",
                args.docs_version,
                "--page",
                str(root / page),
            ],
            check=False,
        )
        failed |= result.returncode != 0
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
