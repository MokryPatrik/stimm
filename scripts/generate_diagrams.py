#!/usr/bin/env python3
"""Render Mermaid diagrams to SVG using the mermaid-cli Docker image.

This script scans `documentation/diagrams/*.mmd` and, for each file, invokes
the official Mermaid CLI container to produce a sibling `.svg`. It only
requires Docker, making it easy for automation or an AI agent to refresh the
diagrams after architecture updates.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

DIAGRAM_DIR = Path("documentation/diagrams")
MERMAID_IMAGE = os.getenv("MERMAID_CLI_IMAGE", "minlag/mermaid-cli:10.9.0")


def render_diagram(source: Path) -> Path:
    """Render a single Mermaid diagram using the Mermaid CLI Docker image."""
    output = source.with_suffix(".svg")
    volume = f"{source.parent.resolve()}:/data"
    input_path = f"/data/{source.name}"
    output_path = f"/data/{output.name}"

    cmd = [
        "docker",
        "run",
        "--rm",
        "-v",
        volume,
    ]

    if os.name == "posix":
        cmd.extend(["-u", f"{os.getuid()}:{os.getgid()}"])

    cmd.extend(
        [
            MERMAID_IMAGE,
            "-i",
            input_path,
            "-o",
            output_path,
        ]
    )

    subprocess.run(cmd, check=True)
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dir",
        default=str(DIAGRAM_DIR),
        help="Directory containing .mmd diagram sources (default: %(default)s)",
    )
    args = parser.parse_args(argv)

    source_dir = Path(args.dir)
    if not source_dir.exists():
        print(f"Diagram directory not found: {source_dir}", file=sys.stderr)
        return 1

    sources = sorted(source_dir.glob("*.mmd"))
    if not sources:
        print(f"No .mmd files found in {source_dir}", file=sys.stderr)
        return 1

    written: list[Path] = []
    try:
        for path in sources:
            if path.suffix != ".mmd":
                continue
            output = render_diagram(path)
            written.append(output)
    except subprocess.CalledProcessError as err:
        print(f"Mermaid CLI failed (exit code {err.returncode})", file=sys.stderr)
        return 1

    for path in written:
        print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
