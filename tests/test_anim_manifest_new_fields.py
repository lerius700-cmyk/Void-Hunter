"""BLOQUE 75: the manifest grows the fields the enemy sets need.

`distinct`, `cut_margin` and `clip.canvas` are USED in Phase 1. `mode` and
`on_end` are PARSED but not enforced yet: enforcing them now would reject
GOLIATH's own manifest, which declares neither.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.anim.manifest import ManifestError, load_set


def _write(tmp_path: Path, body: str) -> None:
    set_dir = tmp_path / "probe"
    set_dir.mkdir(parents=True, exist_ok=True)
    (set_dir / "manifest.toml").write_text(body, encoding="utf-8")


def test_the_new_fields_are_parsed(tmp_path):
    _write(
        tmp_path,
        '[meta]\n'
        'name = "PROBE"\n'
        'canvas = [32, 32]\n'
        'anchor = [16, 16]\n'
        'cut_margin = 0\n'
        '\n'
        '[[clips]]\n'
        'id = "idle"\n'
        'frames = 10\n'
        'fps = 12.5\n'
        'distinct = 3\n'
        'canvas = [16, 16]\n'
        'mode = "variants"\n'
        'on_end = "reset"\n'
        '\n'
        '[[parts]]\n'
        'id = "body"\n'
        'draw = "frames"\n',
    )
    anim_set = load_set("probe", root=tmp_path)
    clip = anim_set.clip("idle")
    assert anim_set.cut_margin == 0
    assert clip.distinct == 3
    assert clip.canvas == (16, 16)
    assert clip.mode == "variants"
    assert clip.on_end == "reset"


def test_on_end_is_derived_from_loop_when_it_is_not_declared(tmp_path):
    _write(
        tmp_path,
        '[meta]\n'
        'name = "PROBE"\n'
        'canvas = [32, 32]\n'
        '\n'
        '[[clips]]\n'
        'id = "loops"\n'
        'frames = 2\n'
        'loop = true\n'
        '\n'
        '[[clips]]\n'
        'id = "holds"\n'
        'frames = 2\n'
        'loop = false\n'
        '\n'
        '[[parts]]\n'
        'id = "body"\n'
        'draw = "frames"\n',
    )
    anim_set = load_set("probe", root=tmp_path)
    assert anim_set.clip("loops").on_end == "loop"
    assert anim_set.clip("holds").on_end == "hold"


def test_goliath_is_unchanged():
    """The control group: no new field is declared, so nothing changes."""
    anim_set = load_set("goliath")
    assert anim_set.cut_margin is None
    for clip in anim_set.clips.values():
        assert clip.distinct is None
        assert clip.canvas is None
        assert clip.mode == "sequence"
    assert anim_set.clip("phase1_idle").on_end == "loop"
    assert anim_set.clip("death").on_end == "hold"


def test_a_malformed_cut_margin_raises_manifest_error(tmp_path):
    _write(
        tmp_path,
        '[meta]\n'
        'name = "PROBE"\n'
        'canvas = [32, 32]\n'
        'cut_margin = "nope"\n'
        '\n'
        '[[clips]]\n'
        'id = "idle"\n'
        'frames = 2\n'
        '\n'
        '[[parts]]\n'
        'id = "body"\n'
        'draw = "frames"\n',
    )
    with pytest.raises(ManifestError):
        load_set("probe", root=tmp_path)


def test_a_bool_is_not_an_integer(tmp_path):
    """`True` would become 1, and for `distinct` that inverts the intent."""
    _write(
        tmp_path,
        '[meta]\n'
        'name = "PROBE"\n'
        'canvas = [32, 32]\n'
        'cut_margin = true\n'
        '\n'
        '[[clips]]\n'
        'id = "idle"\n'
        'frames = 2\n'
        '\n'
        '[[parts]]\n'
        'id = "body"\n'
        'draw = "frames"\n',
    )
    with pytest.raises(ManifestError):
        load_set("probe", root=tmp_path)


def test_a_negative_margin_is_rejected(tmp_path):
    """A negative margin would make the cut-off test never fire."""
    _write(
        tmp_path,
        '[meta]\n'
        'name = "PROBE"\n'
        'canvas = [32, 32]\n'
        'cut_margin = -3\n'
        '\n'
        '[[clips]]\n'
        'id = "idle"\n'
        'frames = 2\n'
        '\n'
        '[[parts]]\n'
        'id = "body"\n'
        'draw = "frames"\n',
    )
    with pytest.raises(ManifestError):
        load_set("probe", root=tmp_path)


def test_a_malformed_distinct_raises_manifest_error(tmp_path):
    """The loader fails LOUDLY, with the manifest's own error type."""
    _write(
        tmp_path,
        '[meta]\n'
        'name = "PROBE"\n'
        'canvas = [32, 32]\n'
        '\n'
        '[[clips]]\n'
        'id = "idle"\n'
        'frames = 2\n'
        'distinct = "nope"\n'
        '\n'
        '[[parts]]\n'
        'id = "body"\n'
        'draw = "frames"\n',
    )
    with pytest.raises(ManifestError):
        load_set("probe", root=tmp_path)
