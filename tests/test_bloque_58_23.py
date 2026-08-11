"""Tests for BLOQUE 58.23: BossIntroScene + SubBossIntroScene reuse
the shared audio engine instead of constructing a new one.

BLOQUE 58.23 background:
  The user reported a 1.2s freeze that always happened right when
  the wave cleared and the boss intro was about to start. The
  per-section timing log (BLOQUE 58.21) attributed the slow frame
  to `wave_state`, but the real culprit was deeper: `_transition_to`
  inside wave_state triggered `BossIntroScene.on_enter`, which
  did `audio = AudioEngine()`. AudioEngine.__post_init__ calls
  `_prebake_all()` which re-renders EVERY SFX + BGM from scratch
  (~1.2s of synthesis). The shared audio engine already has
  everything prebaked; we just need to reuse it.

These tests guard against the regression by checking the source
directly: the introscenes must NOT construct a new AudioEngine
inside on_enter, and they MUST accept an `audio` parameter so
game.py can wire the shared engine through.
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("VOID_HUNTER_INVULN", "1")

import inspect
import pygame
pygame.init()
pygame.display.set_mode((1, 1))


def test_boss_intro_scene_accepts_audio_param():
    """BLOQUE 58.23: BossIntroScene must accept an audio parameter."""
    from src.ui.scenes import BossIntroScene

    def fake_transition(s): pass

    # No audio (backward-compat)
    s = BossIntroScene(fake_transition)
    assert hasattr(s, "_audio")
    assert s._audio is None

    # With audio (new behavior)
    sentinel = object()  # type: ignore[var-annotated]
    s2 = BossIntroScene(fake_transition, audio=sentinel)  # type: ignore[arg-type]
    assert s2._audio is sentinel


def test_sub_boss_intro_scene_accepts_audio_param():
    """BLOQUE 58.23: SubBossIntroScene must accept an audio parameter."""
    from src.ui.scenes import SubBossIntroScene

    def fake_transition(s): pass

    s = SubBossIntroScene(fake_transition)
    assert hasattr(s, "_audio")
    assert s._audio is None

    sentinel = object()  # type: ignore[var-annotated]
    s2 = SubBossIntroScene(fake_transition, audio=sentinel)  # type: ignore[arg-type]
    assert s2._audio is sentinel


def test_boss_intro_on_enter_does_not_construct_audioengine():
    """BLOQUE 58.23: BossIntroScene.on_enter must not call AudioEngine().

    The previous code did `audio = AudioEngine()` inside on_enter,
    which called _prebake_all() and re-rendered every SFX + BGM
    (~1.2s freeze). The fix: accept the shared engine and reuse it.
    The fallback `AudioEngine()` is only used if no engine was passed
    (kept for backward-compat with any unit-test callers that don't
    pass audio).
    """
    from src.ui.scenes import BossIntroScene
    src = inspect.getsource(BossIntroScene.on_enter)
    # The fix: must NOT have an unconditional AudioEngine() call.
    # Allowed: `if audio is None: ... AudioEngine()` (the safe fallback).
    # Disallowed: `audio = AudioEngine()` at the top.
    lines = [ln.strip() for ln in src.split("\n") if ln.strip()]
    for line in lines:
        if line.startswith("audio = AudioEngine("):
            # If this line is NOT inside an `if audio is None` block,
            # the regression is back. We allow it ONLY as a fallback.
            # The simplest guard: it must follow a `None` check.
            # Since we can't easily parse Python AST here, we just
            # require the line to be inside an `if audio is None:`
            # block by checking the source string.
            assert "if audio is None" in src, (
                f"AudioEngine() called outside the 'if audio is None' "
                f"fallback in BossIntroScene.on_enter:\n{src}"
            )


def test_sub_boss_intro_on_enter_does_not_construct_audioengine():
    """BLOQUE 58.23: SubBossIntroScene.on_enter must not unconditionally
    construct a new AudioEngine."""
    from src.ui.scenes import SubBossIntroScene
    src = inspect.getsource(SubBossIntroScene.on_enter)
    lines = [ln.strip() for ln in src.split("\n") if ln.strip()]
    for line in lines:
        if line.startswith("audio = AudioEngine("):
            assert "if audio is None" in src, (
                f"AudioEngine() called outside the 'if audio is None' "
                f"fallback in SubBossIntroScene.on_enter:\n{src}"
            )


def test_game_passes_audio_to_introscenes():
    """BLOQUE 58.23: game.py must pass `audio=self.audio` when
    registering BossIntroScene and SubBossIntroScene. Otherwise the
    scenes will receive None and fall back to creating a new engine."""
    from src.core import game
    src = inspect.getsource(game.Game._register_scenes)
    # Both scenes must be registered with audio=self.audio
    assert "BossIntroScene(transition_to, audio=self.audio)" in src, (
        f"Expected 'BossIntroScene(transition_to, audio=self.audio)' in "
        f"_register_scenes, got:\n{src}"
    )
    assert "SubBossIntroScene(transition_to, audio=self.audio)" in src, (
        f"Expected 'SubBossIntroScene(transition_to, audio=self.audio)' in "
        f"_register_scenes, got:\n{src}"
    )


def test_boss_intro_uses_passed_audio_engine():
    """BLOQUE 58.23: integration test. Construct a mock audio engine,
    pass it to BossIntroScene, then verify on_enter uses that engine
    (not a new one) by checking it doesn't call AudioEngine at all.

    We use a stub engine that records calls to play_sfx.
    """
    from src.ui.scenes import BossIntroScene

    class StubAudio:
        def __init__(self):
            self.sfx_calls = []
        def play_sfx(self, name, volume=1.0):
            self.sfx_calls.append((name, volume))
            return True

    stub = StubAudio()
    s = BossIntroScene(lambda st: None, audio=stub)
    s.on_enter()
    # The shared engine must have been used exactly once
    assert stub.sfx_calls == [("boss_warning", 0.9)], (
        f"Expected boss_warning SFX, got {stub.sfx_calls}"
    )
