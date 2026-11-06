"""BLOQUE 75: the frozen bundle has to carry the manifests of ALL NINE sets.

After Phase 2 the enemy manifests are LOAD-BEARING at runtime: the
runtime reads them every frame to draw the enemies. Before Phase 2 only
GOLIATH's two files were verified, so a bundle that shipped the boss's
manifest and none of the enemies' would have passed the check -- and the
enemies would have fallen back silently, with no error anywhere.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from regen_status import frozen_assets_verified

SETS = (
    "Assets/sprites/bosses/goliath",
    "Assets/sprites/enemies/cruiser",
    "Assets/sprites/enemies/drone",
    "Assets/sprites/enemies/heavy",
    "Assets/sprites/enemies/kamikaze",
    "Assets/sprites/enemies/mine_asteroid",
    "Assets/sprites/enemies/scout",
    "Assets/sprites/enemies/sniper",
    "Assets/sprites/enemies/turret",
)


def _complete_entries() -> list[str]:
    entries: list[str] = []
    for set_dir in SETS:
        entries.append(f"{set_dir}/manifest.toml")
        entries.append(f"{set_dir}/anchors.toml")
    return entries


def test_a_bundle_with_every_set_is_verified() -> None:
    assert frozen_assets_verified(_complete_entries())


def test_a_bundle_without_an_enemy_manifest_is_not_verified() -> None:
    entries = [e for e in _complete_entries() if "enemies/scout/manifest.toml" not in e]
    assert not frozen_assets_verified(entries)


def test_a_bundle_with_only_the_boss_is_not_verified() -> None:
    entries = [e for e in _complete_entries() if "enemies/" not in e]
    assert not frozen_assets_verified(entries)


def test_a_bundle_without_the_anchors_is_not_verified() -> None:
    entries = [e for e in _complete_entries() if "anchors.toml" not in e]
    assert not frozen_assets_verified(entries)
