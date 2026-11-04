"""BLOQUE 75 Fase 2: the golden frames must be reproducible.

The runtime uses the GLOBAL `random` module in 31 screen-affecting places and
seeds only `_asteroid_rng`. A capture that is not reproducible makes the
pixel comparison meaningless: a golden frame that drifts looks like a
regression, and a real regression can hide behind the drift.

This test captures the SAME frame twice and requires the two PNGs to be
byte-identical.

It also guards the THREE guarantees of the harness itself. A guarantee the
check cannot see is a hypothesis, not a guarantee, so each one has a test
that proves the check FAILS when the guarantee is broken:

  * an unknown `--only` name captures nothing, and the check has to say so
    and exit 1 -- a proof that cannot fail is not a proof;
  * the scene is rebuilt for every capture, and the harness ENFORCES it: a
    scene object used twice aborts the run (the frames would still be
    repeatable, but wrong);
  * `--check` compares the fresh capture against the COMMITTED golden
    frames, not only against a second fresh capture: two captures inside
    one process are identical even when the nondeterminism is
    per-process.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HARNESS = ROOT / "tools" / "capture" / "layerstack_frames.py"
GOLDEN_DIR = ROOT / "tools" / "golden" / "layerstack"

# The mutation that the reuse guard has to catch: the scene is built ONCE
# and reused for every frame. The frames would still be REPEATABLE (the
# same world, drawn twice) -- but they would be wrong, and a check that
# cannot see that is a hypothesis.
_REUSE_MUTATION = """
import sys

sys.path.insert(0, {capture_dir!r})
import layerstack_frames as H

_original = H._build_scene
_cache = {{}}


def _reused(is_boss):
    if "scene" not in _cache:
        _cache["scene"] = _original(is_boss)
    return _cache["scene"]


H._build_scene = _reused
raise SystemExit(H.main(["--check"]))
"""


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


def test_check_matches_the_committed_golden_frames(tmp_path: Path) -> None:
    """The committed proof must be reproducible.

    A fresh capture has to match the COMMITTED frame of the same name, not
    only a second fresh capture: two captures inside one process are
    identical even when the nondeterminism is per-process.
    """
    proc = _run(tmp_path, "--check")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "REPRODUCIBLE" in proc.stdout, proc.stdout + proc.stderr
    assert "GOLDENS MATCH" in proc.stdout, proc.stdout + proc.stderr


def test_check_with_an_unknown_frame_name_fails(tmp_path: Path) -> None:
    """A typo'd frame name captures NOTHING, and the check has to say so.

    Otherwise the check prints an empty success and exits 0: the proof
    tool reports success without having captured anything.
    """
    proc = _run(tmp_path, "--check", "--only", "no-such-frame")
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "no-such-frame" in proc.stdout + proc.stderr


def test_check_detects_a_reused_scene(tmp_path: Path) -> None:
    """The scene must be REBUILT for every capture, and the harness has to
    enforce it.

    The mutation builds the scene once and reuses it for every frame. The
    frames would still be repeatable -- the check would still say
    REPRODUCIBLE -- but they would be rendered from a CONTINUED world, so
    the harness has to notice the reuse and fail.
    """
    script = tmp_path / "mutated_harness.py"
    script.write_text(
        _REUSE_MUTATION.format(capture_dir=str(ROOT / "tools" / "capture")),
        encoding="utf-8",
    )
    proc = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
        timeout=300,
    )
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "REUSED" in proc.stdout + proc.stderr, proc.stdout + proc.stderr


def test_check_detects_a_golden_that_diverged(tmp_path: Path) -> None:
    """A committed golden that no longer matches the runtime is a
    regression, and the check has to see it."""
    golden_dir = tmp_path / "golden"
    shutil.copytree(GOLDEN_DIR, golden_dir)
    # The golden of "enemies" now holds another frame: a valid PNG whose
    # pixels are not the ones of the "enemies" frame.
    shutil.copy(golden_dir / "hud.png", golden_dir / "enemies.png")
    proc = _run(
        tmp_path, "--check", "--only", "enemies", "--golden", str(golden_dir)
    )
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "GOLDEN DIVERGED" in proc.stdout + proc.stderr, proc.stdout + proc.stderr
