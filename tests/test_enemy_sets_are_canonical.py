"""BLOQUE 76: the list of the enemy sets is ONE list, and there is a DOOR.

Two facts were kept apart on purpose, and this file holds the tests that
keep them apart:

  * the EXPECTATION -- `src/anim/sets.py::ENEMY_SETS`, the sets the repo
    MUST have, written by hand in ONE place;
  * the DISCOVERY -- `src/anim/sets.py::discover_enemy_sets()`, the sets
    that ARE on disk.

The DOOR is `enemy_sets_mismatch()`: the gate requires the two to
coincide. Without it, a new enemy (BOMBER) could land on the disk with
its art, its manifest and its anchors, and be a PASSENGER: nobody would
draw it, nobody would audit it, nobody would report it, nobody would
demand it from the bundle -- and the gate would be GREEN.

The rule of the phase: a guarantee the check cannot see is not a
guarantee, it is a hypothesis. So every check below can fail.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.anim import sets as sets_module
from src.anim.sets import ENEMY_SETS, clear_enemy_sets_cache, enemy_sets_mismatch

# The kinds that have NO set, by design. CARRIER is a big ship that draws
# its own art and SUB_BOSS is the "Wolfen" dart, which keeps its own
# 4-direction sprites.
KINDS_WITHOUT_A_SET = {"carrier", "sub_boss"}

# The files the declaration may live in. The whole repository is scanned:
# a list written in a place nobody thought about is exactly the failure
# this test exists to catch.
SCANNED_DIRS = ("src", "tools", "tests")
SCANNED_FILES = ("main.py",)


# ---------------------------------------------------------------------------
# The relation with EnemyKind
# ---------------------------------------------------------------------------


def test_every_set_is_an_enemy_kind() -> None:
    """Every set is a type of enemy."""
    from src.entities.enemies.enemy import EnemyKind

    kinds = {kind.value for kind in EnemyKind}
    assert set(ENEMY_SETS) <= kinds, (
        f"these sets are not EnemyKinds: {sorted(set(ENEMY_SETS) - kinds)}"
    )


def test_the_kinds_without_a_set_are_declared() -> None:
    """CARRIER and SUB_BOSS have no set, BY DESIGN.

    The relation ("every set is a type, and every type without a set is
    one of the two declared") was an oral convention nobody verified, and
    it is the kind of thing that breaks in silence when a type is added.
    Now it is a test: adding an EnemyKind fails here until somebody
    decides whether it has a set. The decision, not the default, is the
    point.
    """
    from src.entities.enemies.enemy import EnemyKind

    kinds = {kind.value for kind in EnemyKind}
    without_set = kinds - set(ENEMY_SETS)
    assert without_set == KINDS_WITHOUT_A_SET, (
        "types without a set that nobody declared: "
        f"{sorted(without_set - KINDS_WITHOUT_A_SET)}"
    )


# ---------------------------------------------------------------------------
# The DOOR
# ---------------------------------------------------------------------------


def test_the_door_is_closed_on_the_real_tree() -> None:
    """The discovery and the expectation coincide, right now."""
    mismatch = enemy_sets_mismatch()
    assert mismatch == {"faltan_en_disco": [], "sobran_en_disco": []}, mismatch


def _fake_set(root: Path, name: str) -> None:
    """A directory that IS a set, by the only rule there is."""
    directory = root / name
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "manifest.toml").write_text(
        '[meta]\nname = "FAKE"\nversion = 1\ncanvas = [32, 32]\nanchor = [16, 16]\n',
        encoding="utf-8",
    )


def test_the_door_names_a_set_that_is_on_disk_and_not_declared(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A set nobody declared has to be NAMED, not ignored.

    This is the BOMBER case: the art lands, the manifest lands, and
    without the door it would be a passenger that nobody draws, audits,
    reports or demands.
    """
    _fake_set(tmp_path, "bomber")
    monkeypatch.setattr(sets_module, "enemies_root", lambda: tmp_path)
    clear_enemy_sets_cache()
    try:
        mismatch = enemy_sets_mismatch()
    finally:
        clear_enemy_sets_cache()

    assert mismatch["sobran_en_disco"] == ["bomber"], mismatch
    # Every declared set is missing too, because the fake root has none.
    assert mismatch["faltan_en_disco"] == sorted(ENEMY_SETS), mismatch


def test_the_door_names_a_set_that_is_declared_and_not_on_disk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A set that was declared and is not on disk has to be NAMED."""
    monkeypatch.setattr(sets_module, "enemies_root", lambda: tmp_path)
    clear_enemy_sets_cache()
    try:
        mismatch = enemy_sets_mismatch()
    finally:
        clear_enemy_sets_cache()

    assert mismatch["faltan_en_disco"] == sorted(ENEMY_SETS), mismatch
    assert mismatch["sobran_en_disco"] == [], mismatch


def test_the_door_ignores_a_directory_that_is_not_a_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A directory with no manifest is not a set, and a "_" one never is.

    Both rules are the ones the discovery already had; the door has to
    not invent a third.
    """
    (tmp_path / "not_a_set").mkdir()
    (tmp_path / "_backup").mkdir()
    (tmp_path / "_backup" / "manifest.toml").write_text("[meta]\n", encoding="utf-8")
    monkeypatch.setattr(sets_module, "enemies_root", lambda: tmp_path)
    clear_enemy_sets_cache()
    try:
        found = sets_module.discover_enemy_sets()
    finally:
        clear_enemy_sets_cache()

    assert found == (), found


def test_the_cache_can_be_dropped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A cache that cannot be dropped is a lie.

    The discovery is memoized because the runtime asks for it on the hot
    path. But a set that lands on the disk has to be visible to the very
    next question -- so the memoization has to have a door too.
    """
    monkeypatch.setattr(sets_module, "enemies_root", lambda: tmp_path)
    clear_enemy_sets_cache()
    try:
        assert sets_module.discover_enemy_sets() == ()
        _fake_set(tmp_path, "bomber")
        assert sets_module.discover_enemy_sets() == (), (
            "the discovery did not see the new set: the cache was not dropped"
        )
        clear_enemy_sets_cache()
        assert sets_module.discover_enemy_sets() == ("bomber",)
    finally:
        clear_enemy_sets_cache()


# ---------------------------------------------------------------------------
# The list is written in ONE place
# ---------------------------------------------------------------------------


def _declarations_in(path: Path) -> list[tuple[int, list[str]]]:
    """The list declarations of a file: (line, the names it declares).

    A DECLARATION is a tuple/list/set literal that holds EVERY canonical
    name. Two things are deliberately NOT declarations:

      * an enum member -- `EnemyKind` names the TYPES of enemy, and the
        spec says they are a different truth (D5);
      * a PARTIAL list -- a literal with seven of the eight names is not
        "the list", it is a subset with a reason (the mine is not a
        standard ship: its clips are static and it has its own tests).
        A subset that names every set EXCEPT one would be a declaration,
        and the eight-name rule catches exactly that.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return []
    found: list[tuple[int, list[str]]] = []
    canonical = set(ENEMY_SETS)
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Tuple, ast.List, ast.Set)):
            continue
        names = {
            element.value
            for element in node.elts
            if isinstance(element, ast.Constant) and isinstance(element.value, str)
        }
        overlap = sorted(names & canonical)
        if len(overlap) == len(canonical):
            found.append((node.lineno, overlap))
    return found


