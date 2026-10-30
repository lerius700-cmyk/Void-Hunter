"""BLOQUE 75: the truth anchors of the STATUS block must resolve.

The STATUS block of CLAUDE.md is auto-generated and claims to carry, for
each metric, the command that measures it. A truth anchor that points at
a path that no longer exists is worse than no block at all: it looks
verifiable and is not.

This module reads the block and checks that the file each truth anchor
names actually exists, and that the generator that rewrites the block
agrees with it. The build row is the one that broke: the release
worktree's `dist/` was archived during the repo cleanup, and the row
still pointed there.

The two checks together are the point. A block that lies and a generator
that agrees with the lie are worse than either alone: the next
regeneration puts the broken anchor back.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


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
    """The file a truth anchor names, resolved against the repo root."""
    match = re.search(r"`([^`]*void-hunter[^`]*\.exe)`", source)
    if not match:
        return None
    # The source is a command; the path is its last token.
    candidate = Path(match.group(1).split()[-1])
    return candidate if candidate.is_absolute() else (ROOT / candidate)


def test_the_status_block_has_rows():
    """The block is present and parseable. If this fails, the block moved."""
    rows = _status_rows()
    assert rows, "the STATUS block of CLAUDE.md could not be parsed"
    metrics = {metric for metric, _, _ in rows}
    assert "Tests (tests/)" in metrics
    assert "Rama" in metrics
    assert "Build .exe" in metrics


def test_the_build_truth_anchor_resolves():
    """The build row names a file that exists.

    This is the anchor that broke when the duplicated v1.8.0 binary was
    archived: the row pointed at the release worktree's `dist/`, and that
    copy no longer exists.
    """
    rows = dict((metric, source) for metric, _, source in _status_rows())
    path = _source_path(rows["Build .exe"])
    assert path is not None, f"the build row names no file: {rows['Build .exe']!r}"
    assert path.is_file(), (
        f"the build truth anchor points at {path}, which does not exist"
    )


def test_the_generator_writes_the_same_binary_the_block_shows():
    """`tools/regen_status.py` and the block agree.

    The generator is what rewrites the block. If it still names the old
    path, the next regeneration silently puts the broken anchor back.
    """
    rows = dict((metric, source) for metric, _, source in _status_rows())
    path = _source_path(rows["Build .exe"])
    assert path is not None
    generator = (ROOT / "tools" / "regen_status.py").read_text(encoding="utf-8")
    assert path.name in generator, (
        f"the generator does not mention {path.name!r}: it would rewrite "
        "the build row with a different path"
    )
