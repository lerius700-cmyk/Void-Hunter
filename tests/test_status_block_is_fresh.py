"""BLOQUE 75 (follow-up 7.a): the STATUS block has to be FRESH.

The block of CLAUDE.md is auto-generated: every row says what the repo
measured. That is only worth something if somebody can CHECK it -- and
nobody could. The generator computed the rows inside `main()`, which
also WROTE the block, so the only way to ask "what would it say today?"
was to write to the repository. L7 forbids a test from writing there.

So the rows are now computed by a PURE function (`regen_status.rows_for`),
and this file compares them against the committed block.

WHAT IS COMPARED, AND WHY NOT EVERYTHING
----------------------------------------

Three rows cannot be compared, and saying so is part of the check:

* the three WEIGHTS (the tracked tree, the build output, the history):
  they measure the repository, and the COMMIT that carries the block
  changes them. A block regenerated before the commit is stale by
  definition -- comparing them would make this test red forever.
* the `Tests` row: it needs the SUITE, and a test that runs the suite
  runs the suite inside the suite. It is compared against the COLLECTED
  count instead, which is fast and executes nothing.
* the `Build .exe` row: it needs the ARTIFACT, which is a build output
  (gitignored, absent on a fresh clone). It is compared when this
  machine has it.

Everything else -- the LOC counts, the file count, the silos, the
version and the branch -- is a pure function of the tree, and THAT is
where a stale block shows up: someone adds code and nobody regenerates.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import regen_status  # noqa: E402

# The rows that are a pure function of the tree: the same on every
# machine, and the same before and after a commit.
TREE_ROWS = (
    "Líneas de código (src/)",
    "Archivos Python (src/)",
    "LOC tests/",
    "Silos SF+SM",
    "Versión",
    "Rama",
)


def _committed_rows() -> dict[str, str]:
    """The rows the COMMITTED block says, as {metric: value}."""
    text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    start = text.index("STATUS:GENERATED")
    rows: dict[str, str] = {}
    for line in text[start:].splitlines():
        match = re.match(r"^\| ([^|]+?) \| (.*?) \| (.*?) \|$", line)
        if match:
            metric = match.group(1).strip()
            if metric in ("Métrica", "---------"):
                continue
            rows[metric] = match.group(2).strip()
        elif rows:
            break
    return rows


def _collected_count() -> int:
    """How many tests the suite HAS, counted without running any."""
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests", "--collect-only"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    match = re.search(r"(\d+) tests? collected", proc.stdout)
    assert match, (
        "could not read the collected count from pytest:\n"
        f"{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}"
    )
    return int(match.group(1))


def test_the_committed_block_says_what_the_generator_would_say() -> None:
    """The rows of the block are the rows the generator computes today.

    A stale block is a block that lies: it says "3.165 tests" when the
    suite has 3.186, and the reader has no way to tell.
    """
    committed = _committed_rows()
    computed = regen_status.rows_for(ROOT)
    for metric in TREE_ROWS:
        assert metric in committed, f"the block has no row {metric!r}"
        assert committed[metric] == computed[metric], (
            f"the row {metric!r} says {committed[metric]!r} but the generator "
            f"computes {computed[metric]!r}: the block is STALE -- run "
            "`python tools/regen_status.py`"
        )


def test_the_committed_test_count_is_the_number_of_tests() -> None:
    """The total of the `Tests` row is the number of tests there are.

    The row's breakdown (pass/skip/xfail) needs a real run, but its
    TOTAL is the collected count, and that is what tells a reader
    whether a test was added without regenerating the block.
    """
    row = _committed_rows()["Tests (tests/)"]
    match = re.search(r"\(([\d.]+) total\)", row)
    assert match, f"the row has no total: {row!r}"
    total = int(match.group(1).replace(".", ""))
    collected = _collected_count()
    assert total == collected, (
        f"the block says {total} tests and the suite collects {collected}: "
        "the block is STALE -- run `python tools/regen_status.py`"
    )


def test_the_committed_build_row_matches_the_artifact() -> None:
    """The build row matches the binary, when this machine has it.

    The artifact is a build output: it is gitignored, and a fresh clone
    does not have it. Its absence is not a defect of the repository.
    """
    exe = regen_status.REPO_ROOT / regen_status.BINARY_REL
    if not exe.is_file():
        return
    committed = _committed_rows()["Build .exe"]
    assert regen_status.BINARY_REL in committed, committed
    assert regen_status._sha256(exe) in committed, (
        "the build row does not carry the hash of the binary that is on "
        "disk: the block is STALE -- run `python tools/regen_status.py`"
    )


def test_the_generator_does_not_write_when_it_is_only_asked() -> None:
    """`rows_for` is PURE: asking the question leaves no trace.

    This is the property the whole check rests on: a generator that
    writes cannot be asked what it would say, and a test that writes to
    the repository breaks L7.
    """
    before = (ROOT / "CLAUDE.md").read_bytes()
    regen_status.rows_for(ROOT)
    after = (ROOT / "CLAUDE.md").read_bytes()
    assert before == after, "computing the rows wrote to the repository"
