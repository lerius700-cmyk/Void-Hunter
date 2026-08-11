"""Render the 5 new 16-bit SFX recipes to WAV files in data/sfx/.

Usage:
    python tools/render_sfx_previews.py

Writes:
    data/sfx/warning_miniboss.wav
    data/sfx/warning_boss.wav
    data/sfx/propulsion.wav
    data/sfx/enemy_shoot.wav
    data/sfx/engine_hum.wav

Plus a report (data/sfx/_RENDER_REPORT.md) with peak/duration info.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Make src/ importable when running from project root
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.audio.sfx_16bit_recipes import NEW_SFX_RECIPES
from src.audio.synth_16bit import (
    DEFAULT_SAMPLE_RATE,
    signal_peak,
    write_wav,
)


def main() -> int:
    out_dir = ROOT / "data" / "sfx"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Rendering 5 SFX to {out_dir}")
    print(f"Sample rate: {DEFAULT_SAMPLE_RATE} Hz, 16-bit mono PCM")
    print("-" * 60)

    report_lines = ["# SFX Render Report", "", "| name | duration (s) | samples | peak (int16) | peak (dBFS) |", "| --- | --- | --- | --- | --- |"]

    for name, render_fn in NEW_SFX_RECIPES.items():
        # Render. Most return just a signal; `render_enemy_shoot` returns
        # (signal, effective_sample_rate) to preserve 0.3s playback at
        # the lower lo-fi rate.
        result = render_fn()
        if isinstance(result, tuple):
            sig, effective_sr = result
        else:
            sig = result
            effective_sr = DEFAULT_SAMPLE_RATE
        n_samples = len(sig)
        duration_s = n_samples / effective_sr
        peak = signal_peak(sig)
        import math
        peak_db = 20.0 * math.log10(peak / 32767.0) if peak > 0 else -120.0

        out_path = out_dir / f"{name}.wav"
        write_wav(sig, str(out_path), sample_rate=effective_sr)

        size_kb = out_path.stat().st_size / 1024.0
        sr_label = f"@{effective_sr}Hz" if effective_sr != DEFAULT_SAMPLE_RATE else ""
        print(f"  {name:20s} {duration_s:5.2f}s  {n_samples:7d} samp {sr_label:8s} peak={peak:6.0f}  ({peak_db:6.1f} dBFS)  {size_kb:6.1f} KB")
        report_lines.append(f"| {name} | {duration_s:.2f} | {n_samples} @ {effective_sr} Hz | {peak:.0f} | {peak_db:.1f} |")

    report_lines.append("")
    report_lines.append(f"All files in `{out_dir.relative_to(ROOT)}`")
    report_lines.append("")
    report_lines.append("Listen to each file. If you want changes, tell me which one and what direction (e.g. 'warning_boss más grave', 'propulsion más brillante').")

    (out_dir / "_RENDER_REPORT.md").write_text("\n".join(report_lines), encoding="utf-8")
    print("-" * 60)
    print(f"Report: {out_dir / '_RENDER_REPORT.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
