"""BLOQUE 75 Fase 2: `mode` and `on_end` have a vocabulary.

Phase 1 PARSED these fields but did not enforce them, because enforcing
them on GOLIATH's manifest would have rejected it. Phase 2 enforces them,
and the enemy manifests are corrected to match what the runtime actually
does.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.anim.manifest import ManifestError, load_set


def _probe(root: Path, clips: str) -> Path:
    """Write a probe set under `root` and return the root that holds it.

    The probe is otherwise VALID: every `[meta]` field has a default, and
    the manifest declares one clip and one part. The only thing that can
    make it fail is the vocabulary itself, so the test bites for the
    reason it is about.
    """
    set_dir = root / "probe"
    set_dir.mkdir(parents=True, exist_ok=True)
    (set_dir / "manifest.toml").write_text(
        '[meta]\n'
        'name = "PROBE"\n'
        'canvas = [8, 8]\n'
        '\n'
        '[[clips]]\n'
        f'{clips}'
        '\n'
        '[[parts]]\n'
        'id = "body"\n'
        'draw = "frames"\n',
        encoding="utf-8",
    )
    return root


def test_goliath_still_loads():
    """GOLIATH declares neither `mode` nor `on_end`; it must keep loading."""
    anim_set = load_set("goliath")
    for clip in anim_set.clips.values():
        assert clip.mode == "sequence"
        assert clip.on_end in ("loop", "hold")


def test_the_mine_clips_are_static():
    """The mine never advances a frame: its clips are static."""
    anim_set = load_set("mine_asteroid", root=ROOT / "Assets" / "sprites" / "enemies")
    for clip in anim_set.clips.values():
        assert clip.loop is False, clip.id
        assert clip.on_end == "hold", clip.id


def test_a_variant_clip_declares_every_frame_as_distinct():
    anim_set = load_set("mine_asteroid", root=ROOT / "Assets" / "sprites" / "enemies")
    closed = anim_set.clip("closed")
    assert closed.mode == "variants"
    assert closed.distinct == closed.frames


def test_an_unknown_mode_is_rejected(tmp_path):
    set_dir = tmp_path / "probe"
    set_dir.mkdir()
    (set_dir / "manifest.toml").write_text(
        '[meta]\n'
        'name = "PROBE"\n'
        'canvas = [8, 8]\n'
        '\n'
        '[[clips]]\n'
        'id = "idle"\n'
        'frames = 2\n'
        'mode = "sequences"\n'
        '\n'
        '[[parts]]\n'
        'id = "body"\n'
        'draw = "frames"\n',
        encoding="utf-8",
    )
    with pytest.raises(ManifestError, match="mode"):
        load_set("probe", root=tmp_path)


# --- the rules the four tests above do not exercise on their own ---------
#
# The brief's four tests cover the vocabulary's ENTRY point (an unknown
# mode), the derivation that keeps GOLIATH loading, and the mine's real
# manifest. The rules below are the rest of the vocabulary: each one gets
# a test of its own, so none of them can be deleted without a red run.


def test_a_variant_clip_that_repeats_an_image_is_rejected(tmp_path):
    """`variants` means EVERY frame is a different image."""
    root = _probe(
        tmp_path,
        'id = "closed"\n'
        'frames = 10\n'
        'distinct = 3\n'
        'mode = "variants"\n',
    )
    with pytest.raises(ManifestError, match="variants"):
        load_set("probe", root=root)


def test_a_state_clip_with_more_than_one_frame_is_rejected(tmp_path):
    """`state` is one frame, chosen by the state and never advanced."""
    root = _probe(
        tmp_path,
        'id = "open1"\n'
        'frames = 2\n'
        'mode = "state"\n',
    )
    with pytest.raises(ManifestError, match="frames"):
        load_set("probe", root=root)


def test_an_archive_clip_may_not_declare_an_fps(tmp_path):
    """An archive clip is never played, so no fps applies to it.

    The rule is checked against the RAW entry: `Clip.fps` defaults to
    10.0, so a declared `fps = 10` and a defaulted one are the same
    value once the clip is parsed.
    """
    root = _probe(
        tmp_path,
        'id = "death"\n'
        'frames = 10\n'
        'mode = "archive"\n'
        'fps = 10\n',
    )
    with pytest.raises(ManifestError, match="fps"):
        load_set("probe", root=root)


def test_an_archive_clip_without_an_fps_loads(tmp_path):
    """The other side of the rule: the mine's `death` clip is exactly this."""
    root = _probe(
        tmp_path,
        'id = "death"\n'
        'frames = 10\n'
        'mode = "archive"\n',
    )
    anim_set = load_set("probe", root=root)
    assert anim_set.clip("death").mode == "archive"


def test_an_on_end_that_contradicts_loop_is_rejected(tmp_path):
    """`on_end` and `loop` have to agree.

    `on_end = "reset"` says the clip does not loop, so `loop` has to be
    false; `on_end = "loop"` says it does.
    """
    root = _probe(
        tmp_path,
        'id = "idle"\n'
        'frames = 2\n'
        'on_end = "reset"\n',
    )
    with pytest.raises(ManifestError, match="on_end"):
        load_set("probe", root=root)


def test_a_looping_clip_cannot_declare_a_one_shot_on_end(tmp_path):
    root = _probe(
        tmp_path,
        'id = "idle"\n'
        'frames = 2\n'
        'loop = false\n'
        'on_end = "loop"\n',
    )
    with pytest.raises(ManifestError, match="on_end"):
        load_set("probe", root=root)


def test_an_unknown_on_end_is_rejected(tmp_path):
    root = _probe(
        tmp_path,
        'id = "idle"\n'
        'frames = 2\n'
        'on_end = "restart"\n',
    )
    with pytest.raises(ManifestError, match="on_end"):
        load_set("probe", root=root)
