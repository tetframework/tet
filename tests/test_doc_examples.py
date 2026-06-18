"""Compile-check every Python ``code-block`` example in the documentation.

Each ``.. code-block:: python`` snippet under ``docs/`` is extracted and passed
through :func:`compile`, so syntactically broken examples (or ones the doc
tooling mangles) fail CI. A snippet can opt out with a
``.. doc-example: no-compile`` comment immediately before its directive.

This does not *run* the examples -- many are deliberately partial -- it only
guarantees they are valid Python that parses and compiles.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS = REPO_ROOT / "docs"
sys.path.insert(0, str(REPO_ROOT / "tools"))

from doc_examples import iter_python_examples, iter_rst_files  # noqa: E402


def _collect():
    examples = []
    for path in iter_rst_files([str(DOCS)]):
        text = path.read_text(encoding="utf-8")
        examples.extend(iter_python_examples(text, path))
    return examples


EXAMPLES = _collect()
IDS = [f"{ex.path.relative_to(REPO_ROOT)}:{ex.lineno}" for ex in EXAMPLES]


def test_examples_were_found():
    # Guard against the extractor silently breaking and "passing" zero examples.
    assert len(EXAMPLES) > 100


@pytest.mark.parametrize("example", EXAMPLES, ids=IDS)
def test_doc_example_compiles(example):
    if example.no_compile:
        pytest.skip("marked .. doc-example: no-compile")
    compile(example.code, str(example.path.relative_to(REPO_ROOT)), "exec")
