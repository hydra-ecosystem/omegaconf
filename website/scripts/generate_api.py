"""Render the public OmegaConf API from a specific source release."""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    source = args.source.resolve()
    version_file = source / "omegaconf" / "version.py"
    match = re.search(r'__version__\s*=\s*"([^"]+)"', version_file.read_text())
    if match is None or match.group(1) != args.version:
        parser.error(f"expected OmegaConf {args.version} in {version_file}")

    with TemporaryDirectory() as temporary_dir:
        temporary = Path(temporary_dir)
        config_dir = temporary / ".config"
        config_dir.mkdir()
        (config_dir / "griffe2md.toml").write_text(
            'docstring_style = "sphinx"\n'
            "show_if_no_docstring = true\n"
            "show_signature_annotations = true\n"
            'filters = ["!^_", "!^register_default_resolvers$"]\n'
            'members_order = "alphabetical"\n'
            "show_root_full_path = false\n"
            "show_root_heading = false\n"
            "show_root_members_full_path = false\n"
            "show_object_full_path = false\n"
            "show_submodules = false\n"
            "summary = false\n"
            "heading_level = 2\n"
            f"search_paths = [{json.dumps(str(source))}]\n\n"
            "[docstring_options]\n"
        )
        raw_file = temporary / "api.md"
        subprocess.run(
            [
                str(Path(sys.executable).with_name("griffe2md")),
                "omegaconf.omegaconf",
                "-o",
                str(raw_file),
            ],
            cwd=temporary,
            check=True,
        )
        raw = raw_file.read_text()

    # griffe2md emits links to symbols outside this one-page reference.
    rendered = re.sub(r"\[([^\]]+)\]\(#[^)]+\)", r"\1", raw)
    # This legacy reST directive is not recognized by Griffe's Sphinx parser.
    rendered = re.sub(
        r"(?m)^\.\. warning:\n[ \t]+(.+)$", r"> **Warning:** \1", rendered
    )
    rendered = (
        f"---\ntitle: OmegaConf symbols\n"
        f"description: OmegaConf {args.version} generated Python API\n"
        "toc_max_heading_level: 2\n---\n\n"
        f"API snapshot from OmegaConf {args.version} source. "
        "For task-based entry points, see the [Python API overview](../python-api).\n\n"
        f"{rendered}"
    )

    for symbol in (
        "MISSING",
        "OmegaConf",
        "II",
        "SI",
        "flag_override",
        "open_dict",
        "read_write",
        "create",
        "clear_resolver",
    ):
        if not re.search(rf"(?m)^#{{1,6}} `{symbol}`$", rendered):
            raise RuntimeError(f"missing public API symbol: {symbol}")

    output = args.output.resolve()
    if args.check:
        if not output.exists() or output.read_text() != rendered:
            print(f"Generated API differs from {output}", file=sys.stderr)
            return 1
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
