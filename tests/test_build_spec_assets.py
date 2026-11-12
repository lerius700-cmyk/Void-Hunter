"""The binary must not carry a GENERATED file.

`keep kept - Lerius - soundtrack gameplay_lp600.wav` is not an asset: it
is the gameplay track with a 600 Hz lowpass applied, and the game
rebuilds it in a few seconds and caches it next to the executable
(`src/audio/lowpass_cache.py`). Shipping a copy of it inside the
binary cost 61 MB in every download, for a file the game can make on
its own.

There are TWO ways a generated WAV could get into the bundle, and both
have to stay closed:

* a literal entry in `datas` (the one BLOQUE 58.14 added);
* the glob over the Assets root, which pulls in every loose file there
  -- that one has to keep excluding `*_lp*`.

The ORIGINAL tracks are assets and they stay.

BLOQUE 75 (Task 3) adds the OTHER half of the bundle contract: the
`datas` of the spec have to carry the nine sets whose manifests the
runtime reads EVERY FRAME. After Phase 2 the enemy manifests are
load-bearing -- a bundle without them still runs, still draws the
enemies, and reports NOTHING.

So the check has to be SEMANTIC: it has to know what each `datas`
entry really takes and where it drops it. A substring hunt cannot do
that: the five `player_ships` entries of the spec contain the words
`"Assets" / "sprites"` too, so a spec that bundles NO sprites at all
would pass one.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "build.spec"

sys.path.insert(0, str(ROOT / "tools"))

from regen_status import BUNDLED_SETS  # noqa: E402

# Where the runtime looks for the manifests of a set.
SPRITES_ROOT = "Assets/sprites"


def _spec_text() -> str:
    return SPEC.read_text(encoding="utf-8")


# --- the `datas` of the spec, read SEMANTICALLY --------------------------
#
# `build.spec` is Python, but it cannot be executed: it imports
# PyInstaller, which is not installed everywhere the tests run. So it is
# PARSED with `ast`, and what each entry carries is read off the tree.


def _datas_elements(tree: ast.Module) -> list[ast.expr]:
    """The elements of the `datas=[...]` list of the spec."""
    elements: list[ast.expr] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for keyword in node.keywords:
            if keyword.arg == "datas" and isinstance(keyword.value, ast.List):
                elements.extend(keyword.value.elts)
    return elements


def _path_parts(node: ast.expr) -> list[str]:
    """The string constants of a `PROJECT_ROOT / "a" / "b"` chain, in order.

    `ast.walk` is BREADTH-FIRST, so it would hand the constants back
    out of order ("sprites", "Assets"). The chain is walked by hand,
    left to right.
    """
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        return _path_parts(node.left) + _path_parts(node.right)
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    return []


def _source_path(node: ast.expr) -> str | None:
    """The relative source path of a `datas` entry, or None."""
    expr = node
    if (
        isinstance(expr, ast.Call)
        and isinstance(expr.func, ast.Name)
        and expr.func.id == "str"
    ):
        if len(expr.args) != 1:
            return None
        expr = expr.args[0]
    parts = _path_parts(expr)
    return "/".join(parts) if parts else None


def _string_literal(node: ast.expr) -> str | None:
    """The value of a string literal, or None."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _datas_entries(spec_text: str) -> list[tuple[str, str]]:
    """(source relative path, destination) of every LITERAL `datas` entry.

    The star-unpacked comprehension over the loose files of the Assets
    ROOT has no literal path and is skipped: it carries no set
    directory.
    """
    entries: list[tuple[str, str]] = []
    for element in _datas_elements(ast.parse(spec_text)):
        if not isinstance(element, ast.Tuple) or len(element.elts) != 2:
            continue
        source = _source_path(element.elts[0])
        dest = _string_literal(element.elts[1])
        if source is None or dest is None:
            continue
        entries.append((source, dest))
    return entries


