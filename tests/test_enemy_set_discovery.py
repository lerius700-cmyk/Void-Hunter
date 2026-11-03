"""BLOQUE 75: what is a set, and what is not.

A directory is a SET iff it contains a manifest.toml. A directory whose
name starts with "_" is never one (that is what excludes
`_backup_pre_bloque_65`), and a PNG that is not named `frame_*.png` is
not a frame (that is what excludes the two reference PNGs the generator
reads).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from sprite_pipeline.sets import discover_sets, resolve_set, sets_roots


@pytest.fixture(scope="module")
def enemies_root() -> Path:
    return ROOT / "Assets" / "sprites" / "enemies"


def test_the_two_roots_are_the_bosses_and_the_enemies():
    roots = [p.name for p in sets_roots()]
    assert roots == ["bosses", "enemies"]


def test_the_enemy_sets_are_discovered(enemies_root):
    found = {p.name for p in discover_sets(enemies_root)}
    assert found == {
        "scout",
        "cruiser",
        "drone",
        "heavy",
        "kamikaze",
        "sniper",
        "turret",
        "mine_asteroid",
    }


def test_the_backup_directory_is_not_a_set(enemies_root):
    found = {p.name for p in discover_sets(enemies_root)}
    assert "_backup_pre_bloque_65" not in found


def test_resolve_set_finds_an_enemy_by_name():
    assert resolve_set("scout").name == "scout"
    assert resolve_set("scout").parent.name == "enemies"


def test_resolve_set_finds_goliath():
    assert resolve_set("goliath").parent.name == "bosses"


def test_an_unknown_set_raises_file_not_found():
    with pytest.raises(FileNotFoundError):
        resolve_set("no_existe")


def test_discovery_does_not_crash_on_a_malformed_manifest(tmp_path):
    """L5: a broken manifest degrades, it never takes the caller down."""
    (tmp_path / "broken").mkdir()
    (tmp_path / "broken" / "manifest.toml").write_text(
        "this is not toml at all [[[", encoding="utf-8"
    )
    (tmp_path / "no_manifest").mkdir()
    found = {p.name for p in discover_sets(tmp_path)}
    assert "no_manifest" not in found
    assert "broken" in found  # discovery does not parse; the loader degrades
