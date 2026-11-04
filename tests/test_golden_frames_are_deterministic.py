"""BLOQUE 75 Fase 2: the golden frames must be reproducible.

The runtime uses the GLOBAL `random` module in 31 screen-affecting places and
seeds only `_asteroid_rng`. A capture that is not reproducible makes the
pixel comparison meaningless: a golden frame that drifts looks like a
regression, and a real regression can hide behind the drift.

This test captures the SAME frame twice and requires the two PNGs to be
byte-identical.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HARNESS = ROOT / "tools" / "capture" / "layerstack_frames.py"


def _run(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(HARNESS), *args],
        capture_output=True,
        text=True,
        cwd=str(cwd),
        timeout=300,
    )


def test_the_harness_exists() -> None:
    assert HARNESS.is_file(), HARNESS


def test_two_captures_of_the_same_frame_are_byte_identical(tmp_path: Path) -> None:
    """The determinism self-check: capture twice, compare the bytes."""
    first = tmp_path / "first"
    second = tmp_path / "second"
    for target in (first, second):
        # The harness resolves the repo from its own __file__, so it does not
        # need the repo as cwd. Running it inside tmp_path keeps everything
        # it writes (the captures, and the runtime's slow-section debug log)
        # out of the repository.
        proc = _run(tmp_path, "--out", str(target), "--only", "enemies")
        assert proc.returncode == 0, proc.stdout + proc.stderr
    digests: dict[str, list[str]] = {}
    for target in (first, second):
        for png in sorted(target.glob("*.png")):
            digests.setdefault(png.name, []).append(
                hashlib.md5(png.read_bytes()).hexdigest()
            )
    assert digests, "the harness wrote no frames"
    for name, hashes in digests.items():
        assert hashes[0] == hashes[1], (
            f"{name} is not reproducible: {hashes[0]} != {hashes[1]}"
        )
