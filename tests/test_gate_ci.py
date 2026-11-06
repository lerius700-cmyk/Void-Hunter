"""BLOQUE 75: the CI runner decides WHICH gates apply.

The gate itself is strict: a base commit that is not in the repository is a
FAILURE, and that is right for the branch the phase lives on. But the CI
runs on more than one branch, and `master` has neither the Phase 1 base nor
the Phase 2 base as an ancestor. So the APPLICABILITY decision lives in the
runner, and a phase that does not apply says SKIPPED -- never OK.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from sprite_pipeline import gate_ci


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "t"], check=True)
    (repo / "a.txt").write_text("a\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "base"], check=True)
    return repo


def test_a_base_that_is_an_ancestor_applies(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    base = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    applies, reason = gate_ci.applicable(base, repo)
    assert applies, reason


def test_a_base_that_is_not_in_the_repository_does_not_apply(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    applies, reason = gate_ci.applicable("deadbeefdeadbeef", repo)
    assert not applies
    assert "deadbeefdeadbeef" in reason


def test_a_phase_that_does_not_apply_says_skipped_and_never_ok(tmp_path: Path, capsys) -> None:
    repo = _repo(tmp_path)
    code = gate_ci.run_gate(1, repo, runner=lambda argv: 0, base="deadbeefdeadbeef")
    out = capsys.readouterr().out
    assert code == 0
    assert "SKIPPED" in out
    assert "GATE OK" not in out


def test_a_gate_that_fails_fails_the_runner(tmp_path: Path, capsys) -> None:
    repo = _repo(tmp_path)
    base = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    code = gate_ci.run_gate(1, repo, runner=lambda argv: 3, base=base)
    capsys.readouterr()
    assert code == 3


def test_the_runner_runs_every_phase_that_applies(tmp_path: Path, capsys) -> None:
    repo = _repo(tmp_path)
    base = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    ran: list[list[str]] = []

    def runner(argv: list[str]) -> int:
        ran.append(argv)
        return 0

    code = gate_ci.run_gate(1, repo, runner=runner, base=base)
    capsys.readouterr()
    assert code == 0
    assert ran == [["--phase", "1"]]
