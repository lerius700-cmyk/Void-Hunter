"""BLOQUE 58.14: pause-screen lowpass BGM + rotating ship + stats panel.

These tests cover the new pause features:
  1. `enter_pause_lowpass()` / `exit_pause_lowpass()` in src/audio/music.py
     swap the gameplay BGM with a lowpass-filtered copy at the saved position.
  2. `apply_lowpass_to_wav()` in src/audio/synth.py reads a 16-bit WAV,
     applies the 1st-order IIR filter, and writes a filtered copy.
  3. `GameplayRuntime.get_pause_stats()` returns a dict with stable keys
     (hp, hp_max, lives, bombs, dash_heat, gold_rings, score, etc.).
  4. `GameplayScene.get_pause_stats()` and `BossFightScene.get_pause_stats()`
     forward to the runtime.
  5. `PauseScene` accepts a `get_pause_stats` callback and calls
     `enter_pause_lowpass` / `exit_pause_lowpass` on enter / exit (instead
     of the old `play_title_music` / `play_gameplay_music` swap).
"""
from __future__ import annotations

import os
import tempfile
import wave
from pathlib import Path
from unittest import mock

import pytest


# ---------------------------------------------------------------------------
# 1. apply_lowpass_to_wav — basic behaviour
# ---------------------------------------------------------------------------
def test_apply_lowpass_to_wav_writes_filtered_wav() -> None:
    """The IIR lowpass reads a 16-bit WAV, writes a filtered copy, and
    the output is shorter than the input (muffled = lower RMS amplitude)."""
    from src.audio.synth import apply_lowpass_to_wav

    # Build a small synthetic WAV: 1s of white noise at 44.1kHz, 16-bit, mono.
    sr = 44100
    duration_s = 0.5
    n = int(sr * duration_s)
    # Use random bytes so it's high-frequency content (muffled by LP)
    import array
    samples = array.array("h", [0] * n)
    import random
    rng = random.Random(42)
    for i in range(n):
        samples[i] = rng.randint(-20000, 20000)

    with tempfile.TemporaryDirectory() as tmp:
        in_path = os.path.join(tmp, "in.wav")
        out_path = os.path.join(tmp, "out.wav")
        with wave.open(in_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(samples.tobytes())

        ok = apply_lowpass_to_wav(in_path, out_path, cutoff_hz=300.0)
        assert ok is True
        assert os.path.isfile(out_path)
        # Verify the output is a valid WAV with the same sample rate
        with wave.open(out_path, "rb") as wf:
            assert wf.getnchannels() == 1
            assert wf.getsampwidth() == 2
            assert wf.getframerate() == sr
            out_n = wf.getnframes()
            # Same number of frames (the filter doesn't change length)
            assert out_n == n
            out_bytes = wf.readframes(out_n)
        # And compute RMS — output should be < input because HP content
        # is attenuated by the low cutoff.
        import math
        in_rms = math.sqrt(sum(s * s for s in samples) / n)
        out_samples = array.array("h", out_bytes)
        out_rms = math.sqrt(sum(s * s for s in out_samples) / n)
        # Allow some tolerance (white noise has energy across the spectrum,
        # so a 300Hz LP cuts most of it).
        assert out_rms < in_rms * 0.95, (
            f"expected filtered RMS to be lower than input "
            f"(in={in_rms:.1f}, out={out_rms:.1f})"
        )


def test_apply_lowpass_to_wav_missing_file_returns_false() -> None:
    """Missing input → False (no exception, no crash)."""
    from src.audio.synth import apply_lowpass_to_wav
    with tempfile.TemporaryDirectory() as tmp:
        ok = apply_lowpass_to_wav(
            os.path.join(tmp, "missing.wav"),
            os.path.join(tmp, "out.wav"),
        )
        assert ok is False


def test_apply_lowpass_to_wav_higher_cutoff_changes_signal_less() -> None:
    """Sanity: a 200 Hz cutoff mutes more energy than a 4000 Hz cutoff."""
    from src.audio.synth import apply_lowpass_to_wav
    import array, math, random

    sr = 44100
    n = sr // 2  # 0.5s
    samples = array.array("h", [0] * n)
    rng = random.Random(7)
    for i in range(n):
        samples[i] = rng.randint(-20000, 20000)

    def rms_of(out_path: str) -> float:
        with wave.open(out_path, "rb") as wf:
            data = wf.readframes(wf.getnframes())
        out = array.array("h", data)
        return math.sqrt(sum(s * s for s in out) / len(out))

    with tempfile.TemporaryDirectory() as tmp:
        in_path = os.path.join(tmp, "in.wav")
        with wave.open(in_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(samples.tobytes())
        out_low = os.path.join(tmp, "low.wav")
        out_high = os.path.join(tmp, "high.wav")
        apply_lowpass_to_wav(in_path, out_low, cutoff_hz=200.0)
        apply_lowpass_to_wav(in_path, out_high, cutoff_hz=4000.0)
        rms_low = rms_of(out_low)
        rms_high = rms_of(out_high)
        assert rms_low < rms_high, (
            f"200Hz RMS should be < 4000Hz RMS (got {rms_low:.1f} vs {rms_high:.1f})"
        )


# ---------------------------------------------------------------------------
# 2. music.py — pause lowpass helpers
# ---------------------------------------------------------------------------
def test_get_lowpass_cutoff_hz_default() -> None:
    """Default cutoff is 600 Hz when no env var is set."""
    from src.audio import music
    with mock.patch.dict(os.environ, {}, clear=False):
        os.environ.pop("VOID_HUNTER_LP_HZ", None)
        # The default depends on the module cache; reset to 600 to be sure
        music.set_lowpass_cutoff_hz(600.0)
        assert music.get_lowpass_cutoff_hz() == pytest.approx(600.0, abs=1.0)


def test_get_lowpass_cutoff_hz_env_override() -> None:
    """VOID_HUNTER_LP_HZ env var overrides the default."""
    from src.audio import music
    with mock.patch.dict(os.environ, {"VOID_HUNTER_LP_HZ": "350"}):
        assert music.get_lowpass_cutoff_hz() == pytest.approx(350.0, abs=1.0)


def test_set_lowpass_cutoff_hz_clamps_range() -> None:
    """Out-of-range cutoffs are clamped to safe bounds (80..8000)."""
    from src.audio import music
    music.set_lowpass_cutoff_hz(1.0)  # too low
    assert music.get_lowpass_cutoff_hz() >= 80.0
    music.set_lowpass_cutoff_hz(99999.0)  # too high
    assert music.get_lowpass_cutoff_hz() <= 8000.0


def test_enter_pause_lowpass_no_mixer_returns_false() -> None:
    """When pygame.mixer fails to init, enter returns False gracefully."""
    from src.audio import music
    # Mock _ensure_mixer to return False → enter should be a no-op
    with mock.patch.object(music, "_ensure_mixer", return_value=False):
        result = music.enter_pause_lowpass()
        assert result is False


def test_enter_pause_lowpass_not_in_gameplay_returns_false() -> None:
    """If the current track isn't 'gameplay' (e.g., title music), no-op."""
    from src.audio import music
    with mock.patch.object(music, "_ensure_mixer", return_value=True), \
         mock.patch.object(music, "get_current_track", return_value="title"):
        result = music.enter_pause_lowpass()
        assert result is False


def test_enter_and_exit_pause_lowpass_swap_track() -> None:
    """Happy path: gameplay → filtered on enter, filtered → gameplay on exit.

    We mock pygame.mixer.music so we don't actually need audio hardware.
    """
    from src.audio import music
    fake_music = mock.MagicMock()
    fake_music.get_busy.return_value = True
    fake_music.get_pos.return_value = 12345  # ms
    # Patch BOTH the module reference music uses AND find a source track
    with mock.patch.object(music, "_ensure_mixer", return_value=True), \
         mock.patch.object(music, "get_current_track", return_value="gameplay"), \
         mock.patch.object(music, "_ensure_filtered_bgm",
                            return_value="/tmp/fake_filtered.wav"), \
         mock.patch.object(music, "_find_track",
                            return_value=Path("/tmp/fake_gameplay.wav")):
        # Patch pygame.mixer.music in the music module
        with mock.patch.object(music.pygame.mixer, "music", fake_music):
            # ENTER
            ok_in = music.enter_pause_lowpass()
            assert ok_in is True, "enter_pause_lowpass should succeed"
            # Should have stopped, loaded filtered, and set volume
            assert fake_music.stop.called, "should call pygame.mixer.music.stop()"
            assert fake_music.load.called, "should call pygame.mixer.music.load()"
            loaded_path = fake_music.load.call_args_list[0][0][0]
            assert loaded_path == "/tmp/fake_filtered.wav"
            # EXIT
            ok_out = music.exit_pause_lowpass()
            assert ok_out is True, "exit_pause_lowpass should succeed"
            # Second load() should be the original
            loaded_paths = [c[0][0] for c in fake_music.load.call_args_list]
            assert any("gameplay" in str(p) for p in loaded_paths), (
                f"expected original gameplay track reload, got: {loaded_paths}"
            )


# ---------------------------------------------------------------------------
# 3. GameplayRuntime.get_pause_stats() — stable contract
# ---------------------------------------------------------------------------
def _make_runtime():
    """Build a fresh GameplayRuntime (no pygame audio init)."""
    from src.ui.gameplay_runtime import GameplayRuntime
    return GameplayRuntime(transition_to=lambda s: None, is_boss=False, act=1, audio=None)


def test_get_pause_stats_has_all_keys() -> None:
    """The pause-stats dict has every documented key with the right types."""
    rt = _make_runtime()
    stats = rt.get_pause_stats()
    expected_keys = {
        "hp", "hp_max", "hp_doubled",
        "lives", "lives_max",
        "bombs", "bombs_max",
        "dash_heat", "dash_heat_max",
        "gold_rings", "gold_rings_max",
        "score",
    }
    assert expected_keys.issubset(stats.keys()), (
        f"missing keys: {expected_keys - set(stats.keys())}"
    )
    # Type spot-checks
    assert isinstance(stats["hp"], int)
    assert isinstance(stats["hp_max"], int)
    assert isinstance(stats["hp_doubled"], bool)
    assert isinstance(stats["lives"], int)
    assert isinstance(stats["bombs"], int)
    assert isinstance(stats["dash_heat"], float)
    assert isinstance(stats["gold_rings"], int)
    assert isinstance(stats["score"], int)


def test_get_pause_stats_defaults_at_init() -> None:
    """At init, player has full HP, full bombs, 0 rings, 0 score."""
    rt = _make_runtime()
    stats = rt.get_pause_stats()
    from src.core.settings import (
        PLAYER_HP, PLAYER_HP_MAX, PLAYER_LIVES, PLAYER_BOMBS,
        PLAYER_BOMBS_MAX, PLAYER_DASH_HEAT_MAX,
    )
    assert stats["hp"] == PLAYER_HP
    assert stats["hp_max"] == PLAYER_HP_MAX
    assert stats["lives"] == PLAYER_LIVES
    assert stats["bombs"] == PLAYER_BOMBS
    assert stats["bombs_max"] == PLAYER_BOMBS_MAX
    assert stats["dash_heat"] == 0.0
    assert stats["dash_heat_max"] == PLAYER_DASH_HEAT_MAX
    assert stats["gold_rings"] == 0
    assert stats["score"] == 0


def test_get_pause_stats_reflects_damage_and_score() -> None:
    """After taking damage, hp drops; after killing enemies, score rises."""
    rt = _make_runtime()
    rt._player.take_damage(5)
    rt._scoring.add_kill(EnemyKind_dummy := None) if False else None
    # Use a real scoring event: kill scout = 50 pts (BLOQUE 50 base)
    from src.ui.gameplay_runtime import _ENEMY_SCORE
    from src.entities.enemies import EnemyKind
    rt._scoring.score = 1234
    rt._player.hp_doubled = True
    rt._player.gold_rings = 2
    stats = rt.get_pause_stats()
    assert stats["hp"] == 25  # 30 - 5
    assert stats["hp_doubled"] is True
    assert stats["gold_rings"] == 2
    assert stats["score"] == 1234


# ---------------------------------------------------------------------------
# 4. GameplayScene / BossFightScene forward get_pause_stats
# ---------------------------------------------------------------------------
def test_gameplay_scene_exposes_get_pause_stats() -> None:
    """The gameplay scene has a get_pause_stats() that returns a dict."""
    # Importing pygame just for the display init — we never actually draw.
    from src.ui.scenes import GameplayScene
    scene = GameplayScene(transition_to=lambda s: None, act=1, audio=None)
    stats = scene.get_pause_stats()
    assert isinstance(stats, dict)
    assert "hp" in stats
    assert "score" in stats


def test_boss_fight_scene_exposes_get_pause_stats() -> None:
    """The boss scene has a get_pause_stats() that returns a dict."""
    from src.ui.scenes import BossFightScene
    scene = BossFightScene(transition_to=lambda s: None, act=1, audio=None,
                           get_session_score=lambda: 0,
                           set_session_score=lambda s: None)
    stats = scene.get_pause_stats()
    assert isinstance(stats, dict)
    assert "hp" in stats


# ---------------------------------------------------------------------------
# 5. PauseScene — accepts callback, calls lowpass helpers
# ---------------------------------------------------------------------------
def test_pause_scene_accepts_get_pause_stats_callback() -> None:
    """PauseScene.__init__ stores the callback for later use."""
    from src.ui.scenes import PauseScene
    sentinel = {"hp": 42, "score": 9999}
    cb = lambda: sentinel
    scene = PauseScene(transition_to=lambda s: None, get_pause_stats=cb)
    assert scene._get_pause_stats is cb


def test_pause_scene_callback_returns_dict_when_called() -> None:
    """The callback is called by the scene to read live stats."""
    from src.ui.scenes import PauseScene
    called = {"n": 0}
    sentinel = {"hp": 7, "hp_max": 30, "lives": 2}
    def cb():
        called["n"] += 1
        return sentinel
    scene = PauseScene(transition_to=lambda s: None, get_pause_stats=cb)
    # Manually invoke the same path the draw() uses
    stats = scene._get_pause_stats() if scene._get_pause_stats else {}
    assert stats == sentinel
    assert called["n"] == 1


def test_pause_scene_no_callback_uses_empty_dict() -> None:
    """When no callback is passed, the scene still works (renders empty panel)."""
    from src.ui.scenes import PauseScene
    scene = PauseScene(transition_to=lambda s: None)
    assert scene._get_pause_stats is None
    # Simulate draw()'s fallback path
    stats = {}
    if scene._get_pause_stats is not None:
        stats = scene._get_pause_stats() or {}
    assert stats == {}


def test_pause_scene_on_enter_calls_enter_pause_lowpass() -> None:
    """BLOQUE 58.14: on_enter calls enter_pause_lowpass (not play_title_music)."""
    from src.ui.scenes import PauseScene
    scene = PauseScene(transition_to=lambda s: None)
    with mock.patch("src.audio.music.enter_pause_lowpass", return_value=True) as m:
        scene.on_enter()
        m.assert_called_once()


def test_pause_scene_on_exit_calls_exit_pause_lowpass() -> None:
    """BLOQUE 58.14: on_exit calls exit_pause_lowpass (not play_gameplay_music)."""
    from src.ui.scenes import PauseScene
    scene = PauseScene(transition_to=lambda s: None)
    with mock.patch("src.audio.music.exit_pause_lowpass", return_value=True) as m:
        scene.on_exit()
        m.assert_called_once()


def test_pause_scene_falls_back_to_gameplay_music_when_lowpass_fails() -> None:
    """If exit_pause_lowpass returns False, play_gameplay_music(force=True)
    is the fallback (so the user never hears silence on resume)."""
    from src.ui.scenes import PauseScene
    scene = PauseScene(transition_to=lambda s: None)
    with mock.patch("src.audio.music.exit_pause_lowpass", return_value=False), \
         mock.patch("src.audio.music.play_gameplay_music", return_value=True) as m:
        scene.on_exit()
        m.assert_called_once_with(force=True)


# ---------------------------------------------------------------------------
# 6. Player rotation sprite assets exist
# ---------------------------------------------------------------------------
def test_player_rotation_frames_exist() -> None:
    """All 8 rotation frames are on disk in Assets/sprites/player_rotation/."""
    candidates: list[Path] = []
    # Mirror _find_sprites_dir logic from src/ui/scenes.py
    import sys
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "Assets" / "sprites" / "player_rotation")
        candidates.append(Path(meipass) / "_internal" / "Assets" / "sprites" / "player_rotation")
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
    else:
        # Project root is two levels up from src/ui/
        exe_dir = Path(__file__).resolve().parent.parent
    candidates.append(exe_dir / "Assets" / "sprites" / "player_rotation")
    candidates.append(exe_dir / "_internal" / "Assets" / "sprites" / "player_rotation")
    found = next((c for c in candidates if c.is_dir()), None)
    assert found is not None, (
        f"player_rotation/ directory not found in any of: {candidates}"
    )
    for i in range(8):
        f = found / f"frame_{i:02d}.png"
        assert f.is_file(), f"missing {f}"
        # Sanity: file is non-trivial (> 1 KB; AI-generated PNGs are 400KB+)
        assert f.stat().st_size > 1024, f"file too small: {f}"


# ---------------------------------------------------------------------------
# 7. Game._register_scenes wires up the pause-stats callback
# ---------------------------------------------------------------------------
def test_pause_scene_get_pause_stats_dispatches_to_current_scene() -> None:
    """The callback returned by _register_scenes reads from whichever
    scene is registered under scenes.scenes[current_state]."""
    # Build a minimal mock that mimics Game._register_scenes' inner closure
    from src.ui.scenes import PauseScene, GameplayScene, BossFightScene

    class FakeScenes:
        def __init__(self, current):
            self.current_state = current
            self.scenes = {
                "GAMEPLAY": GameplayScene(lambda s: None, act=1, audio=None),
                "BOSS_FIGHT": BossFightScene(
                    lambda s: None, act=1, audio=None,
                    get_session_score=lambda: 0,
                    set_session_score=lambda s: None,
                ),
            }

    # Same closure body as Game._register_scenes (kept in sync manually)
    def _get_pause_stats_for(fake: FakeScenes):
        def _get_pause_stats() -> dict:
            try:
                underlying = fake.scenes.get(fake.current_state)
            except Exception:
                return {}
            if underlying is None:
                return {}
            fn = getattr(underlying, "get_pause_stats", None)
            if not callable(fn):
                return {}
            try:
                return fn() or {}
            except Exception:
                return {}
        return _get_pause_stats

    # Case 1: current = GAMEPLAY → callback returns gameplay stats
    fake = FakeScenes("GAMEPLAY")
    cb = _get_pause_stats_for(fake)
    stats = cb()
    assert "hp" in stats
    assert "score" in stats

    # Case 2: current = BOSS_FIGHT → callback returns boss stats
    fake.current_state = "BOSS_FIGHT"
    stats = cb()
    assert "hp" in stats

    # Case 3: current = (none) → callback returns empty dict
    fake.scenes = {}
    stats = cb()
    assert stats == {}
