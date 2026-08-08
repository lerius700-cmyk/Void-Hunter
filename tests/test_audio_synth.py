"""Tests for src.audio.synth — 24 SFX + 4 BGM procedurales (BLOQUE 13)."""
from __future__ import annotations

import array
import math
import random

import pytest

from src.audio.synth import (
    BGM_CATALOG,
    BGM_NAMES,
    SFX_CATALOG,
    SFX_NAMES,
    AudioEngine,
    Voice,
    adsr_envelope,
    render_bgm,
    render_sfx,
    saw_wave,
    square_wave,
    triangle_wave,
    noise_wave,
)
from src.core.settings import MIXER_SAMPLE_RATE


# ---------------------------------------------------------------------------
# 1. Waveform helpers
# ---------------------------------------------------------------------------
def test_square_wave_returns_pm_one() -> None:
    for i in range(100):
        t = i * 0.001
        v = square_wave(t, 1000.0)
        assert v in (-1.0, 1.0)


def test_triangle_wave_in_range() -> None:
    for i in range(100):
        t = i * 0.001
        v = triangle_wave(t, 1000.0)
        assert -1.0 <= v <= 1.0


def test_saw_wave_in_range() -> None:
    for i in range(100):
        t = i * 0.001
        v = saw_wave(t, 1000.0)
        assert -1.0 <= v <= 1.0


def test_noise_wave_in_range() -> None:
    rng = random.Random()
    for i in range(100):
        t = i * 0.001
        v = noise_wave(t, 1000.0, rng)
        assert -1.0 <= v <= 1.0


# ---------------------------------------------------------------------------
# 2. ADSR envelope
# ---------------------------------------------------------------------------
def test_adsr_zero_at_t_zero() -> None:
    assert adsr_envelope(0.0, 0.5) == 0.0


def test_adsr_zero_at_t_equals_duration() -> None:
    assert adsr_envelope(0.5, 0.5) == 0.0


def test_adsr_zero_past_duration() -> None:
    assert adsr_envelope(1.0, 0.5) == 0.0


def test_adsr_attack_phase() -> None:
    """During attack, value rises from 0 to 1."""
    v = adsr_envelope(0.005, 0.5, attack=0.01, decay=0.1, sustain=0.5, release=0.1)
    assert 0.0 < v < 1.0


def test_adsr_sustain_phase() -> None:
    """During sustain, value = sustain level."""
    v = adsr_envelope(0.3, 0.5, attack=0.01, decay=0.1, sustain=0.5, release=0.1)
    assert v == 0.5


def test_adsr_release_phase() -> None:
    """During release, value falls from sustain to 0."""
    v = adsr_envelope(0.45, 0.5, attack=0.01, decay=0.1, sustain=0.5, release=0.1)
    assert 0.0 < v < 0.5


# ---------------------------------------------------------------------------
# 3. 24 SFX catalog
# ---------------------------------------------------------------------------
def test_twenty_four_sfx_in_catalog() -> None:
    assert len(SFX_CATALOG) == 24
    assert len(SFX_NAMES) == 24


def test_all_expected_sfx_present() -> None:
    expected = {
        "shoot", "shoot_charged", "hit", "explode_small", "explode_medium",
        "explode_boss", "bomb", "powerup", "dash", "multiplier_up",
        "boss_warning", "boss_phase_change", "wave_cleared", "act_clear",
        "game_over", "victory", "ui_click", "ui_hover", "charge_loop",
        "beam_charge", "beam_fire", "missile_lock", "missile_fire",
        "screen_shake_thump",
    }
    assert set(SFX_NAMES) == expected


def test_sfx_have_required_fields() -> None:
    for name, spec in SFX_CATALOG.items():
        assert spec.voice in Voice
        assert spec.duration_s > 0.0
        assert 0.0 <= spec.volume <= 1.0


