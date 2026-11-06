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
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Callable, Sequence

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from sprite_pipeline import gate  # noqa: E402

PHASES = (1, 2)


def applicable(base: str, repo: Path) -> tuple[bool, str]:
    """Whether the phase's base commit is in this repository's history.

    Returns `(applies, reason)`. The reason is empty when it applies.
    """
    proc = subprocess.run(
        ["git", "-C", str(repo), "merge-base", "--is-ancestor", base, "HEAD"],
        capture_output=True,
        text=True,
    )
    if proc.returncode == 0:
        return True, ""
    if proc.returncode == 128:
        return False, f"the base commit {base!r} is not in this repository"
    return False, f"the base commit {base!r} is not an ancestor of HEAD"


def run_gate(
    phase: int,
    repo: Path,
    runner: Callable[[list[str]], int] | None = None,
    base: str | None = None,
) -> int:
    """Run one phase's gate, or explain why it does not apply.

    `runner` and `base` exist for the test: the test drives the decision
    without running the real gate.
    """
    resolved = base if base is not None else gate.resolve_base(None, phase)
    applies, reason = applicable(resolved, repo)
    if not applies:
        print(f"PHASE {phase} GATE SKIPPED: {reason}")
        return 0
    if runner is None:
        runner = gate.main
    print(f"--- PHASE {phase} GATE (base {resolved}) ---")
    return runner(["--phase", str(phase)])


def main(argv: Sequence[str] | None = None) -> int:
    repo = Path(__file__).resolve().parent.parent.parent
    code = 0
    for phase in PHASES:
        result = run_gate(phase, repo)
        if result != 0:
            code = result
    return code


if __name__ == "__main__":
    raise SystemExit(main())
