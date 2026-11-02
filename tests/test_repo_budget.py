"""The repository has a weight ceiling, and something has to enforce it.

Round one of the cleanup took the repository from 15.70 GB to 2.35 GB
and nothing noticed. Between v1.3.0 and v1.6.3, `dist/` accumulated
8.58 GB of builds that no metric ever mentioned.

The ceilings live in `tools/repo_budget.py` so that raising one is a
deliberate edit of one place -- never a quiet edit of a test.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from repo_budget import BUDGETS, CONTENT_EXCLUDED, measure  # noqa: E402


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


def test_every_budget_has_a_ceiling():
    """The three metrics the project watches are all bounded."""
    assert set(BUDGETS) == {"tracked", "dist", "git"}
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


def test_the_measurement_ignores_the_environment():
    """`.venv` and `.worktrees` are environment, not content.

    They are the two directories that change size for reasons that have
    nothing to do with the project, so the budget does not look at them.
    """
    assert ".venv" in CONTENT_EXCLUDED
    assert ".worktrees" in CONTENT_EXCLUDED
