"""BLOQUE 75: run the gates that apply to this branch.

The gate is STRICT on purpose: a base commit that is not in the repository
is a FAILURE, because the phase's promise is about the range and a gate that
skips its own range is not a gate. That is right for the branch the phase
lives on.

But the CI runs on more than one branch, and `master` has neither the
Phase 1 base (773cf08) nor the Phase 2 base (e619527) as an ancestor -- so
on `master` both gates would fail for a reason that has nothing to do with
the code. The APPLICABILITY decision therefore lives HERE, and the gate
stays strict.

A phase that does not apply prints `PHASE <n> GATE SKIPPED: <reason>` and
NEVER prints `GATE OK`. A skipped gate is not a green gate, and the log has
to say which one it was.

A base that cannot be RESOLVED -- a wrong constant, a shallow clone that
never fetched it, an ambiguous short sha -- is NOT a phase that does not
apply. The gate FAILS on that base on purpose, so the runner FAILS on it
too: skipping it would turn the whole gate system into a green job that
ran zero checks.
"""
from __future__ import annotations

import subprocess
import sys
from enum import Enum
from pathlib import Path
from typing import Callable, Sequence

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from sprite_pipeline import gate  # noqa: E402

PHASES = (1, 2)

# The exit code of the runner when it cannot even DECIDE, because the base
# of the phase is not in the repository. It is not the gate's verdict -- the
# gate never ran -- but it has to be a FAILURE, because the gate would have
# failed on that very same base.
ERROR_EXIT = 1

# The SAME budget the gate gives its own git calls (`gate.GIT_TIMEOUT_S`,
# 60 s). Every other git call in the pipeline is bounded; this module's
# `git merge-base --is-ancestor` was not, and a hung git there turned the
# CI job into its 25-minute wall with NO diagnosis -- the exact outcome
# the gate's own budget exists to avoid. A git that does not answer is a
# base the gate cannot resolve, and an unresolvable base is an ERROR
# (exit 1), not a phase that does not apply.
GIT_TIMEOUT_S = gate.GIT_TIMEOUT_S


class Applicability(Enum):
    """What the repository says about the base commit of a phase.

    Three outcomes, not two. A base that cannot be resolved is an ERROR
    (a wrong constant, a shallow clone, an ambiguous short sha) and NOT
    the same thing as a base that is simply not an ancestor of HEAD: the
    gate fails on the first one and skips nothing.
    """

    APPLIES = "applies"
    NOT_AN_ANCESTOR = "not_an_ancestor"
    UNRESOLVABLE = "unresolvable"


def applicable(base: str, repo: Path) -> tuple[Applicability, str]:
    """What the repository says about the phase's base commit.

    Returns `(status, reason)`. The reason is empty when the phase
    applies.
    """
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), "merge-base", "--is-ancestor", base, "HEAD"],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        # A git that does not answer is a base the repository cannot
        # resolve. The gate FAILS on such a base, so the runner has to
        # fail on it too -- and it has to say WHY: a hung git would
        # otherwise take the whole CI job down with its wall-clock
        # timeout and NO diagnosis at all.
        return (
            Applicability.UNRESOLVABLE,
            f"git did not answer whether {base!r} is an ancestor of HEAD "
            f"within {GIT_TIMEOUT_S}s. The repository may be locked, or the "
            f"clone is too large to walk; the gate cannot decide, so it "
            f"fails instead of skipping",
        )
    if proc.returncode == 0:
        return Applicability.APPLIES, ""
    if proc.returncode == 1:
        return (
            Applicability.NOT_AN_ANCESTOR,
            f"the base commit {base!r} is not an ancestor of HEAD",
        )
    # git exits 128 when the object does not exist: an unknown sha, a
    # shallow clone that never fetched it, or an ambiguous short sha.
    detail = proc.stderr.strip()
    return (
        Applicability.UNRESOLVABLE,
        f"the base commit {base!r} cannot be resolved in this repository: "
        f"{detail or 'git could not resolve it'}. Either the base constant "
        f"is wrong, or this clone is shallow -- `git fetch --unshallow` (or "
        f"`git fetch --depth=0`) brings the history the phase range needs",
    )


def run_gate(
    phase: int,
    repo: Path,
    runner: Callable[[list[str]], int] | None = None,
    base: str | None = None,
) -> int:
    """Run one phase's gate, or say why it does not apply.

    `runner` and `base` exist for the test: the test drives the decision
    without running the real gate.
    """
    resolved = base if base is not None else gate.resolve_base(None, phase)
    status, reason = applicable(resolved, repo)
    if status is Applicability.UNRESOLVABLE:
        print(f"PHASE {phase} GATE ERROR: {reason}")
        return ERROR_EXIT
    if status is Applicability.NOT_AN_ANCESTOR:
        print(f"PHASE {phase} GATE SKIPPED: {reason}")
        return 0
    if runner is None:
        runner = gate.main
    print(f"--- PHASE {phase} GATE (base {resolved}) ---")
    # The gate measures the range the runner APPROVED: `--base` has the top
    # precedence in `gate.resolve_base`, so the two can never drift apart.
    return runner(["--phase", str(phase), "--base", resolved])


def main(argv: Sequence[str] | None = None) -> int:
    code = 0
    for phase in PHASES:
        result = run_gate(phase, ROOT)
        if result != 0:
            code = result
    return code


if __name__ == "__main__":
    raise SystemExit(main())
