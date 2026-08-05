"""Keep the test run inside this project's interpreter.

The agent/editor harness that drives these tests exports a ``PYTHONPATH``
pointing at its own virtualenv's ``site-packages``. Because ``PYTHONPATH``
precedes the venv's own paths, its ``pydantic``/``pydantic_core`` shadow ours,
and collection dies with::

    ModuleNotFoundError: No module named 'pydantic_core._pydantic_core'

(the shadowing copy ships no compiled extension for this interpreter).

Dropping those entries here -- before pytest imports any test module -- means
a bare ``pytest`` works regardless of the parent environment, instead of
requiring ``env -u PYTHONPATH -u PYTHONHOME`` at every call site.
"""

import sys
import sysconfig
from pathlib import Path


def _belongs_to_this_interpreter(entry: Path) -> bool:
    roots = {
        sysconfig.get_paths().get("purelib"),
        sysconfig.get_paths().get("platlib"),
    }
    for root in filter(None, roots):
        try:
            if entry.samefile(root):
                return True
        except OSError:
            continue
    return False


def _prune_foreign_site_packages() -> None:
    prefix = Path(sys.prefix).resolve()
    for raw in list(sys.path):
        if not raw or raw.endswith((".zip", ".egg")):
            continue
        try:
            entry = Path(raw).resolve()
        except OSError:
            continue
        if entry.name != "site-packages":
            continue
        if _belongs_to_this_interpreter(entry):
            continue
        if prefix in entry.parents:  # our own venv, just spelled differently
            continue
        sys.path.remove(raw)

    # Drop already-imported modules that came from the pruned paths, so a later
    # import re-resolves against this interpreter.
    for name in [n for n in sys.modules if n.split(".")[0] == "pydantic_core"]:
        del sys.modules[name]


_prune_foreign_site_packages()

# Make the repo root importable (``import app...``) no matter the working dir.
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
