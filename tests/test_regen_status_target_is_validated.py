"""BLOQUE 75 (follow-up 4.6): the generator writes only into a tree of THIS repo.

`VH_WT` names the tree the generator writes. It exists because the
repository is worked on by more than one agent, each in its own
worktree, and a generator that measured a FIXED tree would rewrite a
sibling agent's CLAUDE.md -- silently, with no error.

Before this, the variable was BELIEVED: a runner with a mistyped (or
hostile) `VH_WT` could point the generator at any directory on the
machine, and the tool would have written a STATUS block into it.

The target has to be a tree of this repository: a git checkout with its
own `CLAUDE.md`. That is what the override is FOR.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "tools" / "regen_status.py"

sys.path.insert(0, str(ROOT / "tools"))


def _run_with_vwt(target: Path) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["VH_WT"] = str(target)
    return subprocess.run(
        [sys.executable, str(TOOL)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=600,
    )


def test_the_generator_refuses_a_tree_that_is_not_a_repository(tmp_path: Path) -> None:
    """A `VH_WT` that is not a tree of this repo is REFUSED.

    The generator has to say so and NOT write: the block it writes is a
    document full of claims about a repository, and in a directory that
    has nothing to do with this one it would be a document full of
    lies.
    """
    foreign = tmp_path / "not-a-repo"
    foreign.mkdir()
    (foreign / "CLAUDE.md").write_text("# not ours\n", encoding="utf-8")

    proc = _run_with_vwt(foreign)
    assert proc.returncode != 0, "the generator wrote into a foreign directory"
    said = proc.stdout + proc.stderr
    assert "refuses" in said, said
    assert (foreign / "CLAUDE.md").read_text(encoding="utf-8") == "# not ours\n", (
        "the generator wrote into the foreign tree anyway"
    )


def test_the_generator_refuses_a_directory_that_does_not_exist(tmp_path: Path) -> None:
    """A `VH_WT` that does not exist is refused too."""
    proc = _run_with_vwt(tmp_path / "nope")
    assert proc.returncode != 0
    assert "refuses" in proc.stdout + proc.stderr


def test_the_generator_accepts_the_other_worktree_of_this_repository() -> None:
    """The override still does what it is FOR.

    The tree the tool lives in is a valid target, and so is any other
    checkout of this repository: the check is "is it a tree of ours",
    NOT "is it this exact tree".

    The validation is called DIRECTLY and not through the CLI: running
    the CLI would WRITE the block, and a test never writes in the
    repository (L7).
    """
    import regen_status

    regen_status._validate_target(ROOT)  # does not raise
