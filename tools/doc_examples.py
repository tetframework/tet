#!/usr/bin/env python3
"""Extract (and compile-check) Python ``code-block`` examples in RST docs.

Shared by :mod:`tools.format_doc_examples` (which ruff-formats the examples) and
``tests/test_doc_examples.py`` (which compile-checks them). Pure standard
library so it imports cleanly under pytest with no extra dependencies.

Run directly to compile-check every example (used as a pre-commit gate)::

    tools/doc_examples.py            # checks docs/
    tools/doc_examples.py docs/narr  # checks a subset

A snippet can opt out of compile-checking with a ``.. doc-example: no-compile``
comment on the line immediately before the ``.. code-block:: python`` directive,
for intentionally partial fragments.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Iterator, NamedTuple

DIRECTIVE_RE = re.compile(r"^(?P<indent>[ \t]*)\.\. code-block:: *python3?\s*$")
OPTION_RE = re.compile(r"^(?P<indent>[ \t]*):[\w-]+:")
NO_COMPILE_RE = re.compile(r"^\s*\.\. doc-example: *no-compile\s*$")


class Example(NamedTuple):
    """One extracted Python code block."""

    path: Path
    lineno: int  # 1-based line of the first body line
    code: str  # dedented snippet text
    no_compile: bool  # opted out of compile-checking


def _indent_of(line: str) -> int:
    return len(line) - len(line.lstrip())


def iter_python_examples(text: str, path: Path) -> Iterator[Example]:
    """Yield each ``.. code-block:: python`` body found in *text*, dedented."""
    lines = text.split("\n")
    n = len(lines)
    i = 0
    while i < n:
        m = DIRECTIVE_RE.match(lines[i])
        if not m:
            i += 1
            continue

        no_compile = i > 0 and bool(NO_COMPILE_RE.match(lines[i - 1]))
        base = len(m.group("indent"))
        i += 1

        # Skip directive options (e.g. :caption:) and blank lines.
        while i < n:
            cur = lines[i]
            if cur.strip() == "":
                i += 1
                continue
            mo = OPTION_RE.match(cur)
            if mo and len(mo.group("indent")) > base:
                i += 1
                continue
            break

        # Collect the indented body.
        body_start = i + 1
        body: list[str] = []
        while i < n:
            cur = lines[i]
            if cur.strip() == "" or _indent_of(cur) > base:
                body.append(cur)
                i += 1
                continue
            break

        while body and body[-1].strip() == "":
            body.pop()
        nonblank = [b for b in body if b.strip()]
        if not nonblank:
            continue

        body_indent = min(_indent_of(b) for b in nonblank)
        code = "\n".join(b[body_indent:] if b.strip() else "" for b in body)
        yield Example(path=path, lineno=body_start, code=code, no_compile=no_compile)


def iter_rst_files(paths: list[str]) -> Iterator[Path]:
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            yield from sorted(p.rglob("*.rst"))
        elif p.suffix == ".rst":
            yield p


def main(argv: list[str]) -> int:
    """Compile-check every example under the given paths (default ``docs``)."""
    paths = argv or ["docs"]
    total = 0
    skipped = 0
    failures = []
    for path in iter_rst_files(paths):
        text = path.read_text(encoding="utf-8")
        for ex in iter_python_examples(text, path):
            total += 1
            if ex.no_compile:
                skipped += 1
                continue
            try:
                compile(ex.code, f"{ex.path}:{ex.lineno}", "exec")
            except SyntaxError as exc:
                failures.append((ex.path, ex.lineno, exc.msg))

    for p, lineno, msg in failures:
        print(f"{p}:{lineno}: does not compile: {msg}", file=sys.stderr)

    print(f"checked {total} example(s) ({skipped} skipped, {len(failures)} failed)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
