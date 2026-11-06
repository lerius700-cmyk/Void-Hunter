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
    destination has to drop it under `Assets/sprites`, which is where
    the runtime reads the manifests from.
    """
    source, dest = entry
    if source != set_dir and not set_dir.startswith(source + "/"):
        return False
    if dest != SPRITES_ROOT and not dest.startswith(SPRITES_ROOT + "/"):
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
    """
    lines = spec_text.splitlines(keepends=True)
    for element in _datas_elements(ast.parse(spec_text)):
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
        return "".join(lines)
    raise AssertionError(f"build.spec has no datas entry for {source}")


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
    missing = _uncovered_sets(_spec_text())
    assert not missing, (
        f"the `datas` of build.spec do not carry {missing}: the frozen "
        "build would lose those manifests and the runtime would fall "
        "back silently -- with no error anywhere."
    )
    for set_dir in BUNDLED_SETS:
        source = ROOT / Path(set_dir)
        assert (source / "manifest.toml").is_file(), set_dir
        assert (source / "anchors.toml").is_file(), set_dir


_BOSSES_ONLY = (
    '        (str(PROJECT_ROOT / "Assets" / "sprites" / "bosses"), '
    '"Assets/sprites/bosses"),\n'
)
_ENEMIES_ONLY = (
    '        (str(PROJECT_ROOT / "Assets" / "sprites" / "enemies"), '
    '"Assets/sprites/enemies"),\n'
)


def test_the_check_notices_a_spec_that_drops_the_enemies_tree():
    """M1: only the bosses are bundled and the enemies tree is gone.

    The hole this file exists to close: with this spec the bundle
    loses the 16 enemy manifests, the enemies fall back silently, and
    a substring check would not have noticed.
    """
    mutated = _replace_datas_entry(_spec_text(), SPRITES_ROOT, _BOSSES_ONLY)
    mutated = _replace_datas_entry(mutated, "Assets/sprites/enemies", None)
    missing = _uncovered_sets(mutated)
    enemies = {set_dir for set_dir in BUNDLED_SETS if "/enemies/" in set_dir}
    assert set(missing) == enemies, missing


def test_the_check_notices_a_spec_that_drops_every_set():
    """M2: the sprites tree is not bundled at all.

    Not even the boss reaches the bundle. A substring check still
    passed here: the five `player_ships` entries carry the words
    `"Assets" / "sprites"`.
    """
    mutated = _replace_datas_entry(_spec_text(), SPRITES_ROOT, None)
    mutated = _replace_datas_entry(mutated, "Assets/sprites/enemies", None)
    missing = _uncovered_sets(mutated)
    assert set(missing) == set(BUNDLED_SETS), missing


def test_the_check_notices_a_spec_that_drops_the_boss():
    """M3: only the enemies are bundled and the boss is left out."""
    mutated = _replace_datas_entry(_spec_text(), SPRITES_ROOT, _ENEMIES_ONLY)
    mutated = _replace_datas_entry(mutated, "Assets/sprites/enemies", None)
    missing = _uncovered_sets(mutated)
    assert missing == ["Assets/sprites/bosses/goliath"], missing
