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
