"""BLOQUE 75 Fase 2: the golden frames must be reproducible.

The runtime uses the GLOBAL `random` module in 31 screen-affecting places and
seeds only `_asteroid_rng`. A capture that is not reproducible makes the
pixel comparison meaningless: a golden frame that drifts looks like a
regression, and a real regression can hide behind the drift.

This test captures the SAME frame twice and requires the two PNGs to be
byte-identical.

It also guards the FIVE guarantees of the harness itself. A guarantee the
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
    per-process;
  * a MISSING golden set fails: skipping the comparison would leave the
    weaker intra-process check and the phase gate would go green with
    ZERO proof fixtures;
  * the proof set cannot SHRINK silently: a committed golden whose frame is
    GONE from the FRAMES table is reported, not ignored;
  * the proof fixtures cannot be DESTROYED by accident: the default `--out`
    is a scratch directory outside the repository, so a bare capture cannot
    rewrite the committed goldens.
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
    regression, and the check has to see it.

    The assertion is on the PIXEL divergence, not only on the
    "GOLDEN DIVERGED" header: the orphan report (a golden whose frame is
    gone from the FRAMES table) prints that very same header, so a test
    that only looks at the header passes even when the pixels were never
    compared -- the proof would be vacuous. This test has to FAIL against
    a PRISTINE golden set: that is what makes it a proof.
    """
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
    # The PIXELS differ -- not merely the shape of the golden set.
    assert "the captured frame differs from the committed one" in (
        proc.stdout + proc.stderr
    ), proc.stdout + proc.stderr
    assert "pixels differ" in proc.stdout + proc.stderr, proc.stdout + proc.stderr


def test_check_of_a_single_frame_matches_the_committed_goldens(tmp_path: Path) -> None:
    """`--only` is LEGAL: one frame can be checked against the proof.

    The harness reports a golden whose frame is gone from the FRAMES table
    as an orphan, and it compares the committed set against the FRAMES
    TABLE -- not against the captured subset. If the reference were the
    captured subset, every golden that was not selected would look like an
    orphan and this check could never pass.
    """
    golden_dir = tmp_path / "golden"
    shutil.copytree(GOLDEN_DIR, golden_dir)
    proc = _run(tmp_path, "--check", "--only", "enemies", "--golden", str(golden_dir))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "GOLDENS MATCH: enemies" in proc.stdout + proc.stderr, proc.stdout + proc.stderr


def test_a_bare_capture_does_not_rewrite_the_committed_proof(tmp_path: Path) -> None:
    """The proof tool must not be able to DESTROY the proof by accident.

    The default `--out` used to be the committed golden directory, so a
    bare `python tools/capture/layerstack_frames.py` silently rewrote the
    committed proof fixtures. The default is now a scratch directory
    outside the repository: rewriting the proof takes an explicit
    `--out tools/golden/layerstack`.
    """
    before = {
        path.name: hashlib.md5(path.read_bytes()).hexdigest()
        for path in sorted(GOLDEN_DIR.glob("*.png"))
    }
    assert before, "the committed proof set is empty"
    proc = _run(tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    after = {
        path.name: hashlib.md5(path.read_bytes()).hexdigest()
        for path in sorted(GOLDEN_DIR.glob("*.png"))
    }
    assert after == before, "the bare capture rewrote the committed proof"


def test_check_fails_when_the_golden_set_is_missing(tmp_path: Path) -> None:
    """A MISSING golden set is a failure, never a pass.

    Skipping the comparison would leave the weaker intra-process check
    that the golden comparison exists to replace, and the Phase 2 gate
    (P2-G2) would go green with ZERO proof fixtures.
    """
    missing = tmp_path / "no-such-golden-dir"
    proc = _run(tmp_path, "--check", "--golden", str(missing))
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "GOLDENS MISSING" in proc.stdout + proc.stderr, proc.stdout + proc.stderr


def test_check_fails_when_the_proof_set_shrank(tmp_path: Path) -> None:
    """The committed golden files and the captured frames have to be the
    SAME set.

    A golden with no capture (a frame dropped from the FRAMES table) would
    otherwise sit on disk, never compared, and the proof set could shrink
    silently.
    """
    golden_dir = tmp_path / "golden"
    shutil.copytree(GOLDEN_DIR, golden_dir)
    # A golden with no frame to capture it.
    shutil.copy(golden_dir / "boss.png", golden_dir / "ghost.png")
    proc = _run(tmp_path, "--check", "--golden", str(golden_dir))
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "GOLDEN DIVERGED" in proc.stdout + proc.stderr, proc.stdout + proc.stderr
    assert "ghost" in proc.stdout + proc.stderr, proc.stdout + proc.stderr
