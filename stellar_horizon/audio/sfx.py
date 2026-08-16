"""SFX wrapper around Void-Hunter's `src.audio.synth`."""
from __future__ import annotations


def play_event(name: str) -> None:
    """Best-effort SFX dispatch. No-op if synth can't be loaded."""
    try:
        from src.audio.synth import play_sfx  # type: ignore
        play_sfx(name)
    except Exception:
        pass
