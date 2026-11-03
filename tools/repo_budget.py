"""Measure the weight of the repository and hold it to a budget.

Round one of the cleanup was an EVENT: the repository was measured,
pruned and archived. Nothing measured it afterwards, so 8.58 GB of
builds accumulated in `dist/` between v1.3.0 and v1.6.3 without anyone
noticing.

This is the RULE. The ceilings live here, so raising one is a deliberate
edit of one place.

What is measured, and where it lives
------------------------------------
* **tracked** — the tree the repository carries, measured from the BLOBS
  (not from the checkout, which on Windows is a few percent larger
  because of CRLF). It is the size of what the repository holds, and it
  is branch-local: another agent's commits do not change it.
* **dist** — the build output, summed over the repository root AND
  every linked worktree. PyInstaller writes to `<cwd>/dist`, and this
  project's builds happen inside worktrees: measuring only the root
  would have missed 281 MB of build output the day this was written.
* **git** — the history. It is SHARED state: every branch and every
  worktree grows it. It is reported, but it is NOT enforced, because a
  commit made by another agent would redden a branch that has nothing to
  do with it.

The `.venv` and `.worktrees` directories are not part of any measurement:
they are environment, not content. The tracked measurement excludes them
by construction (git only lists tracked files), and the build-output
measurement only looks at `dist/`.

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

# The ceilings, in megabytes. Only these two are ENFORCED; the history
# is reported but not enforced (it is shared state).
BUDGETS: dict[str, int] = {
    "tracked": 300,   # the tree the repository carries
    "dist": 1200,     # the build output, root + every worktree
}

# The history has no ceiling: it is shared, so a hard limit on it would
# fail a branch for commits it did not make.
ADVISORY = ("git",)

# The lowpass cache is a cache, not build output: the game rebuilds it
# in a few seconds and it can be deleted at any moment.
_CACHE_DIRS = {"_vh_cache"}


@dataclass
class BudgetReport:
    """The three weights, in megabytes."""

    tracked_mb: float
    dist_mb: float
    git_mb: float

    def over(self) -> list[str]:
        """The ENFORCED ceilings that were crossed, as readable lines."""
        values = {"tracked": self.tracked_mb, "dist": self.dist_mb}
        return [
            f"{name} is over: {value:.1f} MB > {BUDGETS[name]} MB"
            for name, value in values.items()
            if value > BUDGETS[name]
        ]

    def advisory(self) -> list[str]:
        """The reported-but-not-enforced measurements that are high."""
        values = {"git": self.git_mb}
        return [
            f"{name} is high (not enforced): {value:.1f} MB"
            for name, value in values.items()
            if value > BUDGETS.get(name, value) * 0.9
        ]

    def describe(self) -> str:
        """A readable report of the three weights."""
        lines = []
        for name, value in (
            ("tracked", self.tracked_mb),
            ("dist", self.dist_mb),
            ("git", self.git_mb),
        ):
            mark = "advisory" if name in ADVISORY else "OVER" if (
                name in BUDGETS and value > BUDGETS[name]
            ) else "ok"
            if name in BUDGETS:
                lines.append(
                    f"{name:<8} {value:>9.1f} MB / {BUDGETS[name]} MB  {mark}"
                )
            else:
                lines.append(f"{name:<8} {value:>9.1f} MB / (sin techo)  {mark}")
        return "\n".join(lines)


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


def _dir_mb(path: Path, skip: set[str] | None = None) -> float:
    """The size of a directory in megabytes."""
    if not path.is_dir():
        return 0.0
    skip = skip or set()
    total = 0
    for entry in path.rglob("*"):
        try:
            if not entry.is_file():
                continue
            if skip and entry.name in skip:
                continue
            total += entry.stat().st_size
        except OSError:
            continue
    return total / (1024 * 1024)


def _tracked_mb(root: Path) -> float:
    """The size of the tracked tree, measured from the BLOBS.

    The checkout on Windows is a few percent larger than the blobs
    because of CRLF, and its size changes with the checkout. What the
    repository CARRIES is the sum of the blob sizes.
    """
    proc = subprocess.run(
        ["git", "-C", str(root), "ls-tree", "-r", "-l", "HEAD"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        return 0.0
    total = 0
    for line in proc.stdout.splitlines():
        fields = line.split(None, 4)
        if len(fields) < 4:
            continue
        try:
            total += int(fields[3])
        except ValueError:
            continue
    return total / (1024 * 1024)


def _dist_mb(base: Path) -> float:
    """The build output, summed over the root and every worktree.

    PyInstaller writes to `<cwd>/dist`, and the builds of this project
    happen inside worktrees. Measuring only the root would miss exactly
    the accumulation this budget exists to catch.
    """
    total = _dir_mb(base / "dist", skip=_CACHE_DIRS)
    worktrees = base / ".worktrees"
    if worktrees.is_dir():
        for entry in worktrees.iterdir():
            if entry.is_dir():
                total += _dir_mb(entry / "dist", skip=_CACHE_DIRS)
    return total


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
        dist_mb=_dist_mb(base),
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
                    "advisory": list(ADVISORY),
                    "over": report.over(),
                },
                indent=2,
            )
        )
    else:
        print(report.describe())
        for line in report.advisory():
            print(f"  ! {line}")
    return 1 if report.over() else 0


if __name__ == "__main__":
    sys.exit(main())
