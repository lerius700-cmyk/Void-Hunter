"""SFX wrapper around Void-Hunter's `src.audio.synth` (AudioEngine).

This module exposes a small surface (`play_event`, `engine`) so
gameplay code doesn't need to know about the underlying mixer.
The engine is lazy-initialized on first use so the game boots fast
and headless tests can swap it out via `set_engine()`.

The AudioEngine itself pre-bakes 30+ SFX from the synth catalog
(one-shots for shoot/hit/explode/bomb) plus 7 thruster loops
added in the Stellar Horizon audio pass.
"""
from __future__ import annotations

from typing import Optional


_engine: Optional["object"] = None  # src.audio.synth.AudioEngine


def _get_engine():
    """Lazy-init the audio engine. Returns None if the synth can't
    be loaded (e.g. no display in headless CI)."""
    global _engine
    if _engine is not None:
        return _engine
    try:
        from src.audio.synth import AudioEngine  # type: ignore
        _engine = AudioEngine()
    except Exception:
        _engine = None
    return _engine


def set_engine(engine) -> None:
    """Override the engine (used by tests to inject a mock)."""
    global _engine
    _engine = engine


def engine():
    """Return the active engine (lazy-initialized). May be None
    if the synth failed to load (headless / no audio device)."""
    return _get_engine()


def play_event(name: str, volume: float = 1.0) -> None:
    """Best-effort one-shot SFX dispatch. No-op if synth can't be
    loaded or the name is unknown."""
    eng = _get_engine()
    if eng is None:
        return
    try:
        eng.play_sfx(name, volume=volume)
    except Exception:
        pass
