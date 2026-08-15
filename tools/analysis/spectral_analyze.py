"""Quick spectral analysis for the 5 rendered SFX (DFT-based, no numpy).

Reports:
  - Top 5 dominant frequencies (with their magnitude)
  - Spectral centroid (brightness)
  - RMS loudness
  - Crest factor (peak / RMS) — indicates dynamic content
"""
from __future__ import annotations

import array
import math
import wave
from pathlib import Path


def dft_at(samples: array.array, freq_hz: float, sample_rate: int) -> float:
    """Magnitude of signal at freq_hz (slow DFT for a single bin)."""
    n = len(samples)
    re = 0.0
    im = 0.0
    two_pi_f = 2.0 * math.pi * freq_hz
    for i, s in enumerate(samples):
        # Use Hanning window implicitly by reducing influence of edges
        t = i / sample_rate
        re += s * math.cos(-two_pi_f * t)
        im += s * math.sin(-two_pi_f * t)
    return math.sqrt(re * re + im * im) / n


def analyze(path: str) -> dict:
    with wave.open(path, "rb") as w:
        sr = w.getframerate()
        n = w.getnframes()
        raw = w.readframes(n)
    samples = array.array("h", raw)

    # RMS
    rms = math.sqrt(sum(s * s for s in samples) / len(samples))
    rms_db = 20 * math.log10(rms / 32767) if rms > 0 else -120

    # Peak
    peak = max(abs(s) for s in samples)
    peak_db = 20 * math.log10(peak / 32767) if peak > 0 else -120
    crest = 20 * math.log10(peak / rms) if rms > 0 else 0

    # Top frequencies — sample at 50 frequencies logarithmically
    test_freqs = [int(f) for f in [
        30, 40, 55, 65, 80, 100, 110, 130, 160, 180, 200, 220, 250, 300,
        350, 400, 440, 500, 550, 600, 660, 700, 800, 880, 1000, 1100, 1175,
        1200, 1500, 1800, 2000, 2500, 3000, 3500, 4000, 5000, 6000, 8000, 10000,
    ] if f < sr / 2]
    mags = [(f, dft_at(samples, f, sr)) for f in test_freqs]
    mags.sort(key=lambda x: -x[1])
    top5 = mags[:5]

    # Spectral centroid (weighted average of frequency * magnitude)
    # Use top 20 frequencies for speed
    total_mag = sum(m for _, m in mags)
    if total_mag > 0:
        centroid = sum(f * m for f, m in mags) / total_mag
    else:
        centroid = 0

    return {
        "name": Path(path).stem,
        "duration_s": len(samples) / sr,
        "sr": sr,
        "rms_db": rms_db,
        "peak_db": peak_db,
        "crest_db": crest,
        "top5": top5,
        "centroid_hz": centroid,
    }


def main() -> int:
    sfx_dir = Path("D:/AI/void-hunter/data/sfx")
    print("=" * 90)
    print("SPECTRAL ANALYSIS — 5 new SFX (16-bit Mega Drive-style)")
    print("=" * 90)
    for path in sorted(sfx_dir.glob("*.wav")):
        if path.name.startswith("_"):
            continue
        a = analyze(str(path))
        print(f"\n{a['name']}  ({a['duration_s']:.2f}s @ {a['sr']} Hz)")
        print(f"  Loudness: RMS {a['rms_db']:+.1f} dBFS | Peak {a['peak_db']:+.1f} dBFS | Crest {a['crest_db']:.1f} dB")
        print(f"  Spectral centroid: {a['centroid_hz']:.0f} Hz (brilliance)")
        print(f"  Top 5 dominant frequencies:")
        for freq, mag in a["top5"]:
            bar = "#" * min(40, int(mag / 100))
            print(f"    {freq:6d} Hz  mag={mag:8.0f}  {bar}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
