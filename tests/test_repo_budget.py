"""The repository has a weight ceiling, and something has to enforce it.

Round one of the cleanup took the repository from 15.70 GB to 2.35 GB
and nothing noticed. Between v1.3.0 and v1.6.3, `dist/` accumulated
8.58 GB of builds that no metric ever mentioned.

The ceilings live in `tools/repo_budget.py` so that raising one is a
deliberate edit of one place -- never a quiet edit of a test.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from repo_budget import ADVISORY, BUDGETS, measure  # noqa: E402


def test_the_repository_is_inside_its_budget():
    """The repository today is under every ceiling."""
    report = measure(ROOT)
    over = report.over()
    assert not over, (
        "the repository is over its budget: "
        + "; ".join(over)
        + f" (tracked={report.tracked_mb:.1f}MB dist={report.dist_mb:.1f}MB "
        + f"git={report.git_mb:.1f}MB)"
    )


def test_the_enforced_ceilings_are_the_local_ones():
    """Only the tracked tree and the build output are enforced.

    The history is shared state: every branch and every worktree grows
    it. A hard ceiling on it would redden a branch for commits it did
    not make.
    """
    assert set(BUDGETS) == {"tracked", "dist"}
    assert set(ADVISORY) == {"git"}
    for name, ceiling in BUDGETS.items():
        assert ceiling > 0, f"the {name} ceiling is not a ceiling"


def test_the_three_weights_are_measured():
    """The measurement returns something for each of the three."""
    report = measure(ROOT)
    assert report.tracked_mb > 0
    assert report.dist_mb >= 0
    assert report.git_mb > 0


def test_a_crossed_ceiling_is_reported():
    """A weight over the ceiling is reported, not ignored."""
    from repo_budget import BudgetReport

    fat = BudgetReport(tracked_mb=10_000.0, dist_mb=0.0, git_mb=0.0)
    over = fat.over()
    assert over, "a tree ten times over the ceiling was not reported"
    assert "tracked" in over[0]


def test_the_history_is_reported_but_never_enforced():
    """A huge history is advisory, not a failure."""
    from repo_budget import BudgetReport

    fat = BudgetReport(tracked_mb=1.0, dist_mb=1.0, git_mb=99_999.0)
    assert fat.over() == [], "the shared history must not be enforced"
    assert fat.advisory(), "a huge history should be reported"


def test_the_build_output_of_every_worktree_is_counted(tmp_path: Path):
    """The budget sees the builds of the WORKTREES, not only the root.

    PyInstaller writes to `<cwd>/dist`, and this project's builds happen
    inside worktrees. A budget that only looked at the root could not
    catch the accumulation it was created for -- and 281 MB of build
    output was invisible to it the day it was written.
    """
    repo = tmp_path / "repo"
    (repo / "dist").mkdir(parents=True)
    (repo / "dist" / "root.bin").write_bytes(b"x" * 1024)
    (repo / ".worktrees" / "wt" / "dist").mkdir(parents=True)
    (repo / ".worktrees" / "wt" / "dist" / "worktree.bin").write_bytes(
        b"x" * 2048
    )

    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "t@t"], check=True
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "t"], check=True
    )
    (repo / "keep.txt").write_text("x", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-q", "-m", "x"], check=True
    )

    report = measure(repo)
    # 1 KB at the root + 2 KB in the worktree.
    assert report.dist_mb == pytest.approx(3 / 1024, abs=0.01), (
        f"the worktree's build output was not counted: {report.dist_mb} MB"
    )


def test_the_lowpass_cache_is_not_counted_as_build_output(tmp_path: Path):
    """`_vh_cache` is a cache: the game rebuilds it in a few seconds."""
    repo = tmp_path / "repo"
    (repo / "dist" / "_vh_cache").mkdir(parents=True)
    (repo / "dist" / "_vh_cache" / "track.wav").write_bytes(b"x" * 4096)
    (repo / "dist" / "real.bin").write_bytes(b"x" * 1024)

    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "t@t"], check=True
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "t"], check=True
    )
    (repo / "keep.txt").write_text("x", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-q", "-m", "x"], check=True
    )

    report = measure(repo)
    assert report.dist_mb == pytest.approx(1 / 1024, abs=0.01)
