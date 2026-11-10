"""BLOQUE 76: the canonical list of the enemy sets.

TWO truths, and they never mix:

  * ENEMY_SETS -- the EXPECTATION: the sets the repo MUST have. It is a
    fact of the project, written BY HAND, in ONE place. It is NOT derived
    from the disk: derived, the gate would have nothing to compare
    against and the guarantee would be empty.

  * discover_enemy_sets() -- the DISCOVERY: the sets that ARE there, read
    from the directory. It is what the runtime asks to decide whether an
    enemy has a sprite.

The DOOR that joins them lives in tools/sprite_pipeline/gate.py: it
requires the two to match.

This module lives in src/ (and not in tools/) for a hard reason: the
frozen build does not bundle tools/, and main.py --check-pipeline has to
run INSIDE the .exe.
"""
from __future__ import annotations

import functools
import sys
from pathlib import Path

# The EXPECTATION. The eight enemy sets the repo must have.
#
# It is written BY HAND on purpose (spec D2): a list derived from the disk
# would make the gate's door tautological -- the gate would compare the
# disk against itself and always be green. The door is only a door if the
# two sides can disagree.
ENEMY_SETS: tuple[str, ...] = (
    "scout",
    "cruiser",
    "drone",
    "heavy",
    "kamikaze",
    "sniper",
    "turret",
    "mine_asteroid",
)


def _is_set(path: Path) -> bool:
    """ONE definition of "is a set": no "_" prefix and a manifest.toml.

    The manifest is NOT parsed here: the discovery must not raise on a
    broken one -- the loader degrades to None for that.
    """
    if path.name.startswith("_"):
        return False
    return (path / "manifest.toml").is_file()


@functools.lru_cache(maxsize=1)
def enemies_root() -> Path:
    """Where the enemy sets live.

    The SAME probe the bosses use (`src/anim/manifest.py::_sets_root`),
    for the other root:

        running from source: <project root>/Assets/sprites/enemies
        frozen (PyInstaller):  <_MEIPASS>/Assets/sprites/enemies

    It is resolved on CALL, never at import time: a frozen build never
    needs the source tree.

    BLOQUE 75 (fix round 1): the resolution is MEMOIZED. The root was
    re-resolved from the filesystem once per ENEMY, per FRAME -- the
    player was cached but the root was not -- and the resolution costs
    ~72-90 us on Windows. The cache keeps the "resolved on call" property
    (the first call still happens at RUNTIME, so a frozen build still
    reads `_MEIPASS`), and it collapses the cost to one resolution per
    process.
    """
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass) / "Assets" / "sprites" / "enemies"
    return (
        Path(__file__).resolve().parent.parent.parent
        / "Assets"
        / "sprites"
        / "enemies"
    )


@functools.lru_cache(maxsize=1)
def discover_enemy_sets() -> tuple[str, ...]:
    """The sets that ARE on disk, sorted by name.

    The scan is ONE level deep: the children of the enemies root. The
    manifests are NOT parsed here: the discovery must not raise on a
    broken one -- the loader degrades to None.

    The result is MEMOIZED (spec D3): the runtime asks for it on the hot
    path. `clear_enemy_sets_cache()` drops it when the disk changes.
    """
    root = enemies_root()
    if not root.is_dir():
        return ()
    try:
        children = sorted(root.iterdir())
    except OSError:
        return ()
    return tuple(
        child.name for child in children if child.is_dir() and _is_set(child)
    )


@functools.lru_cache(maxsize=1)
def enemy_set_lookup() -> frozenset[str]:
    """The DISCOVERY as a set, for the O(1) membership test of the hot path.

    The runtime asks "does this enemy kind have a set?" once per enemy,
    per frame. A tuple would be a linear scan; a frozenset is a hash
    lookup. Same truth, same cache, same invalidation hook.
    """
    return frozenset(discover_enemy_sets())


def clear_enemy_sets_cache() -> None:
    """Drop the cached discovery.

    The discovery is cached because the runtime reads it on the hot path,
    but a cache that cannot be dropped is a lie: a set added to the disk
    would stay invisible for the life of the process. Everything that
    caches the discovery is cleared here -- the frozenset view included,
    or the view would keep the stale answer.
    """
    discover_enemy_sets.cache_clear()
    enemy_set_lookup.cache_clear()


def enemy_sets_mismatch() -> dict[str, list[str]]:
    """{faltan_en_disco, sobran_en_disco}: where the expectation and the
    discovery do not coincide. Empty = everything is fine.

    The gate prints it and fails with this. A new set on disk that was
    not declared appears in "sobran_en_disco"; a declared set that is not
    on disk appears in "faltan_en_disco".
    """
    on_disk = set(discover_enemy_sets())
    expected = set(ENEMY_SETS)
    return {
        "faltan_en_disco": sorted(expected - on_disk),
        "sobran_en_disco": sorted(on_disk - expected),
    }
