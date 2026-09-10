"""BLOQUE 71 Task 3: asteroid_hit SFX is in the catalog and renders + the
WAV file exists for PyInstaller bundling.

The actual SFX catalog lives in ``src.audio.synth`` (SFX_CATALOG / SFX_NAMES).
There is no ``src.audio.sfx`` module — the brief assumed one. We adapt the
test to import the real module.
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import array

import pytest

from src.audio import synth
from src.audio.synth import (
    SFX_CATALOG,
    SFX_NAMES,
    Voice,
    render_sfx,
)


def test_asteroid_hit_in_catalog():
    """asteroid_hit is registered in the SFX_CATALOG."""
    assert "asteroid_hit" in SFX_CATALOG
    assert "asteroid_hit" in SFX_NAMES


def test_asteroid_hit_is_noise_voice_short_burst():
    """asteroid_hit is a brief noise burst (~0.05s) at modest volume.

    Brief spec: 0.05s noise burst, vol 0.3.
    Pattern matches other noise SFX in the catalog (e.g. ``hit``).
    """
    spec = SFX_CATALOG["asteroid_hit"]
    assert spec.voice == Voice.NOISE
    # Allow a small tolerance around the brief's 0.05s target.
    assert 0.04 <= spec.duration_s <= 0.07
    # Volume target is 0.3 (the in-game _play_sfx call uses volume=0.3 too).
    assert 0.2 <= spec.volume <= 0.4


def test_asteroid_hit_dispatch_does_not_raise():
    """render_sfx on asteroid_hit must not raise and must return a non-empty
    buffer (the runtime dispatch path prebakes the SFX in-memory; this is
    the equivalent of ``sfx.dispatch`` for the in-engine AudioEngine).
    """
    buf = render_sfx("asteroid_hit")
    assert isinstance(buf, array.array)
    assert len(buf) > 0


def test_asteroid_hit_wav_file_exists():
    """The actual WAV file is at Assets/sounds/asteroid_hit.wav.

    This is bundled by PyInstaller. The game also prebakes SFX in-memory,
    so a missing WAV would not crash the game itself — but the bundle
    would be silent for asteroid_hit. Test guards the artifact.
    """
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    wav_path = root / "Assets" / "sounds" / "asteroid_hit.wav"
    assert wav_path.exists(), f"Missing {wav_path}"
    assert wav_path.stat().st_size > 0, f"{wav_path} is empty"


def test_asteroid_hit_dispatch_via_audio_engine():
    """BLOQUE 71 fix: the actual runtime dispatch path.

    The previous dispatch-safety test only called ``render_sfx`` (a pure
    buffer-render function that is null-safe for unknown names by design).
    It did not exercise ``AudioEngine.play_sfx`` — the function the game
    actually calls when an asteroid hits the player. This test guards
    that real path.

    ``play_sfx`` returns ``True`` if the SFX was dispatched to the mixer,
    or ``False`` if the mixer is unavailable / the name is unknown. Both
    outcomes are valid; the key invariant is **no exception is raised**.
    """
    engine = synth.AudioEngine()
    result = engine.play_sfx("asteroid_hit", volume=0.3)
    assert result is True, (
        f"play_sfx('asteroid_hit') must return True (dispatched), "
        f"got {result!r} — SFX is likely missing from the catalog or "
        f"the dummy SDL mixer could not initialize"
    )
