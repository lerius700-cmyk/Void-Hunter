"""Audio: 24 SFX + 4 BGM procedurales (BLOQUE 13)."""
from src.audio.synth import (
    BGM_NAMES,
    SFX_NAMES,
    AudioEngine,
    Voice,
    adsr_envelope,
    render_bgm,
    render_sfx,
    square_wave,
    triangle_wave,
    saw_wave,
    noise_wave,
)

__all__ = [
    "BGM_NAMES", "SFX_NAMES", "AudioEngine", "Voice",
    "adsr_envelope", "render_bgm", "render_sfx",
    "square_wave", "triangle_wave", "saw_wave", "noise_wave",
]
