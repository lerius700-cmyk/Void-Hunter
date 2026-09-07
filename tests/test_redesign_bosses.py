"""Tests for the GOLIATH boss redesign pipeline (BLOQUE 60).

Covers:
  - GOLIATH boss spec (5 states × 10 frames)
  - StateSpec / BossSpec dataclasses
"""
from __future__ import annotations

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
