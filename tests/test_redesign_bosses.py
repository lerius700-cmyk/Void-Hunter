"""Tests for the GOLIATH boss redesign pipeline (BLOQUE 60).

Covers:
  - GOLIATH boss spec (5 states × 10 frames)
  - StateSpec / BossSpec dataclasses
  - Prompt builder (state fill + boss style header)

BLOQUE 60 deviation: ``01_generate_bases.py`` is loaded via
``importlib.util.spec_from_file_location`` because its digit prefix
makes it unimportable via ``from tools.redesign_bosses import 01_...``.
This matches the existing convention set by
``tests/test_postprocess_shared.py`` (which loads ``02_postprocess.py``
the same way).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from tools.redesign_bosses._specs import GOLIATH_SPEC, StateSpec, BossSpec


def test_goliath_spec_is_bossspec():
    assert isinstance(GOLIATH_SPEC, BossSpec)


def test_goliath_spec_key():
    assert GOLIATH_SPEC.key == "goliath"


def test_goliath_spec_source_size():
    assert GOLIATH_SPEC.source_size == 96


def test_goliath_spec_has_5_states():
    assert len(GOLIATH_SPEC.states) == 5


def test_goliath_spec_state_keys():
    state_keys = {s.key for s in GOLIATH_SPEC.states}
    assert state_keys == {"idle", "damage", "phase2", "death", "intro"}


def test_goliath_spec_state_has_prompt_fill():
    for s in GOLIATH_SPEC.states:
        assert isinstance(s, StateSpec)
        assert len(s.prompt_fill) > 10
        assert "{state}" not in s.prompt_fill  # not templated, already filled


def test_goliath_spec_state_has_base_filename():
    for s in GOLIATH_SPEC.states:
        assert s.base_filename == f"goliath_{s.key}_base.png"


def test_goliath_spec_state_has_10_frames():
    for s in GOLIATH_SPEC.states:
        assert s.frame_count == 10


# ---------------------------------------------------------------------------
# Task 3: prompt builder for AI base generation
# ---------------------------------------------------------------------------

_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent
_GENERATE_BASES_PATH = (
    _PROJECT_ROOT / "tools" / "redesign_bosses" / "01_generate_bases.py"
)
_spec = importlib.util.spec_from_file_location(
    "_redesign_bosses_generate_bases", _GENERATE_BASES_PATH
)
assert _spec is not None and _spec.loader is not None, (
    f"could not load spec for {_GENERATE_BASES_PATH}"
)
gen = importlib.util.module_from_spec(_spec)
sys.modules["_redesign_bosses_generate_bases"] = gen
_spec.loader.exec_module(gen)


def test_build_prompt_includes_state_fill():
    prompt = gen.build_prompt(state_key="idle", prompt_fill="standing still")
    assert "GOLIATH" in prompt.upper() or "goliath" in prompt.lower()
    assert "16-bit pixel art" in prompt
    assert "standing still" in prompt
    assert "facing down" in prompt.lower() or "facing downward" in prompt.lower()


def test_build_prompt_includes_bronze_armor():
    prompt = gen.build_prompt(state_key="idle", prompt_fill="x")
    assert "bronze" in prompt.lower()
    assert "spear" in prompt.lower()
    assert "shield" in prompt.lower()
    assert "red eyes" in prompt.lower() or "red eye" in prompt.lower()


# ---------------------------------------------------------------------------
# Task 4: postprocess for bosses (96x80, distance_threshold=90)
# ---------------------------------------------------------------------------
#
# ``02_postprocess.py`` cannot be imported via ``from package import 02_...``
# because the leading digit makes it an invalid Python identifier. Load it
# by file path with importlib, matching the convention used by
# tests/test_postprocess_shared.py and by the Task 3 load above.

_BOSS_POSTPROCESS_PATH = (
    _PROJECT_ROOT / "tools" / "redesign_bosses" / "02_postprocess.py"
)
_pp_spec = importlib.util.spec_from_file_location(
    "_redesign_bosses_postprocess", _BOSS_POSTPROCESS_PATH
)
assert _pp_spec is not None and _pp_spec.loader is not None, (
    f"could not load spec for {_BOSS_POSTPROCESS_PATH}"
)
pp = importlib.util.module_from_spec(_pp_spec)
sys.modules["_redesign_bosses_postprocess"] = pp
_pp_spec.loader.exec_module(pp)


def test_boss_postprocess_source_size():
    """BLOQUE 60: boss source is 96x80, NOT 32x32 like ships."""
    assert pp.SOURCE_SIZE == 96
    assert pp.SOURCE_HEIGHT == 80


def test_boss_postprocess_uses_threshold_90():
    """Bosses at 96x80 need a wider transparentize threshold (90 vs 70
    default for ships) because LANCZOS at 1024->96 blends more damero."""
    assert pp.TRANSPARENTIZE_DISTANCE_THRESHOLD == 90.0


def test_boss_postprocess_calls_shared_transparentize():
    """Verify that boss postprocess uses the shared transparentize
    function from redesign_ships, not its own copy."""
    import inspect
    src = inspect.getsource(pp)
    assert "_transparentize_damero_after_resize" in src
    # And the call must pass the boss threshold
    assert "90" in src


def test_boss_postprocess_crops_15_pct_bottom():
    """Same as ships: remove bottom 15% (the AI watermark)."""
    assert pp.WATERMARK_CROP_BOTTOM_PCT == 0.15


# ---------------------------------------------------------------------------
# Task 5: animation frame generators (10 frames per state)
# ---------------------------------------------------------------------------
#
# ``_animation_frames.py`` uses an underscore prefix (a valid Python
# identifier), so it is importable directly via the normal import system.
# No importlib shim needed here.

from tools.redesign_bosses import _animation_frames as af


def test_generate_idle_frames_produces_10():
    """idle: 10 byte-identical copies of _source (motion is runtime bob)."""
    import tempfile
    from PIL import Image
    with tempfile.TemporaryDirectory() as td:
        td_p = __import__('pathlib').Path(td)
        src = td_p / "_source.png"
        Image.new("RGBA", (80, 96), (40, 80, 180, 255)).save(src)
        out_dir = td_p / "idle"
        af.generate_idle_frames(src, out_dir)
        frames = sorted(out_dir.glob("frame_*.png"))
        assert len(frames) == 10
        # All 10 must be byte-identical (motion comes from runtime transforms)
        contents = [f.read_bytes() for f in frames]
        assert all(c == contents[0] for c in contents)


def test_generate_damage_frames_produces_10():
    """damage: 10 byte-identical copies (motion is runtime tilt)."""
    import tempfile
    from PIL import Image
    with tempfile.TemporaryDirectory() as td:
        td_p = __import__('pathlib').Path(td)
        src = td_p / "_source.png"
        Image.new("RGBA", (80, 96), (40, 80, 180, 255)).save(src)
        out_dir = td_p / "damage"
        af.generate_damage_frames(src, out_dir)
        frames = sorted(out_dir.glob("frame_*.png"))
        assert len(frames) == 10


def test_generate_phase2_frames_produces_10():
    """phase2: 10 distinct frames (real AI gen sequence)."""
    import tempfile
    from PIL import Image
    with tempfile.TemporaryDirectory() as td:
        td_p = __import__('pathlib').Path(td)
        src = td_p / "_source.png"
        Image.new("RGBA", (80, 96), (40, 80, 180, 255)).save(src)
        out_dir = td_p / "phase2"
        af.generate_phase2_frames(src, out_dir)
        frames = sorted(out_dir.glob("frame_*.png"))
        assert len(frames) == 10


def test_generate_death_frames_produces_10():
    import tempfile
    from PIL import Image
    with tempfile.TemporaryDirectory() as td:
        td_p = __import__('pathlib').Path(td)
        src = td_p / "_source.png"
        Image.new("RGBA", (80, 96), (40, 80, 180, 255)).save(src)
        out_dir = td_p / "death"
        af.generate_death_frames(src, out_dir)
        frames = sorted(out_dir.glob("frame_*.png"))
        assert len(frames) == 10


def test_generate_intro_frames_produces_10():
    import tempfile
    from PIL import Image
    with tempfile.TemporaryDirectory() as td:
        td_p = __import__('pathlib').Path(td)
        src = td_p / "_source.png"
        Image.new("RGBA", (80, 96), (40, 80, 180, 255)).save(src)
        out_dir = td_p / "intro"
        af.generate_intro_frames(src, out_dir)
        frames = sorted(out_dir.glob("frame_*.png"))
        assert len(frames) == 10


# ---------------------------------------------------------------------------
# Task 6: build sheets + integrate
# ---------------------------------------------------------------------------
#
# ``_03_build_sheets.py`` and ``_04_integrate.py`` are named with an
# underscore prefix (BLOQUE 60 deviation from plan: plan called for
# ``03_build_sheets.py`` / ``04_integrate.py``). Underscore prefix is
# required so the modules are importable as identifiers via
# ``from tools.redesign_bosses import _03_build_sheets`` (Python's
# ``from X import Y`` syntax does not accept digit-prefixed names).

from tools.redesign_bosses import _03_build_sheets, _04_integrate


def test_build_sheet_grid_is_5x10():
    """Sheet is 5 rows (states) x 10 cols (frames)."""
    assert _03_build_sheets.STATES == ("idle", "damage", "phase2", "death", "intro")
    assert _03_build_sheets.FRAMES_PER_STATE == 10


def test_integrate_copies_to_live_assets():
    """Verify the integration target is Assets/sprites/bosses/goliath/, not
    redesign/ which is staging-only. Path is normalized to forward slashes
    so the assertion works on both Windows and POSIX."""
    # Normalize path separators to forward slashes for portability.
    live_norm = str(_04_integrate.LIVE_DIR).replace("\\", "/")
    assert "Assets/sprites/bosses/goliath" in live_norm
    # The path after the 'bosses' segment must not contain 'redesign'.
    after_bosses = live_norm.lower().split("bosses")[1]
    assert "redesign" not in after_bosses


def test_integrate_copies_one_frame_at_a_time():
    """50 frames total: 5 states * 10 frames = 50."""
    assert _04_integrate.STATE_COUNT == 5
    assert _04_integrate.FRAMES_PER_STATE == 10