def _carries(entry: tuple[str, str], set_dir: str) -> bool:
    """Whether a `datas` entry carries `set_dir` where the runtime looks.

    Two things have to hold. The source has to BE the set directory or
    a directory that CONTAINS it -- a file never contains a directory,
    which is why the five `player_ships` entries carry no set. And the
    set has to LAND where the runtime reads it: the entry copies the
    source under the destination, so the set lands at the destination
    plus the part of `set_dir` that is below the source.

    That SECOND rule is the whole rule. It is what makes a symmetric
    entry legitimate: `("Assets", "Assets")` drops
    `Assets/sprites/bosses/goliath` exactly where the runtime reads it.

    BLOQUE 75 (follow-up 3.2): the rule used to ALSO demand that the
    DESTINATION be under `Assets/sprites`. That was stricter than
    needed, and it rejected a legitimate entry -- bundling the whole
    Assets tree into itself -- for a reason that had nothing to do with
    the sets.
    """
    source, dest = entry
    if source != set_dir and not set_dir.startswith(source + "/"):
        return False
    relative = set_dir[len(source) :].strip("/")
    landed = dest if not relative else f"{dest}/{relative}"
    return landed == set_dir


def _uncovered_sets(spec_text: str) -> list[str]:
    """The sets that no `datas` entry carries into the bundle."""
    entries = _datas_entries(spec_text)
    return [
        set_dir
        for set_dir in BUNDLED_SETS
        if not any(_carries(entry, set_dir) for entry in entries)
    ]


def _replace_datas_entry(spec_text: str, source: str, replacement: str | None) -> str:
    """The spec text with the `datas` entry of `source` replaced or removed.

    The entry is LOCATED with `ast`: the spec is Python, and a line
    that happens to contain the same words is not the entry.

    EVERY entry of that source is removed, not only the first one: a
    directory that is listed twice is a duplicate, and a mutation that
    removes one of the two copies would not remove the directory at
    all -- the check would go on passing, and the mutation would prove
    nothing.
    """
    lines = spec_text.splitlines(keepends=True)
    removed = 0
    while True:
        for element in _datas_elements(ast.parse("".join(lines))):
            if not isinstance(element, ast.Tuple) or len(element.elts) != 2:
                continue
            if _source_path(element.elts[0]) != source:
                continue
            start = element.lineno - 1
            end = element.end_lineno
            if replacement is None:
                del lines[start:end]
            else:
                ending = "\n" if "".join(lines[start:end]).endswith("\n") else ""
                lines[start:end] = [replacement.rstrip("\n") + ending]
            removed += 1
            break
        else:
            break
    if removed == 0:
        raise AssertionError(f"build.spec has no datas entry for {source}")
    return "".join(lines)


def test_no_generated_wav_is_bundled_as_a_literal_entry():
    """No `datas` entry names a `*_lp*.wav`."""
    text = _spec_text()
    offenders = [
        name
        for name in re.findall(r'"([^"]+\.wav)"', text)
        if "_lp" in name.lower()
    ]
    assert not offenders, (
        f"the spec still bundles generated tracks: {offenders}. The game "
        "rebuilds and caches them next to the executable."
    )


def test_the_glob_over_the_assets_root_keeps_excluding_them():
    """The glob must not pull a generated WAV back in."""
    text = _spec_text()
    assert 'glob("*")' in text, (
        "the glob over the Assets root is gone: the loose runtime assets "
        "(the music, the painted background) would leave the binary"
    )
    assert '"_lp" not in p.name' in text, (
        "the glob over Assets/* would pull a generated WAV back into the "
        "bundle"
    )


def test_the_original_tracks_are_still_bundled():
    """The real music still goes in through the glob."""
    text = _spec_text()
    assert 'glob("*")' in text
    assets_root = ROOT / "Assets"
    for name in (
        "keep kept - Lerius - soundtrack gameplay.wav",
        "pantalla principal.wav",
    ):
        assert (assets_root / name).is_file(), (
            f"{name} is missing from the Assets root, so it cannot be bundled"
        )
        assert "_lp" not in name


# The paths that the bundle does NOT have to carry.
#
# BLOQUE 75 (follow-up 3.6): both are REVIEW artefacts -- a contact
# sheet of GOLIATH's frames and a backup of the mine's old art. Nothing
# in `src/` reads either of them, and they were 90 KB of download for
# every player of the .exe. They live in `docs/references/` now, which is
# not bundled.
#
# The bundle takes the sprites tree WHOLE, so the guarantee is
# STRUCTURAL: what is not under `Assets/sprites` cannot travel.
DEV_ONLY_PATHS = (
    "Assets/sprites/bosses/goliath/spritesheet_goliath_64b.png",
    "Assets/sprites/enemies/mine_asteroid/_backup_pre_bloque_65",
)


