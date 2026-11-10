"""BLOQUE 75: where the animated sets live.

A directory is a SET iff it holds a `manifest.toml` AND its name does not
start with "_". Nothing else is.

How the exclusion actually works: `discover_sets` scans the CHILDREN of a
root, ONE level deep. `_backup_pre_bloque_65` lives INSIDE `mine_asteroid/`,
so the scan never visits it -- it is excluded by NESTING, and the "_" rule
would exclude it as well if it ever moved up to the root. The two
`_new_reference_*.png` files are excluded because they are files, not
directories. This module never enumerates frames, so the `frame_*.png`
naming rule does not live here.

The two roots are probed in order: the bosses first (GOLIATH), then the
enemies. The frozen build resolves the same way: the bundle is extracted to
`_MEIPASS` and the Assets are read from THERE.

BLOQUE 76: "is a set" and the ENEMIES probe now live in ONE place --
`src/anim/sets.py`, next to the canonical list of the enemy sets. This
module keeps its own API (`sets_roots()`, `resolve_set()`, `discover_sets()`)
for the six tests and the CLIs that use it, and RE-EXPORTS the definition
instead of repeating it: two copies of "is a set" are two truths that can
drift, and the drift would be silent -- the pipeline would discover a set
the game does not draw, or the other way round.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.anim.sets import _is_set, enemies_root  # noqa: E402

SET_DIR_NAMES = ("bosses", "enemies")


class SetNotFoundError(ValueError):
    """The named set does not exist under any sets root.

    A `ValueError` subclass on purpose: the CLIs catch `ValueError`
    (`run.py`, `audit.py`) and print `error: ...` instead of a traceback.
    `FileNotFoundError` is an `OSError` and would NOT be caught.
    """


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def sets_roots() -> list[Path]:
    """Every directory that HOLDS sets, in resolution order.

    The frozen bundle has no project root: the assets are read from
    `_MEIPASS`. The ENEMIES root is the CANONICAL one --
    `src.anim.sets.enemies_root()` -- so there is ONE probe for it, the
    same one the runtime uses. The BOSSES root is the other one, and
    `src/anim/manifest.py::_sets_root` owns it.
    """
    meipass = getattr(sys, "_MEIPASS", None)
    base = Path(meipass) if meipass else _project_root()
    return [base / "Assets" / "sprites" / SET_DIR_NAMES[0], enemies_root()]


def resolve_set(name: str, root: Path | None = None) -> Path:
    """The directory of the set called `name`.

    An explicit `root` wins. Otherwise the name is resolved against every
    sets root, in order. Raises `SetNotFoundError` (a `ValueError`) when no
    root has it -- the CLIs catch `ValueError` and print an error instead of
    a traceback.

    The name must be a single path component: a name that could escape the
    root ("..", "a/b") is rejected, so the resolver can never hand back the
    excluded backup directory.
    """
    if name in ("", ".", "..") or "/" in name or "\\" in name:
        raise SetNotFoundError(f"invalid set name {name!r}")
    if root is not None:
        candidate = root / name
        if _is_set(candidate):
            return candidate
        raise SetNotFoundError(f"no set {name!r} under {root}")
    roots = sets_roots()
    for base in roots:
        candidate = base / name
        if _is_set(candidate):
            return candidate
    raise SetNotFoundError(f"no set {name!r} under {roots}")


def discover_sets(root: Path) -> list[Path]:
    """Every set under `root`, sorted by name.

    The scan is ONE level deep: the children of `root`. The manifests are
    NOT parsed here: discovery must not raise on a broken one -- the loader
    degrades to None for that.
    """
    if not root.is_dir():
        return []
    try:
        children = sorted(root.iterdir())
    except OSError:
        return []
    return [child for child in children if child.is_dir() and _is_set(child)]
