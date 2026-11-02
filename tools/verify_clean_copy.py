"""Prove that a directory is an uncontaminated copy of a git tree.

A copy is uncontaminated when it holds EXACTLY the files of the tree and
the same CONTENT git sees in them: nothing missing, nothing extra,
nothing altered. Eyeballing a tree cannot establish that; hashing every
file against its git blob can.

"the same content git sees" is not the same as "the same bytes", and
the difference is the whole point of asking git. With
`core.autocrlf=true` a CRLF file IS the same file as an LF blob, and
with `*.toml text eol=lf` a `.toml` is LF even on Windows. `git archive`
applies the same rules, so a copy cut with it comes out with CRLF text
files and LF `.toml` files -- and comparing that copy against the raw
blobs without the filters would call a perfect copy different on every
line. The comparison therefore uses git's own notion of equality.

What counts as contamination
----------------------------
A file that is not in the tree is NOT automatically contamination: a
Python runtime leaves `__pycache__/` and `logs/` behind, and those are
byproducts, not source. The line is the repository's own `.gitignore`:
an extra file that git ignores is a byproduct and is reported separately,
an extra file that git does NOT ignore is contamination.

That distinction cuts both ways. The repository's own `.gitignore`
carries `Assets/*_lp*.wav`, so the 61 MB filtered track that a test run
generates next to the source IS ignored: the tool reports it as litter,
not as contamination. A file the repository does NOT ignore --
`not_in_the_tree.txt`, a stray `.png` in `Assets/` -- is contamination,
and that is what the tool is for.

The default `--ref` is the branch the baseline is cut from. Verifying a
copy against any OTHER tree compares two different things and reports
the difference as contamination, which is a lie.

Usage:
    python tools/verify_clean_copy.py --tree F:\\AI\\MM\\void-hunter-baseline
    python tools/verify_clean_copy.py --tree <dir> --ref <ref>
    python tools/verify_clean_copy.py --tree <dir> --json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_REF = "bloquec-75-sprite-migration"


@dataclass
class CleanCopyReport:
    """The verdict of one comparison."""

    tree: Path
    ref: str
    checked: int = 0
    missing: list[str] = field(default_factory=list)
    extra: list[str] = field(default_factory=list)
    ignored_extra: list[str] = field(default_factory=list)
    mismatched: list[str] = field(default_factory=list)
    ignored_bytes: int = 0

    @property
    def ok(self) -> bool:
        """True when the copy is exactly the tree, source-wise."""
        return not (self.missing or self.extra or self.mismatched)

    def describe(self) -> str:
        """A human-readable report of everything that is wrong."""
        lines = [f"tree={self.tree} ref={self.ref} checked={self.checked}"]
        if self.ignored_extra:
            lines.append(
                f"ignored-extra: {len(self.ignored_extra)} files, "
                f"{self.ignored_bytes / (1024 * 1024):.1f} MB of runtime litter"
            )
        for label, items in (
            ("missing", self.missing),
            ("extra", self.extra),
            ("mismatched", self.mismatched),
            ("ignored-extra", self.ignored_extra),
        ):
            for item in items[:20]:
                lines.append(f"{label}: {item}")
            if len(items) > 20:
                lines.append(f"{label}: ... and {len(items) - 20} more")
        return "\n".join(lines)


def _git_lines(repo: Path, args: list[str]) -> list[str]:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.splitlines()


def _git_bytes(repo: Path, args: list[str]) -> bytes:
    """The raw stdout of a git command."""
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed: "
            f"{proc.stderr.decode('utf-8', 'replace').strip()}"
        )
    return proc.stdout


def _expected(repo: Path, ref: str, paths: list[str] | None = None) -> dict[str, str]:
    """{path: blob hash} for every file of the ref.

    `paths` restricts the comparison to a subset of the tree, the same
    subset that was archived into the copy.

    `-z` is not optional: without it git QUOTES and escapes every path
    that holds a non-ASCII character, and the quoted key can never match
    the real file on disk -- the file would show up as missing AND as
    extra.
    """
    out: dict[str, str] = {}
    args = ["ls-tree", "-r", "-z", ref]
    if paths:
        args += ["--", *paths]
    for chunk in _git_bytes(repo, args).split(b"\0"):
        if not chunk:
            continue
        meta, _, path = chunk.decode("utf-8").partition("\t")
        if not path:
            continue
        fields = meta.split()
        if fields[0] == "160000":
            continue  # a submodule, not a file of this tree
        out[path] = fields[2]
    return out


def _in_subset(rel: str, paths: list[str] | None) -> bool:
    """Whether a repo-relative path belongs to the compared subset."""
    if not paths:
        return True
    return any(rel == p or rel.startswith(p.rstrip("/") + "/") for p in paths)


def _tree_paths(repo: Path, ref: str) -> set[str]:
    """Every path of the tree, not a subset.

    This is what decides whether an extra file is REALLY extra: a file
    that is in the tree but outside the compared subset is part of the
    project, not contamination.
    """
    out: set[str] = set()
    for chunk in _git_bytes(repo, ["ls-tree", "-r", "-z", ref]).split(b"\0"):
        if not chunk:
            continue
        _, _, path = chunk.decode("utf-8").partition("\t")
        if path:
            out.add(path)
    return out


def _actual_paths(tree: Path) -> list[str]:
    """Every file of the copy, relative and sorted."""
    out: list[str] = []
    for path in tree.rglob("*"):
        if not path.is_file():
            continue
        rel = str(path.relative_to(tree)).replace("\\", "/")
        if rel == ".git" or rel.startswith(".git/"):
            continue
        out.append(rel)
    return sorted(out)


def _actual(tree: Path, paths: list[str] | None = None) -> dict[str, str]:
    """{path: blob hash} for the compared subset of the copy.

    `git hash-object --stdin-paths` reads the paths from stdin and writes
    one hash per line, in the same order. It is a single process for the
    whole tree.

    Two details make this correct rather than merely working:

    * The input is written as BYTES. In text mode Python translates
      every "\\n" into "\\r\\n" on Windows, and git would then read a
      path with a trailing carriage return.
    * The filters are applied, and that is the POINT. Git decides what
      "the same file" means with them: with `core.autocrlf=true` a
      CRLF file IS the same file as an LF blob, and with
      `*.toml text eol=lf` a `.toml` is LF even on Windows. Hashing
      without the filters would flag every legitimate copy as
      different, because `git archive` applies them too -- the archive
      of a text file comes out CRLF while its blob is LF.

    The subset restriction applies here: comparing `src` does not make
    the rest of the copy contamination, and it does not cost the hash of
    a file that was not asked about.
    """
    relatives = [
        rel for rel in _actual_paths(tree) if _in_subset(rel, paths)
    ]
    if not relatives:
        return {}
    proc = subprocess.run(
        ["git", "-C", str(tree), "hash-object", "--stdin-paths"],
        input=("\n".join(relatives) + "\n").encode("utf-8"),
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"git hash-object failed: "
            f"{proc.stderr.decode('utf-8', 'replace').strip()}"
        )
    hashes = proc.stdout.decode("utf-8", "replace").split()
    if len(hashes) != len(relatives):
        raise RuntimeError(
            f"git hash-object returned {len(hashes)} hashes for "
            f"{len(relatives)} paths"
        )
    return dict(zip(relatives, hashes))


def _ignored(repo: Path, paths: list[str]) -> set[str]:
    """Which of these paths the repository's .gitignore ignores.

    The paths are relative to the repository root, and so are the ones of
    a copy cut from it: the same rules apply.

    `-z` asks git for NUL-separated, UNQUOTED input AND output: a path
    that needs quoting (because it holds a character git considers
    unusual) would otherwise come back with the quotes baked into the
    string. With `-z` the INPUT is NUL-separated too.
    """
    if not paths:
        return set()
    proc = subprocess.run(
        ["git", "-C", str(repo), "check-ignore", "--stdin", "-z"],
        input=("\0".join(paths) + "\0").encode("utf-8"),
        capture_output=True,
    )
    # Exit code 1 simply means "nothing matched", which is not an error.
    out = proc.stdout.decode("utf-8", "replace")
    return {chunk for chunk in out.split("\0") if chunk}


def verify(
    tree: Path, ref: str, repo: Path, paths: list[str] | None = None
) -> CleanCopyReport:
    """Compare `tree` against the git tree `ref`.

    `paths` restricts the BYTE comparison to a subset of the tree; None
    means the whole tree. It does NOT restrict what counts as
    contamination: a file of the copy that is not in the tree at all is
    contamination wherever it sits, and a file that IS in the tree is
    not, even when it is outside the compared subset.
    """
    expected = _expected(repo, ref, paths)
    actual = _actual(tree, paths)

    report = CleanCopyReport(tree=tree, ref=ref, checked=len(expected))
    for path, want in expected.items():
        got = actual.get(path)
        if got is None:
            report.missing.append(path)
        elif got != want:
            report.mismatched.append(path)

    tree_paths = _tree_paths(repo, ref)
    unexpected = sorted(set(_actual_paths(tree)) - tree_paths)
    ignored = _ignored(repo, unexpected)
    for path in unexpected:
        if path in ignored:
            report.ignored_extra.append(path)
            report.ignored_bytes += (tree / path).stat().st_size
        else:
            report.extra.append(path)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tree", required=True, help="the directory to verify")
    parser.add_argument("--ref", default=DEFAULT_REF)
    parser.add_argument("--repo", default=str(Path(__file__).resolve().parent.parent))
    parser.add_argument(
        "--path",
        action="append",
        default=None,
        help="restrict the comparison to this path of the tree (repeatable)",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = verify(Path(args.tree), args.ref, Path(args.repo), args.path)
    if args.json:
        print(
            json.dumps(
                {
                    "tree": str(report.tree),
                    "ref": report.ref,
                    "checked": report.checked,
                    "missing": report.missing,
                    "extra": report.extra,
                    "ignored_extra": report.ignored_extra,
                    "mismatched": report.mismatched,
                    "ok": report.ok,
                },
                indent=2,
            )
        )
    else:
        print(report.describe())
    print("CLEAN COPY OK" if report.ok else "CONTAMINATED")
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
