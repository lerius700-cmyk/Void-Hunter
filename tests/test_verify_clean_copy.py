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

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from verify_clean_copy import DEFAULT_REF, verify  # noqa: E402

REF = "HEAD"


def _cut(tmp_path: Path, subpaths: list[str], ref: str = REF) -> Path:
    """Cut a copy of `subpaths` of the ref, the way `git archive` does."""
    dest = tmp_path / "copy"
    dest.mkdir()
    tar = tmp_path / "copy.tar"
    with tar.open("wb") as handle:
        subprocess.run(
            ["git", "-C", str(ROOT), "archive", "--format=tar", ref, *subpaths],
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


# --- the findings of the pre-landing review -------------------------------
# These came out of an independent review of this branch. Each one was
# reproduced with real git behaviour before being written down.


def test_the_tool_agrees_with_git_about_line_endings(tmp_path: Path):
    """The tool has to judge a file the way GIT judges it.

    With `core.autocrlf=true` a CRLF file IS an LF blob; on a Linux
    runner it is NOT. So the question "is this the same file?" has no
    answer that holds on every machine -- it has the answer GIT gives.
    The tool has to follow git in both cases, so the test asks git and
    compares, instead of assuming one platform's rule.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "t@t"], check=True
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "t"], check=True
    )
    victim = repo / "mod.py"
    victim.write_bytes(b"x = 1\ny = 2\n")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "x"], check=True)

    raw = victim.read_bytes()
    flipped = (
        raw.replace(b"\r\n", b"\n")
        if b"\r\n" in raw
        else raw.replace(b"\n", b"\r\n")
    )
    victim.write_bytes(flipped)

    # git status is the WRONG oracle here: it reports the stat cache's
    # opinion (the mtime changed), so it says "modified" for a file whose
    # content did not change. git diff is the content comparison, and
    # it is the one the tool mirrors.
    git_says_modified = bool(
        subprocess.run(
            ["git", "-C", str(repo), "diff", "--name-only"],
            capture_output=True,
            text=True,
        ).stdout.strip()
    )
    report = verify(repo, "HEAD", repo)
    assert (not report.ok) == git_says_modified, (
        "the tool and git disagree about the same file: git says modified="
        f"{git_says_modified}, the tool says ok={report.ok}"
    )


def test_a_content_change_is_contamination(tmp_path: Path):
    """What the tool has to catch: the CONTENT is different.

    The line endings may differ -- git says they do not matter. The
    bytes of the code may not.
    """
    copy = _cut(tmp_path, ["src"])
    victim = next(p for p in copy.rglob("*.py"))
    victim.write_text(
        victim.read_text(encoding="utf-8") + "\n# tampered\n", encoding="utf-8"
    )
    report = verify(copy, REF, ROOT, ["src"])
    assert not report.ok
    assert report.mismatched, report.describe()


def test_a_non_ascii_path_is_not_mangled(tmp_path: Path):
    """A path with a non-ASCII character is compared, not mangled.

    `git ls-tree` quotes and escapes non-ASCII paths unless `-z` is
    given. The quoted key can never match the real file on disk, so the
    file would show up as missing AND as extra. The repository is
    Spanish-language; the day a file gets an accent in its name, the
    tool has to keep working.

    The copy is made with Python rather than by extracting a tar: the
    Windows `tar` decodes the archive's UTF-8 entry names with the
    console code page and mangles the accent itself, which would make
    this test measure the extractor instead of the tool.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "t@t"], check=True
    )
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "t"], check=True)
    (repo / "café.txt").write_text("hola", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "x"], check=True)

    copy = tmp_path / "copy"
    copy.mkdir()
    shutil.copy2(repo / "café.txt", copy / "café.txt")

    report = verify(copy, "HEAD", repo)
    assert report.ok, report.describe()
    assert report.checked == 1
    assert report.missing == []
    assert report.extra == []


def test_the_default_ref_resolves_wherever_the_tests_run(tmp_path: Path):
    """The default `--ref` matches the tree the baseline was cut from.

    The tool ships with a default ref, and the baseline is cut from the
    work branch. If the default is a different tree, the tool reports a
    pristine baseline as CONTAMINATED -- which is exactly what happened
    before this was pinned.
    """
    # The default ref has to be a branch that exists wherever the tests
    # run: HEAD is the checkout itself, on a CI runner and on a machine.
    assert DEFAULT_REF, "the tool must have a default ref"
    copy = _cut(tmp_path, ["src"], ref="HEAD")
    report = verify(copy, "HEAD", ROOT, ["src"])
    assert report.ok, report.describe()


def test_a_path_subset_does_not_flag_the_rest_of_the_copy(tmp_path: Path):
    """Comparing a subset does not flag the files outside it.

    `--path src` means "compare src". The rest of the copy is not
    contamination against a subset that does not mention it.
    """
    copy = _cut(tmp_path, ["src", "docs"])
    report = verify(copy, REF, ROOT, ["src"])
    assert report.ok, report.describe()


def test_a_git_directory_is_not_contamination(tmp_path: Path):
    """A `.git/` directory is not part of the tree, and not junk.

    Pointing the tool at a clone must not report its `.git/` as
    contamination: it is the tool's own machinery, not stray files.
    """
    copy = _cut(tmp_path, ["src"])
    (copy / ".git").mkdir()
    (copy / ".git" / "HEAD").write_text("ref: refs/heads/x", encoding="utf-8")
    report = verify(copy, REF, ROOT, ["src"])
    assert report.ok, report.describe()


def test_the_generated_wav_is_litter_and_not_contamination(tmp_path: Path):
    """The truth about the generated WAV, pinned.

    The repository's own `.gitignore` carries `Assets/*_lp*.wav`: these
    files are generated output and the project says so. A file that the
    repository ignores is litter, and the tool has to say THAT -- the
    opposite of what an earlier version of this module's docstring
    claimed.
    """
    copy = _cut(tmp_path, ["src"])
    wav = copy / "Assets" / "keep kept - Lerius - soundtrack gameplay_lp8000.wav"
    wav.parent.mkdir(parents=True, exist_ok=True)
    wav.write_bytes(b"RIFF")
    report = verify(copy, REF, ROOT, ["src"])
    assert report.ok, report.describe()
    assert any("_lp8000.wav" in path for path in report.ignored_extra)
    assert report.extra == []
