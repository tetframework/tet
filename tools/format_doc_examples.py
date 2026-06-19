#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = ["ruff==0.4.4"]
# ///
"""Format the Python ``code-block`` examples embedded in reStructuredText docs.

This is a small ``blacken-docs`` equivalent that uses **ruff** (not black) so the
examples in our documentation are formatted exactly like the rest of the source
tree (same ``ruff format`` rules, same pinned ruff version as the pre-commit
``ruff-format`` hook).

Usage::

    # Reformat every example in docs/ in place
    tools/format_doc_examples.py

    # Only report which examples are not formatted (CI / pre-commit); exit 1 if any
    tools/format_doc_examples.py --check

    # Restrict to specific files or directories
    tools/format_doc_examples.py docs/narr/services.rst

Only ``.. code-block:: python`` (and ``python3``) blocks are touched. Snippets
that ruff cannot parse (intentional fragments) are left untouched and reported.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

# Share the RST code-block parsing with the compile-check tooling/tests.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from doc_examples import (  # noqa: E402,I001
    DIRECTIVE_RE,
    OPTION_RE,
    _indent_of,
    iter_rst_files,
)

RUFF = shutil.which("ruff")


def ruff_format(code: str, stdin_filename: Path) -> str | None:
    """Format a snippet with ruff. Return formatted text, or None if unparseable."""
    if RUFF is None:
        sys.exit("error: could not find the 'ruff' executable on PATH")
    proc = subprocess.run(
        [RUFF, "format", "-", "--stdin-filename", str(stdin_filename)],
        input=code,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        # Most commonly a syntax error: an intentionally partial snippet.
        return None
    return proc.stdout


def process_text(text: str, path: Path):
    """Return (new_text, formatted_count, skipped) for one document."""
    lines = text.split("\n")
    n = len(lines)
    out: list[str] = []
    formatted_count = 0
    skipped: list[int] = []
    i = 0
    while i < n:
        line = lines[i]
        m = DIRECTIVE_RE.match(line)
        if not m:
            out.append(line)
            i += 1
            continue

        base = len(m.group("indent"))
        out.append(line)
        i += 1

        # Pass through directive options (e.g. :caption:) and the blank line(s).
        while i < n:
            cur = lines[i]
            if cur.strip() == "":
                out.append(cur)
                i += 1
                continue
            mo = OPTION_RE.match(cur)
            if mo and len(mo.group("indent")) > base:
                out.append(cur)
                i += 1
                continue
            break

        # Collect the indented body of the code block.
        body_start = i + 1  # 1-based line number of first body line
        body: list[str] = []
        while i < n:
            cur = lines[i]
            if cur.strip() == "":
                body.append(cur)
                i += 1
                continue
            if _indent_of(cur) > base:
                body.append(cur)
                i += 1
                continue
            break

        # Split trailing blank lines off — they sit between this block and the next.
        trailing: list[str] = []
        while body and body[-1].strip() == "":
            trailing.insert(0, body.pop())

        nonblank = [b for b in body if b.strip()]
        if not nonblank:
            out.extend(body)
            out.extend(trailing)
            continue

        body_indent = min(_indent_of(b) for b in nonblank)
        code = "\n".join(b[body_indent:] if b.strip() else "" for b in body)
        formatted = ruff_format(code + "\n", path)
        if formatted is None:
            skipped.append(body_start)
            out.extend(body)
            out.extend(trailing)
            continue

        prefix = " " * body_indent
        new_body = [
            (prefix + fl) if fl else "" for fl in formatted.rstrip("\n").split("\n")
        ]
        if new_body != body:
            formatted_count += 1
        out.extend(new_body)
        out.extend(trailing)

    return "\n".join(out), formatted_count, skipped


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        default=["docs"],
        help="RST files or directories to process (default: docs/)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="do not write files; exit 1 if any example would be reformatted",
    )
    args = parser.parse_args()

    total_changed = 0
    changed_files = 0
    total_skipped = 0
    for path in iter_rst_files(args.paths):
        original = path.read_text(encoding="utf-8")
        new_text, count, skipped = process_text(original, path)
        if skipped:
            total_skipped += len(skipped)
            locs = ", ".join(f"{path}:{ln}" for ln in skipped)
            print(f"skip (unparseable, left as-is): {locs}", file=sys.stderr)
        if count:
            total_changed += count
            changed_files += 1
            if args.check:
                print(f"would reformat {count} example(s) in {path}")
            else:
                path.write_text(new_text, encoding="utf-8")
                print(f"reformatted {count} example(s) in {path}")

    if args.check:
        if total_changed:
            print(
                f"\n{total_changed} example(s) in {changed_files} file(s) need formatting"
            )
            return 1
        print("all doc examples are formatted")
        return 0

    print(
        f"\ndone: {total_changed} example(s) reformatted in {changed_files} file(s)"
        f"; {total_skipped} unparseable snippet(s) skipped"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
