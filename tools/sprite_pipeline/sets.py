"""BLOQUE 75: where the animated sets live.

A directory is a SET iff it contains a `manifest.toml`. Nothing else is.
That single rule is what keeps `_backup_pre_bloque_65` (no manifest) and
the two loose reference PNGs (not named `frame_*.png`) out of the
pipeline, without a heuristic that could get it wrong.

The two roots are probed in order: the bosses first (GOLIATH), then the
enemies. The frozen build resolves the same way: the bundle is extracted
to `_MEIPASS` and the Assets are read from THERE.
"""
from __future__ import annotations

import sys
from pathlib import Path

SET_DIR_NAMES = ("bosses", "enemies")


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def sets_roots() -> list[Path]:
    """Every directory that HOLDS sets, in resolution order.

    The frozen bundle has no project root: the assets are read from
    `_MEIPASS`. This is the same probe `src/anim/manifest.py::_sets_root`
    uses, extended to the second root.
    """
    meipass = getattr(sys, "_MEIPASS", None)
    base = Path(meipass) if meipass else _project_root()
    return [base / "Assets" / "sprites" / name for name in SET_DIR_NAMES]


def resolve_set(name: str, root: Path | None = None) -> Path:
    """The directory of the set called `name`.

    An explicit `root` wins. Otherwise the name is resolved against every
    sets root, in order. Raises `FileNotFoundError` (an `OSError`) when no
    root has it -- the CLI catches it and prints an error instead of a
    traceback.
    """
    if root is not None:
        candidate = root / name
        if candidate.is_dir():
            return candidate
        raise FileNotFoundError(f"no set {name!r} under {root}")
    for base in sets_roots():
        candidate = base / name
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError(f"no set {name!r} under {sets_roots()}")


def discover_sets(root: Path) -> list[Path]:
    """Every set under `root`, sorted by name.

    A directory whose name starts with "_" is NEVER a set. A directory
    without a `manifest.toml` is not a set either. The manifests are NOT
    parsed here: discovery must not raise on a broken one -- the loader
    degrades to None for that.
    """
    if not root.is_dir():
        return []
    found: list[Path] = []
    for candidate in sorted(root.iterdir()):
        if not candidate.is_dir() or candidate.name.startswith("_"):
            continue
        if not (candidate / "manifest.toml").is_file():
            continue
        found.append(candidate)
    return found
