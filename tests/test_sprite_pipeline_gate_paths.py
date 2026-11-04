"""BLOQUE 75 Fase 2: G5's range diff protects the ART, not the measurement.

G5's first half diffs the boss assets over the phase range. What it
protects is GOLIATH's ART: the manifest (the SPEC) and the PNGs. The
`anchors.toml` is NOT art -- it is the MEASUREMENT the auditor generates
FROM the art, and what the gate checks about it is its FRESHNESS (the
second half, `verify_contract` -> `anchors_fresh`), not whether it moved.

So the range diff must NOT report the generated file, and it MUST still
report the manifest and the PNGs. These three cases are what tell the
exclusion apart from a hole: dropping the exclusion turns the first one
red, and dropping the whole pathspec turns the other two red.

The tests run the gate's OWN helper, with the gate's OWN pathspec, over a
temporary repository under `tmp_path`: nothing here writes into the
repository (L7).
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from sprite_pipeline import gate  # noqa: E402

# The three kinds of file that live under the boss directory: the
# GENERATED measurement, the SPEC and the ART.
ANCHORS = "Assets/sprites/bosses/goliath/anchors.toml"
MANIFEST = "Assets/sprites/bosses/goliath/manifest.toml"
FRAME = "Assets/sprites/bosses/goliath/death/frame_00.png"

# The identity the temporary commits use. It is passed with `-c`, so the
# user's own git configuration is never written to.
AUTHOR = ("-c", "user.email=gate@test", "-c", "user.name=gate")


def _git(repo: Path, args: list[str]) -> None:
    """Run a git command in the temporary repository."""
    subprocess.run(
        ["git", *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=True,
    )


def _repo(tmp_path: Path) -> Path:
    """A temporary git repository holding one file of each kind."""
    repo = tmp_path / "repo"
    for rel in (ANCHORS, MANIFEST, FRAME):
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"base\n")
    _git(repo, ["init", "-q", "-b", "main"])
    _git(repo, ["add", "-A"])
    _git(repo, [*AUTHOR, "-c", "commit.gpgsign=false", "commit", "-q", "-m", "base"])
    return repo


def _commit_change(repo: Path, rel: str, payload: bytes) -> None:
    """Change one file and commit it, so HEAD~1..HEAD is exactly that."""
    (repo / rel).write_bytes(payload)
    _git(repo, ["add", "-A"])
    _git(
        repo,
        [*AUTHOR, "-c", "commit.gpgsign=false", "commit", "-q", "-m", "change"],
    )


def _range_diff(repo: Path) -> str:
    """What the gate's own helper reports for the last commit."""
    proc = gate._goliath_assets_diff("HEAD~1", repo=repo)
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


def test_the_generated_anchors_are_not_reported_by_the_range_diff(tmp_path):
    """The measurement is validated by FRESHNESS, not by "did it change?"."""
    repo = _repo(tmp_path)
    _commit_change(repo, ANCHORS, b"regenerated\n")
    out = _range_diff(repo)
    assert out.strip() == "", (
        "the generated anchors must not be reported by the range diff:\n" + out
    )


def test_the_manifest_is_reported_by_the_range_diff(tmp_path):
    """The SPEC is not a generated file: it stays inside the range."""
    repo = _repo(tmp_path)
    _commit_change(repo, MANIFEST, b"changed\n")
    out = _range_diff(repo)
    assert "goliath/manifest.toml" in out, out


def test_a_png_is_reported_by_the_range_diff(tmp_path):
    """The ART is what the promise is about: it stays inside the range."""
    repo = _repo(tmp_path)
    _commit_change(repo, FRAME, b"\x89PNG\r\n\x1a\nchanged")
    out = _range_diff(repo)
    assert "frame_00.png" in out, out