def _carries_file(entry: tuple[str, str], path: str) -> bool:
    """Whether a `datas` entry carries the FILE at `path` where it is.

    The entry copies the source under the destination: the file lands at
    the destination plus the part of its path that is below the source.
    A file that IS the source lands at the destination under its own
    name.
    """
    source, dest = entry
    if path == source:
        return f"{dest}/{source.rsplit('/', 1)[-1]}" == path
    if not path.startswith(source + "/"):
        return False
    relative = path[len(source) :].strip("/")
    landed = dest if not relative else f"{dest}/{relative}"
    return landed == path


# The STAGING area of the sprite pipeline: the sources the dev tools
# post-process into the live art. Nothing in `src/` opens it.
STAGING_REL = SPRITES_ROOT + "/redesign"


def test_the_staging_area_is_not_carried() -> None:
    """`Assets/sprites/redesign/` does NOT travel inside the .exe.

    BLOQUE 75 (follow-up 3.6): it is 465 files (7.3 MB) of AI
    generation output -- 3.3% of every download -- and the game reads
    the POST-PROCESSED frames, not the sources. The dev tools under
    `tools/redesign_*/` are the only readers, and `tools/` is not
    bundled.
    """
    entries = _datas_entries(_spec_text())
    for source, _dest in entries:
        assert source != STAGING_REL and not source.startswith(STAGING_REL + "/"), (
            f"the spec carries the staging area again: {source}"
        )
    staging = ROOT / STAGING_REL
    assert staging.is_dir(), f"{STAGING_REL} is not there any more"
    for path in sorted(staging.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix()
        assert not any(_carries_file(entry, rel) for entry in entries), rel


def test_every_sprite_file_is_carried_by_some_entry() -> None:
    """Not one file of the sprites tree is left behind.

    Taking the tree BY SUBTREE is what makes the staging area
    excludable -- and it opens a hole: a subtree that somebody adds and
    forgets would not travel, and the .exe would lose art in silence.

    This test closes the hole: EVERY file of the tree, except the
    declared staging area, has to be carried by some entry, exactly
    where it is now.
    """
    entries = _datas_entries(_spec_text())
    sprites = ROOT / SPRITES_ROOT
    missing: list[str] = []
    for path in sorted(sprites.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix()
        if rel.startswith(STAGING_REL + "/"):
            continue
        if not any(_carries_file(entry, rel) for entry in entries):
            missing.append(rel)
    assert not missing, (
        f"these files of the sprites tree do not travel inside the .exe: "
        f"{missing[:10]} -- the .exe would lose that art in silence"
    )


def test_the_spec_really_takes_the_sprites_tree_by_subtree() -> None:
    """The guarantee above rests on THIS: the tree travels by subtree.

    If the spec ever goes back to taking `Assets/sprites` as a whole,
    the staging area travels with it again -- and the test above would
    be a guarantee about nothing.
    """
    entries = _datas_entries(_spec_text())
    whole_tree = [
        source
        for source, _dest in entries
        if source == SPRITES_ROOT
    ]
    assert not whole_tree, (
        "the spec takes the sprites tree as a whole again: the staging "
        "area would travel with it"
    )


def test_a_symmetric_datas_entry_carries_the_sets() -> None:
    """`("Assets", "Assets")` is a LEGITIMATE entry.

    BLOQUE 75 (follow-up 3.2): the rule was stricter than needed. It
    demanded that the DESTINATION be under `Assets/sprites`, so an
    entry that bundles the whole Assets tree into itself was rejected --
    even though it drops every set exactly where the runtime reads it.

    The rule has to accept it without opening a hole: an entry that
    does NOT land the set where the runtime reads it still carries
    nothing, and that is what the mutation tests below prove.
    """
    entry = ("Assets", "Assets")
    for set_dir in BUNDLED_SETS:
        assert _carries(entry, set_dir), set_dir


def test_an_entry_that_lands_the_set_in_the_wrong_place_carries_nothing() -> None:
    """The symmetric entry is legal; a MISPLACED one is not.

    This is the other half of 3.2: relaxing the rule must not open the
    hole that the rule was closing. An entry that copies the Assets tree
    somewhere else carries no set, because the runtime would not find
    the manifest where it reads it.
    """
    entry = ("Assets", "Elsewhere")
    for set_dir in BUNDLED_SETS:
        assert not _carries(entry, set_dir), set_dir


def test_the_bundle_carries_the_manifest_of_every_set():
    """The `datas` of the spec really carry the nine sets.

    The check is SEMANTIC: it reads what each `datas` entry takes and
    where it drops it, and it asks whether the nine set directories
    land where the runtime reads them. A substring hunt cannot do
    this -- the five `player_ships` entries contain the words
    `"Assets" / "sprites"` too, so a spec that bundles NO sprites at
    all would pass one.

    The manifests also have to be IN the source tree: a set directory
    with no `manifest.toml` in it is a directory that reaches the
    bundle empty.
    """
    _assert_the_bundle_carries_every_set(_spec_text())


def _assert_the_bundle_carries_every_set(spec_text: str) -> list[str]:
    """THE check, as a function: the mutation tests call THIS.

    BLOQUE 75 (follow-up 3.3): the three mutation tests below used to
    assert on the shared PREDICATE (`_uncovered_sets`) instead of
    calling the main check. A test that does not call the function it
    is protecting cannot detect that the function broke -- it was a
    second copy of the logic, free to drift from the first one.

    It raises `AssertionError` when the spec does not carry the sets,
    and returns the missing ones so the caller can say WHICH.
    """
    missing = _uncovered_sets(spec_text)
    assert not missing, (
        f"the `datas` of build.spec do not carry {missing}: the frozen "
        "build would lose those manifests and the runtime would fall "
        "back silently -- with no error anywhere."
    )
    for set_dir in BUNDLED_SETS:
        source = ROOT / Path(set_dir)
        assert (source / "manifest.toml").is_file(), set_dir
        assert (source / "anchors.toml").is_file(), set_dir
    return missing


_BOSSES_ENTRY = "Assets/sprites/bosses"
_ENEMIES_ENTRY = "Assets/sprites/enemies"
_SPRITE_SUBTREES = (
    "Assets/sprites/asteroids",
    "Assets/sprites/bosses",
    "Assets/sprites/enemies",
    "Assets/sprites/player_rotation",
    "Assets/sprites/player_ships",
)


def test_the_check_notices_a_spec_that_drops_the_enemies_tree():
    """M1: the enemies tree is gone from the bundle.

    The hole this file exists to close: with this spec the bundle
    loses the 16 enemy manifests, the enemies fall back silently, and
    a substring check would not have noticed.

    BLOQUE 75 (follow-up 3.3): this calls the MAIN CHECK, not the shared
    predicate. A test that does not call the function it is protecting
    cannot detect that the function broke.
    """
    mutated = _replace_datas_entry(_spec_text(), _ENEMIES_ENTRY, None)
    with pytest.raises(AssertionError) as raised:
        _assert_the_bundle_carries_every_set(mutated)
    joined = str(raised.value)
    enemies = {set_dir for set_dir in BUNDLED_SETS if "/enemies/" in set_dir}
    assert enemies, "the bundle is expected to carry the enemy sets"
    for set_dir in enemies:
        assert set_dir in joined, (set_dir, joined)


def test_the_check_notices_a_spec_that_drops_every_set():
    """M2: none of the sprites subtrees is bundled.

    Not even the boss reaches the bundle. A substring check still
    passed here: the five `player_ships` entries carry the words
    `"Assets" / "sprites"`.
    """
    mutated = _spec_text()
    for subtree in _SPRITE_SUBTREES:
        mutated = _replace_datas_entry(mutated, subtree, None)
    with pytest.raises(AssertionError) as raised:
        _assert_the_bundle_carries_every_set(mutated)
    joined = str(raised.value)
    for set_dir in BUNDLED_SETS:
        assert set_dir in joined, (set_dir, joined)


def test_the_check_notices_a_spec_that_drops_the_boss():
    """M3: the boss is left out and the enemies are bundled."""
    mutated = _replace_datas_entry(_spec_text(), _BOSSES_ENTRY, None)
    with pytest.raises(AssertionError) as raised:
        _assert_the_bundle_carries_every_set(mutated)
    assert "Assets/sprites/bosses/goliath" in str(raised.value)
