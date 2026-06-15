#!/usr/bin/env python3
# tet documentation build configuration file

import os
import re
import sys

# Make the package importable for autodoc (src layout)
sys.path.insert(0, os.path.abspath("../src"))

# -- General configuration ------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "myst_parser",
]

# Suppress myst header warnings (logo replaces H1 title)
suppress_warnings = ["myst.header"]

templates_path = ["_templates"]

# Support both RST and Markdown
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

master_doc = "index"

# General information about the project.
project = "tet"
copyright = "2013-2026, Tet Contributors"
author = "Tet Contributors"

# Read version from pyproject.toml
pyproject_path = os.path.join(os.path.dirname(__file__), "..", "pyproject.toml")
with open(pyproject_path) as f:
    content = f.read()
    match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
    if match:
        release = match.group(1)
        version = ".".join(release.split(".")[:2])
    else:
        version = "0.5"
        release = "0.5.0"

language = "en"

exclude_patterns = ["_build"]

pygments_style = "sphinx"


# -- Options for autodoc --------------------------------------------------

# Exclude deprecated classes from documentation
autodoc_default_options = {
    "exclude-members": "TetAppFactory",
}


def autodoc_skip_member(app, what, name, obj, skip, options):
    """Skip deprecated TetAppFactory class."""
    if name == "TetAppFactory":
        return True
    return skip


def setup(app):
    app.connect("autodoc-skip-member", autodoc_skip_member)


# -- Options for HTML output ----------------------------------------------

html_theme = "sphinx_rtd_theme"

html_theme_options = {
    "logo_only": True,
}

html_logo = "_static/tet.png"

html_static_path = ["_static"]

htmlhelp_basename = "tet_doc"


# -- Options for intersphinx ----------------------------------------------

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "pyramid": ("https://docs.pylonsproject.org/projects/pyramid/en/latest/", None),
}