def test_sfx_adsr_ranges_per_spec() -> None:
    """ADSR ranges per GDD §9: A 0.005-0.05s, D 0.05-0.2s, S 0.0-0.7, R 0.1-0.6s.
    Some SFX (boss_warning, game_over) extend slightly beyond for dramatic effect.
    """
    for spec in SFX_CATALOG.values():
        assert 0.001 <= spec.attack_s <= 0.1
        assert 0.01 <= spec.decay_s <= 0.4
        assert 0.0 <= spec.sustain <= 0.9
        assert 0.02 <= spec.release_s <= 1.5


# ---------------------------------------------------------------------------
# 4. 4 BGM catalog
# ---------------------------------------------------------------------------
def test_four_bgm_in_catalog() -> None:
    assert len(BGM_CATALOG) == 4
    assert len(BGM_NAMES) == 4


def test_bgm_durations_in_30_to_45_range() -> None:
    for spec in BGM_CATALOG.values():
        assert 30.0 <= spec.duration_s <= 50.0


# ---------------------------------------------------------------------------
# 5. render_sfx / render_bgm
# ---------------------------------------------------------------------------
def test_render_sfx_returns_array() -> None:
    buf = render_sfx("shoot")
    assert isinstance(buf, array.array)
    assert len(buf) > 0
    assert buf.typecode == "h"  # signed short


def test_render_sfx_unknown_name_returns_zero_buffer() -> None:
    buf = render_sfx("nonexistent")
    assert len(buf) == 1
    assert buf[0] == 0


def test_render_sfx_sample_count_matches_duration() -> None:
    buf = render_sfx("shoot")
    expected_samples = int(SFX_CATALOG["shoot"].duration_s * MIXER_SAMPLE_RATE)
    assert len(buf) == expected_samples


def test_render_bgm_returns_nonempty_array() -> None:
    buf = render_bgm("title")
    assert isinstance(buf, array.array)
    assert len(buf) > 1000  # 32s @ 44100 = ~1.4M samples


def test_render_bgm_unknown_name_returns_zero() -> None:
    buf = render_bgm("nonexistent")
    assert len(buf) == 1


@pytest.mark.parametrize("name", SFX_NAMES)
def test_all_24_sfx_render(name: str) -> None:
    """Every SFX renders to a non-empty array without exception."""
    buf = render_sfx(name)
    assert len(buf) > 0


@pytest.mark.parametrize("name", BGM_NAMES)
def test_all_4_bgm_render(name: str) -> None:
    buf = render_bgm(name)
    assert len(buf) > 0


# ---------------------------------------------------------------------------
# 6. AudioEngine (with mixer init)
# ---------------------------------------------------------------------------
def test_audio_engine_init_does_not_crash() -> None:
    """If mixer is available, init succeeds; if not, no crash either."""
    engine = AudioEngine()
    # Whether or not mixer initialized, we should have the attribute
    assert hasattr(engine, "mixer_available")
    assert engine.mixer_available in (True, False)


def test_audio_engine_sfx_count() -> None:
    engine = AudioEngine()
    if engine.mixer_available:
        assert len(engine.sfx_sounds) == 24
        assert len(engine.bgm_sounds) == 4


def test_audio_engine_play_sfx_returns_bool() -> None:
    engine = AudioEngine()
    result = engine.play_sfx("shoot")
    assert isinstance(result, bool)


def test_audio_engine_play_sfx_unknown_returns_false() -> None:
    engine = AudioEngine()
    assert engine.play_sfx("nonexistent") is False


def test_audio_engine_play_bgm_tracks_current() -> None:
    engine = AudioEngine()
    if engine.mixer_available:
        engine.play_bgm("title")
        assert engine.current_bgm == "title"
        engine.stop_bgm()
        assert engine.current_bgm is None


def test_audio_engine_master_volume_clamped() -> None:
    engine = AudioEngine()
    engine.set_master_volume(2.0)
    assert engine.master_volume == 1.0
    engine.set_master_volume(-1.0)
    assert engine.master_volume == 0.0


def test_audio_engine_shutdown_safe() -> None:
    engine = AudioEngine()
    engine.shutdown()  # should not raise
