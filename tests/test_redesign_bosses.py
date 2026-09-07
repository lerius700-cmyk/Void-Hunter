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
