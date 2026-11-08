"""BLOQUE 76: the gate must FAIL on an empty phase range.

The range (base..HEAD) is how the gate sees a PNG committed INSIDE the
phase: the working-tree check (`git diff HEAD`) is blind to it, and only
`git diff base..HEAD` is not. With `--base HEAD` the range holds ZERO
commits -- every range check has nothing to look at, finds nothing to
complain about, and the gate prints "PHASE 1 GATE OK" for a phase it
never looked at.

The phase's central promise ("not one PNG byte changed inside the phase")
was UNCHECKED, and the gate was green anyway. Nothing pinned the base
constants, so a base that stopped being the phase's start was invisible.

These tests hold both halves: the count the gate reads, and the verdict it
prints for it.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import pytest  # noqa: E402

from sprite_pipeline import gate  # noqa: E402


# ---------------------------------------------------------------------------
# The count the gate reads.
# ---------------------------------------------------------------------------
def test_the_range_of_head_against_head_is_empty() -> None:
    assert gate._range_commit_count("HEAD") == 0


def test_the_phase_1_range_is_not_empty() -> None:
    """The real base still holds the phase's commits."""
    count = gate._range_commit_count(gate.PHASE_1_BASE)
    assert count is not None, "git could not resolve the Phase 1 base"
    assert count > 0, "the Phase 1 range is empty -- the base moved"


def test_the_phase_2_range_is_not_empty() -> None:
    count = gate._range_commit_count(gate.PHASE_2_BASE)
    assert count is not None, "git could not resolve the Phase 2 base"
    assert count > 0, "the Phase 2 range is empty -- the base moved"


def test_an_unresolvable_base_is_not_an_empty_range() -> None:
    """None is not zero.

    A base git cannot resolve is the phase's own failure to report (it
    knows how to explain it). Reporting it as an EMPTY range here would
    hide the better message behind a worse one.
    """
    assert gate._range_commit_count("deadbeefdeadbeef") is None


# ---------------------------------------------------------------------------
# The verdict the gate prints.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("phase", (1, 2))
def test_the_gate_fails_on_an_empty_range(
    phase: int,
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = gate.main(["--phase", str(phase), "--base", "HEAD"])
    out = capsys.readouterr().out
    assert code == 1, f"the gate passed an empty range:\n{out}"
    assert "EMPTY" in out, out
    assert "GATE OK" not in out, out


def test_the_gate_says_the_range_is_what_it_measured(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The failure names the range, so the reader knows what to fix."""
    gate.main(["--phase", "1", "--base", "HEAD"])
    out = capsys.readouterr().out
    assert "HEAD..HEAD" in out, out
