"""BLOQUE 73 Fase B+: generate 4 weapon SFX WAV files.

Same pattern as tools/generate_asteroid_hit_wav.py (BLOQUE 71). The
game's audio runtime prebakes SFX in-memory from SFX_CATALOG specs
(see src.audio.synth), so these WAVs are PyInstaller bundle artifacts
(not runtime dependencies). Generated here to match the catalog.

The 4 weapon SFX:
  shoot_thick.wav   - punchy 0.08s square wave 880->220 Hz (heavy shot)
  laser_hum.wav     - 0.5s triangle sweep 200->800 Hz (sustained beam)
  flame_loop.wav    - 0.1s noise burst (crackle, fast fire)
  shoot_double.wav  - 0.05s square wave 1320->660 Hz (dual click)

Output: Assets/sounds/<name>.wav (mono 16-bit PCM at MIXER_SAMPLE_RATE).

Run: .venv/Scripts/python.exe tools/generate_weapon_sfx.py
"""
from __future__ import annotations

import struct
import wave
from pathlib import Path

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.audio.synth import SFX_CATALOG, render_sfx
from src.core.settings import MIXER_SAMPLE_RATE


WEAPON_SFX = ("shoot_thick", "laser_hum", "flame_loop", "shoot_double")


def write_wav(name: str, out_dir: Path) -> Path:
    """Render SFX and save to Assets/sounds/<name>.wav."""
    spec = SFX_CATALOG[name]
    samples = render_sfx(name)
    raw = struct.pack("<" + "h" * len(samples), *samples)

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{name}.wav"
    with wave.open(str(out_path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(MIXER_SAMPLE_RATE)
        w.writeframes(raw)

    print(f"  wrote {out_path.name} ({out_path.stat().st_size} bytes, "
          f"voice={spec.voice.value}, dur={spec.duration_s}s, vol={spec.volume})")
    return out_path


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    sounds_dir = repo_root / "Assets" / "sounds"
    print(f"Generating {len(WEAPON_SFX)} weapon SFX in {sounds_dir.relative_to(repo_root)}/")
    for name in WEAPON_SFX:
        write_wav(name, sounds_dir)
    print("Done.")


if __name__ == "__main__":
    main()