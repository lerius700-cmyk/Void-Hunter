"""BLOQUE 75: a copy of the tree must be provably uncontaminated.

`F:\\AI\\MM\\void-hunter-baseline-v1.8.0` is the restore point for the
BLOQUE 75 migration. "It looks clean" is not a property anyone can check
by eye: the check is that the copy contains EXACTLY the files of a git
tree, with EXACTLY the bytes of those files.

This module exercises the tool in both directions: green on a copy that
was cut with `git archive`, red on a copy with an extra file, red on a
copy whose bytes were tampered with, and red on a copy that lost a file.

It also pins the distinction the tool draws between two kinds of extra
file. A `__pycache__` entry is a byproduct of running Python and is
ignored by the repository, so it does not make a copy contaminated. A
generated WAV next to the source track is NOT ignored, so it does: that
file is 61 MB and a test run inside a copy will create it.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from verify_clean_copy import verify  # noqa: E402

REF = "bloquec-67-goliath-port"


def _cut(tmp_path: Path, subpaths: list[str]) -> Path:
    """Cut a copy of `subpaths` of the ref, the way `git archive` does."""
    dest = tmp_path / "copy"
    dest.mkdir()
    tar = tmp_path / "copy.tar"
    with tar.open("wb") as handle:
        subprocess.run(
            ["git", "-C", str(ROOT), "archive", "--format=tar", REF, *subpaths],
            check=True,
            stdout=handle,
        )
    subprocess.run(
        ["tar", "-xf", str(tar), "-C", str(dest)], check=True, capture_output=True
    )
    return dest


def test_a_clean_copy_verifies(tmp_path: Path):
    """The happy path: a copy cut with `git archive` passes."""
    copy = _cut(tmp_path, ["src", "docs"])
    report = verify(copy, REF, ROOT, ["src", "docs"])
    assert report.ok, report.describe()
    assert report.missing == []
    assert report.extra == []
    assert report.mismatched == []
    assert report.checked > 0


def test_an_extra_file_is_contamination(tmp_path: Path):
    """A file that is not in the tree and is not ignored is contamination."""
    copy = _cut(tmp_path, ["src", "docs"])
    (copy / "not_in_the_tree.txt").write_text("leftover", encoding="utf-8")
    report = verify(copy, REF, ROOT, ["src", "docs"])
    assert not report.ok
    assert "not_in_the_tree.txt" in report.extra


def test_a_missing_file_is_damage(tmp_path: Path):
    """A file the tree declares but the copy lacks is damage."""
    copy = _cut(tmp_path, ["src", "docs"])
    victim = next(p for p in copy.rglob("*.py"))
    victim.unlink()
    report = verify(copy, REF, ROOT, ["src", "docs"])
    assert not report.ok
    assert report.missing
    assert any("missing" in line for line in report.describe().splitlines())


def test_tampered_bytes_are_damage(tmp_path: Path):
    """Same file set, different bytes: still contamination."""
    copy = _cut(tmp_path, ["src", "docs"])
    victim = next(p for p in copy.rglob("*.py"))
    victim.write_text(
        victim.read_text(encoding="utf-8") + "\n# tampered\n", encoding="utf-8"
    )
    report = verify(copy, REF, ROOT, ["src", "docs"])
    assert not report.ok
    assert report.mismatched


def test_an_ignored_byproduct_does_not_contaminate(tmp_path: Path):
    """A `__pycache__` entry is a runtime byproduct, not contamination.

    The repository ignores `__pycache__/`, so the tool reports it
    separately and the copy still passes. Without this distinction the
    tool would be useless against a copy anyone ever ran Python in.
    """
    copy = _cut(tmp_path, ["src", "docs"])
    cache = copy / "src" / "__pycache__"
    cache.mkdir(parents=True, exist_ok=True)
    (cache / "manifest.cpython-311.pyc").write_bytes(b"\x00\x01")
    report = verify(copy, REF, ROOT, ["src", "docs"])
    assert report.ok, report.describe()
    assert report.ignored_extra
    assert report.extra == []