def _python_files() -> list[Path]:
    files: list[Path] = []
    for directory in SCANNED_DIRS:
        files.extend(sorted((ROOT / directory).rglob("*.py")))
    for name in SCANNED_FILES:
        files.append(ROOT / name)
    return [path for path in files if path.is_file()]


def test_the_list_is_declared_in_one_place_only() -> None:
    """Only `src/anim/sets.py` may declare the list of the enemy sets.

    The list used to be written in fourteen places. A copy is a second
    truth, and the second truth can go stale in silence: a set added to
    the canonical list would not reach the fourteen copies, and the game
    would keep drawing the old eight while every test stayed green.
    """
    declarations: dict[str, list[tuple[int, list[str]]]] = {}
    for path in _python_files():
        found = _declarations_in(path)
        if found:
            declarations[path.relative_to(ROOT).as_posix()] = found

    assert set(declarations) == {"src/anim/sets.py"}, (
        "the list of the enemy sets is declared in more than one place: "
        f"{sorted(declarations)} -- import it from `src.anim.sets` instead "
        "of writing it again"
    )


def test_the_canonical_list_is_not_empty_and_has_no_duplicates() -> None:
    """The expectation is a list of NAMES, and a name twice is a bug."""
    assert ENEMY_SETS, "the canonical list of the enemy sets is empty"
    assert len(set(ENEMY_SETS)) == len(ENEMY_SETS), (
        f"the canonical list has a duplicate: {sorted(ENEMY_SETS)}"
    )
    assert all(name and not name.startswith("_") for name in ENEMY_SETS), (
        f"the canonical list has an invalid name: {list(ENEMY_SETS)}"
    )
