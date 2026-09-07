"""Animation frame generators for GOLIATH (BLOQUE 60).

For each state, take a single 96x80 source PNG and produce 10 frame
PNGs. For idle/damage the 10 frames are byte-identical copies — the
runtime applies bob and tilt transforms. For phase2/death/intro the
10 frames would normally be a unique AI sequence, but the AI gives us
one image per state, so we duplicate. The animation_state field
distinguishes which set of 10 frames is active; the frame index
advances at runtime via the Boss.animation_state machine.
"""
from __future__ import annotations

import shutil
from pathlib import Path


def _duplicate_source(source: Path, out_dir: Path) -> list[Path]:
    """Copy source.png to out_dir/frame_00.png .. frame_09.png (10 copies)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    frames: list[Path] = []
    for i in range(10):
        dst = out_dir / f"frame_{i:02d}.png"
        shutil.copy2(source, dst)
        frames.append(dst)
    return frames


def generate_idle_frames(source: Path, out_dir: Path) -> list[Path]:
    """10 identical frames. Runtime applies vertical bob via sin curve."""
    return _duplicate_source(source, out_dir)


def generate_damage_frames(source: Path, out_dir: Path) -> list[Path]:
    """10 identical frames. Runtime applies tilt oscillation + white flash."""
    return _duplicate_source(source, out_dir)


def generate_phase2_frames(source: Path, out_dir: Path) -> list[Path]:
    """10 identical frames. In future BLOQUE these would be a unique AI
    sequence; for BLOQUE 60 we duplicate the single AI generation."""
    return _duplicate_source(source, out_dir)


def generate_death_frames(source: Path, out_dir: Path) -> list[Path]:
    """10 identical frames. Plays once on on_death, holds last frame."""
    return _duplicate_source(source, out_dir)


def generate_intro_frames(source: Path, out_dir: Path) -> list[Path]:
    """10 identical frames. Plays once on spawn, then transitions to idle."""
    return _duplicate_source(source, out_dir)
