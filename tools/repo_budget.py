"""Measure the weight of the repository and hold it to a budget.

Round one of the cleanup was an EVENT: the repository was measured,
pruned and archived. Nothing measured it afterwards, so 8.58 GB of
builds accumulated in `dist/` between v1.3.0 and v1.6.3 without anyone
noticing.

This is the RULE. Three weights are measured and three ceilings are
enforced by `tests/test_repo_budget.py`. The ceilings live here, so
raising one is a deliberate edit of one place.

Usage:
    python tools/repo_budget.py
    python tools/repo_budget.py --json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The ceilings, in megabytes.
BUDGETS: dict[str, int] = {
    "tracked": 300,   # the tree the repository carries
    "dist": 600,      # the build output
    "git": 550,       # the history
}

# Directories that are ENVIRONMENT, not content: they change size for
# reasons that have nothing to do with the project. They are excluded
# from the CONTENT measurement (the tracked tree), which is the one
# that says how much the project itself weighs.
CONTENT_EXCLUDED = {".venv", ".worktrees"}


@dataclass
class BudgetReport:
    """The three weights, in megabytes."""

    tracked_mb: float
    dist_mb: float
    git_mb: float

    def over(self) -> list[str]:
        """The ceilings that were crossed, as readable lines."""
        values = {
            "tracked": self.tracked_mb,
            "dist": self.dist_mb,
            "git": self.git_mb,
        }
        return [
            f"{name} is over: {value:.1f} MB > {BUDGETS[name]} MB"
            for name, value in values.items()
            if value > BUDGETS[name]
        ]

    def describe(self) -> str:
        """A readable report of the three weights."""
        lines = []
        for name, value in (
            ("tracked", self.tracked_mb),
            ("dist", self.dist_mb),
            ("git", self.git_mb),
        ):
            ceiling = BUDGETS[name]
            mark = "OVER" if value > ceiling else "ok"
            lines.append(f"{name:<8} {value:>9.1f} MB / {ceiling} MB  {mark}")
        return "\n".join(lines)


def _dir_mb(path: Path) -> float:
    """The size of a directory in megabytes."""
    if not path.is_dir():
        return 0.0
    total = 0
    for entry in path.rglob("*"):
        try:
            if entry.is_file():
                total += entry.stat().st_size
        except OSError:
            continue
    return total / (1024 * 1024)


def _tracked_mb(root: Path) -> float:
    """The size of every file the repository tracks."""
    proc = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        capture_output=True,
    )
    if proc.returncode != 0:
        return 0.0
    total = 0
    for chunk in proc.stdout.split(b"\0"):
        if not chunk:
            continue
        path = root / chunk.decode("utf-8", "replace")
        try:
            if path.is_file():
                total += path.stat().st_size
        except OSError:
            continue
    return total / (1024 * 1024)


def repo_root(root: Path) -> Path:
    """The root of the repository, even from a linked worktree.

    In a linked worktree `.git` is a FILE that points at the common
    directory, and `dist/` lives in the repository root rather than in
    the worktree. The build output and the history are therefore
    measured where they actually are.
    """
    proc = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--git-common-dir"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        return root
    common = Path(proc.stdout.strip())
    if not common.is_absolute():
        common = (root / common).resolve()
    return common.parent if common.name == ".git" else common


def measure(root: Path | None = None) -> BudgetReport:
    """Measure the three weights of the repository at `root`.

    The tracked tree is measured where it was asked for: that is the
    branch this checkout carries. The build output and the history
    belong to the repository as a whole, so they are measured at its
    root.
    """
    root = root or ROOT
    base = repo_root(root)
    return BudgetReport(
        tracked_mb=_tracked_mb(root),
        dist_mb=_dir_mb(base / "dist"),
        git_mb=_dir_mb(base / ".git"),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = measure(Path(args.root))
    if args.json:
        print(
            json.dumps(
                {
                    "tracked_mb": round(report.tracked_mb, 1),
                    "dist_mb": round(report.dist_mb, 1),
                    "git_mb": round(report.git_mb, 1),
                    "budgets": BUDGETS,
                    "over": report.over(),
                },
                indent=2,
            )
        )
    else:
        print(report.describe())
    return 1 if report.over() else 0


if __name__ == "__main__":
    sys.exit(main())
