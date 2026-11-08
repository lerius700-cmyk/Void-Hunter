"""BLOQUE 75: the truth anchors of the STATUS block must resolve.

The STATUS block of CLAUDE.md is auto-generated and claims to carry, for
each metric, the command that measures it. A truth anchor that points at
a path that no longer exists is worse than no block at all: it looks
verifiable and is not.

This module reads the block and checks the two properties the
repository owns:

* the build row names the canonical binary, and the generator that
  writes the block measures the SAME file -- a block that lies and a
  generator that agrees with the lie is worse than either alone;
* the build artifact, when this machine has it, is really there.

The artifact itself is a BUILD OUTPUT: it is gitignored, and a fresh
clone does not have it. Its absence is not a defect of the repository,
so the test that needs it skips instead of failing -- otherwise the
suite would go red on CI for a reason that has nothing to do with the
code.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from regen_status import BINARY_REL, REPO_ROOT, VERSION  # noqa: E402


def _status_rows() -> list[tuple[str, str, str]]:
    """(metric, value, source) for every row of the STATUS table."""
    text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    start = text.index("STATUS:GENERATED")
    rows: list[tuple[str, str, str]] = []
    for line in text[start:].splitlines():
        match = re.match(r"^\| ([^|]+?) \| (.*?) \| (.*?) \|$", line)
        if match:
            metric = match.group(1).strip()
            if metric in ("Métrica", "---------"):
                continue
            rows.append((metric, match.group(2).strip(), match.group(3).strip()))
        elif rows:
            break
    return rows


def _source_path(source: str) -> Path | None:
    """The file a truth anchor names, resolved against the repository root.

    The anchor is RELATIVE: an absolute path would name one machine and
    resolve nowhere else -- the CI included.
    """
    match = re.search(r"`([^`]*void-hunter[^`]*\.exe)`", source)
    if not match:
        return None
    # The source is a command; the path is its last token.
    candidate = Path(match.group(1).split()[-1])
    if candidate.is_absolute():
        return candidate
    return REPO_ROOT / candidate


def test_the_status_block_has_rows():
    """The block is present and parseable. If this fails, the block moved."""
    rows = _status_rows()
    assert rows, "the STATUS block of CLAUDE.md could not be parsed"
    metrics = {metric for metric, _, _ in rows}
    assert "Tests (tests/)" in metrics
    assert "Rama" in metrics
    assert "Build .exe" in metrics


def test_the_build_truth_anchor_names_the_canonical_binary():
    """The build row names the file the generator measures.

    This is the anchor that broke when the duplicated v1.8.0 binary was
    archived: the row pointed at the release worktree's `dist/`, and
    that copy no longer exists.
    """
    rows = dict((metric, source) for metric, _, source in _status_rows())
    path = _source_path(rows["Build .exe"])
    assert path is not None, f"the build row names no file: {rows['Build .exe']!r}"
    assert path == REPO_ROOT / BINARY_REL, (
        f"the build row names {path}, but the generator measures "
        f"{REPO_ROOT / BINARY_REL}"
    )


def test_the_generator_writes_the_same_binary_the_block_shows():
    """`tools/regen_status.py` and the block agree.

    The generator is what rewrites the block. If it still names the old
    path, the next regeneration silently puts the broken anchor back.

    BLOQUE 76: the comparison is against the generator's COMPUTED path,
    not against its source text. The path used to be a literal spelled
    out in the generator, so grepping the source proved the agreement; it
    is now DERIVED from the version (one place to bump, not two), and the
    source no longer contains the file name. What has to hold is that the
    generator and the block name the SAME file.
    """
    rows = dict((metric, source) for metric, _, source in _status_rows())
    path = _source_path(rows["Build .exe"])
    assert path is not None
    assert path == REPO_ROOT / BINARY_REL, (
        f"the block names {path}, but the generator measures "
        f"{REPO_ROOT / BINARY_REL}"
    )


def test_the_binary_path_is_derived_from_the_version():
    """The version is written ONCE.

    It used to be written twice -- once as VERSION and once inside the
    binary's file name -- and the generator's own comment claimed there
    was only one place. Bumping VERSION alone left the block naming the
    PREVIOUS release's binary, with that file's SHA256, under the new
    version's label.
    """
    assert BINARY_REL == f"dist/void-hunter-{VERSION}.exe"
    assert VERSION in BINARY_REL


def test_the_build_artifact_is_there_when_this_machine_has_it():
    """The artifact is real when it is there.

    It is a build output, so it is not in the repository and a fresh
    clone does not have it. When this machine DOES have it, the anchor
    has to point at a real file.
    """
    path = REPO_ROOT / BINARY_REL
    if not path.is_file():
        pytest.skip("this machine has no build artifact")
    assert path.stat().st_size > 0
