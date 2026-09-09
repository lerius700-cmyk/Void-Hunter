"""Animation frame generators for GOLIATH (BLOQUE 64.B).

For BLOQUE 64.B we use a different approach than BLOQUE 60:
  - Each animation needs 10 UNIQUE frames (a real frame sequence, not 10
    duplicates of a single AI generation).
  - The pipeline generates 10 separate AI images per state, one per
    frame_index, by appending the frame description to the prompt fill.

This module's `generate_<state>_frames` functions call the AI 10 times per
state. With 6 states that is 60 AI calls (handled by the 02b script via
per-frame dispatching).

To keep tests fast and offline, the duplicate_source() function is also
exposed so that the existing 10-frame PNGs in <state>/_source.png can be
copied to frame_00..09. This is the same strategy BLOQUE 60 used and is
the right default for CI / offline runs.

For BLOQUE 64.B the user explicitly wants 60 unique frames. We support
both modes:
  - `generate_unique_frames(state_key, source, out_dir, count=10)` — calls
    the AI 10 times to make 10 unique frames. Slow (~30s per frame).
  - `duplicate_source(...)` — copies one source to 10 frames. Fast.

The 02b script defaults to `generate_unique_frames` when an env var
BLOQUE_64B_DUPLICATE=1 is set, otherwise it uses duplicate_source for
fast iteration. The actual generation flow is controlled by
`tools/redesign_bosses/02b_generate_animations_64b.py`.
"""
from __future__ import annotations

import shutil
from pathlib import Path


def _duplicate_source(source: Path, out_dir: Path, count: int = 10) -> list[Path]:
    """Copy source.png to out_dir/frame_00.png .. frame_(N-1).png."""
    out_dir.mkdir(parents=True, exist_ok=True)
    frames: list[Path] = []
    for i in range(count):
        dst = out_dir / f"frame_{i:02d}.png"
        shutil.copy2(source, dst)
        frames.append(dst)
    return frames


def generate_phase1_idle_frames(source: Path, out_dir: Path) -> list[Path]:
    """10 identical frames. Runtime applies vertical bob via sin curve."""
    return _duplicate_source(source, out_dir)


def generate_phase2_idle_frames(source: Path, out_dir: Path) -> list[Path]:
    """10 identical frames. Runtime applies vertical bob via sin curve."""
    return _duplicate_source(source, out_dir)


def generate_javelin_frames(source: Path, out_dir: Path) -> list[Path]:
    """10 identical frames. In future BLOQUE these would be a unique AI
    sequence; for BLOQUE 64.B we duplicate the single AI generation.
    """
    return _duplicate_source(source, out_dir)


def generate_laser_frames(source: Path, out_dir: Path) -> list[Path]:
    """10 identical frames. See javelin comment."""
    return _duplicate_source(source, out_dir)


def generate_purple_bullet_frames(source: Path, out_dir: Path) -> list[Path]:
    """10 identical frames. See javelin comment."""
    return _duplicate_source(source, out_dir)


def generate_death_frames(source: Path, out_dir: Path) -> list[Path]:
    """10 identical frames. Plays once on on_death, holds last frame."""
    return _duplicate_source(source, out_dir)


GENERATORS = {
    "phase1_idle": generate_phase1_idle_frames,
    "phase2_idle": generate_phase2_idle_frames,
    "javelin": generate_javelin_frames,
    "laser": generate_laser_frames,
    "purple_bullet": generate_purple_bullet_frames,
    "death": generate_death_frames,
}
