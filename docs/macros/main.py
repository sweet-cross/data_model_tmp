"""mkdocs-macros entry point: aggregate every contract-type macro module.

``mkdocs-macros-plugin`` loads a single Python module (named by
``plugins.macros.module_name`` in mkdocs.yml) and calls ``define_env(env)`` on
it. This file is that module. It delegates to each contract-type submodule so
each macro lives next to its own data/render logic instead of piling into one
giant file.

To add a new contract type (e.g. results) later: create
``docs/macros/<type>.py`` exposing ``register(env)`` and add an import + call
below.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import assumptions  # noqa: E402
import dimensions  # noqa: E402


def define_env(env):
    """mkdocs-macros hook: register every contract-type module's macros."""
    dimensions.register(env)
    assumptions.register(env)
