"""BLOQUE 75: what is a set, and what is not.

A directory is a SET iff it contains a `manifest.toml`. Nothing else is.

How the exclusion actually works: the scan is ONE level deep -- the CHILDREN
of a root. `_backup_pre_bloque_65` lives INSIDE `mine_asteroid/`, so the scan
never visits it: it is excluded by NESTING, not by the manifest rule. The two
`_new_reference_*.png` files are excluded because they are files, not
directories. This module never enumerates frames, so the `frame_*.png` naming
rule does not live here.
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


def test_an_unknown_set_raises_a_value_error_the_clis_catch():
    """The CLIs catch `ValueError`; `FileNotFoundError` would escape them.

    `run.py` and `audit.py` only catch `ValueError`, and `FileNotFoundError`
    is an `OSError`, so the resolver must raise a `ValueError` subclass or
    the CLI dies with a traceback instead of printing `error: ...`.
    """
    with pytest.raises(ValueError):
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


def test_a_underscore_directory_with_a_manifest_is_not_a_set(tmp_path):
    """The `_` rule needs a test that FAILS if the rule is removed.

    The shipped `_backup_pre_bloque_65` lives INSIDE `mine_asteroid/`, so the
    root scan never visits it: without this fixture the rule is untested, and
    deleting it leaves every other test green.
    """
    hidden = tmp_path / "_hidden_set"
    hidden.mkdir()
    (hidden / "manifest.toml").write_text(
        "[meta]\nname = 'HIDDEN'\n", encoding="utf-8"
    )
    assert {p.name for p in discover_sets(tmp_path)} == set()


def test_resolve_set_prefers_an_explicit_root(tmp_path):
    """An explicit root wins over the default roots.

    The default roots DO have a `scout` set, so this also proves the
    precedence rule itself.
    """
    here = tmp_path / "scout"
    here.mkdir()
    (here / "manifest.toml").write_text(
        "[meta]\nname = 'SCOUT'\n", encoding="utf-8"
    )
    assert resolve_set("scout", root=tmp_path) == here


def test_resolve_set_agrees_with_discovery_about_what_a_set_is(tmp_path):
    """One definition of "is a set": a directory without a manifest is not."""
    (tmp_path / "not_a_set").mkdir()
    with pytest.raises(ValueError):
        resolve_set("not_a_set", root=tmp_path)


def test_resolve_set_rejects_a_name_that_could_escape_the_root(tmp_path):
    """The name is a single path component: the resolver cannot escape.

    The ROOT itself is a set here, so a name that escapes into it WOULD
    resolve without the guard: this test has to go red if the guard is
    removed.
    """
    real = tmp_path / "real_set"
    real.mkdir()
    (real / "manifest.toml").write_text(
        "[meta]\nname = 'REAL'\n", encoding="utf-8"
    )
    (tmp_path / "manifest.toml").write_text(
        "[meta]\nname = 'ROOT'\n", encoding="utf-8"
    )
    with pytest.raises(ValueError):
        resolve_set("real_set/..", root=tmp_path)
    with pytest.raises(ValueError):
        resolve_set("..", root=tmp_path)
    with pytest.raises(ValueError):
        resolve_set("mine_asteroid/_backup_pre_bloque_65", root=tmp_path)


def test_discovery_degrades_when_the_root_cannot_be_read(monkeypatch, tmp_path):
    """L5: an unreadable root degrades to an empty list, it never raises.

    `iterdir()` can raise `PermissionError` (an `OSError`): the scan must
    swallow it instead of taking the caller down.
    """

    def boom(self: Path) -> list[Path]:
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(Path, "iterdir", boom)
    assert discover_sets(tmp_path) == []
