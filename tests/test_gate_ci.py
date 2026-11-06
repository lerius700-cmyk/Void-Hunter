"""BLOQUE 75: the CI runner decides WHICH gates apply.

The gate itself is strict: a base commit that is not in the repository is a
FAILURE, and that is right for the branch the phase lives on. But the CI
runs on more than one branch, and `master` has neither the Phase 1 base nor
the Phase 2 base as an ancestor. So the APPLICABILITY decision lives in the
runner, and a phase that does not apply says SKIPPED -- never OK.

A base that cannot be RESOLVED at all -- a wrong constant, a shallow clone
that never fetched it, an ambiguous short sha -- is NOT a phase that does
not apply. The gate fails on that base on purpose, so the runner must fail
on it too: skipping it would turn the gate system into a green no-op that
ran zero checks.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from sprite_pipeline import gate_ci


def _git(repo: Path, *args: str) -> str:
    """Run a git command in the temporary repository, and return its output."""
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "t"], check=True)
    (repo / "a.txt").write_text("a\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-q",
            "-m",
            "base",
        ],
        check=True,
    )
    return repo


def _head(repo: Path) -> str:
    """The commit the repository is standing on."""
    return _git(repo, "rev-parse", "HEAD")


def _not_an_ancestor(repo: Path) -> str:
    """A commit the repository HAS but HEAD does not contain.

    The base of a phase that does not apply is a commit the repository
    knows and that HEAD does not have -- not a sha that is not there at
    all: a sha that is not there is an ERROR, not a skip.
    """
    subprocess.run(
        ["git", "-C", str(repo), "checkout", "-q", "-b", "side"],
        check=True,
        capture_output=True,
    )
    (repo / "side.txt").write_text("side\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-q",
            "-m",
            "side",
        ],
        check=True,
        capture_output=True,
    )
    side = _head(repo)
    subprocess.run(
        ["git", "-C", str(repo), "checkout", "-q", "-"], check=True, capture_output=True
    )
    return side


def test_a_base_that_is_an_ancestor_applies(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    status, reason = gate_ci.applicable(_head(repo), repo)
    assert status is gate_ci.Applicability.APPLIES, reason


def test_a_base_that_cannot_be_resolved_is_an_error(tmp_path: Path) -> None:
    """A base that is NOT THERE is an error, not a phase that does not apply."""
    repo = _repo(tmp_path)
    status, reason = gate_ci.applicable("deadbeefdeadbeef", repo)
    assert status is gate_ci.Applicability.UNRESOLVABLE
    assert "deadbeefdeadbeef" in reason


def test_a_base_that_exists_but_is_not_an_ancestor_does_not_apply(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    status, reason = gate_ci.applicable(_not_an_ancestor(repo), repo)
    assert status is gate_ci.Applicability.NOT_AN_ANCESTOR
    assert reason


def test_a_phase_that_does_not_apply_says_skipped_and_never_ok(
    tmp_path: Path, capsys
) -> None:
    repo = _repo(tmp_path)
    ran: list[list[str]] = []

    def runner(argv: list[str]) -> int:
        ran.append(argv)
        return 0

    code = gate_ci.run_gate(1, repo, runner=runner, base=_not_an_ancestor(repo))
    out = capsys.readouterr().out
    assert code == 0
    assert "SKIPPED" in out
    assert "GATE OK" not in out
    assert ran == [], "the gate must NOT run for a phase that does not apply"


def test_a_base_that_cannot_be_resolved_fails_the_runner(
    tmp_path: Path, capsys
) -> None:
    """The gate FAILS on a base that is not there, so the runner fails too.

    A shallow checkout has no base object: skipping it would turn the
    whole gate system into a green job that ran zero checks.
    """
    repo = _repo(tmp_path)
    ran: list[list[str]] = []

    def runner(argv: list[str]) -> int:
        ran.append(argv)
        return 0

    code = gate_ci.run_gate(1, repo, runner=runner, base="deadbeefdeadbeef")
    out = capsys.readouterr().out
    assert code != 0
    assert "ERROR" in out
    assert "SKIPPED" not in out
    assert "GATE OK" not in out
    assert ran == [], "the gate must NOT run with a base it cannot measure"


def test_a_gate_that_fails_fails_the_runner(tmp_path: Path, capsys) -> None:
    repo = _repo(tmp_path)
    code = gate_ci.run_gate(1, repo, runner=lambda argv: 3, base=_head(repo))
    capsys.readouterr()
    assert code == 3


def test_the_runner_runs_the_gate_with_the_base_it_approved(
    tmp_path: Path, capsys
) -> None:
    """The gate measures the range the runner approved, not another one."""
    repo = _repo(tmp_path)
    base = _head(repo)
    ran: list[list[str]] = []

    def runner(argv: list[str]) -> int:
        ran.append(argv)
        return 0

    code = gate_ci.run_gate(1, repo, runner=runner, base=base)
    capsys.readouterr()
    assert code == 0
    assert ran == [["--phase", "1", "--base", base]]


def test_the_runner_honours_the_phase_base_environment_variable(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    """PHASE<n>_BASE decides the base, and the runner reaches it.

    The runner does not copy the constant: it asks the gate, so there is
    ONE source of truth for the base of a phase.
    """
    repo = _repo(tmp_path)
    base = _head(repo)
    monkeypatch.setenv("PHASE1_BASE", base)
    ran: list[list[str]] = []

    def runner(argv: list[str]) -> int:
        ran.append(argv)
        return 0

    code = gate_ci.run_gate(1, repo, runner=runner)
    capsys.readouterr()
    assert code == 0
    assert ran == [["--phase", "1", "--base", base]]
