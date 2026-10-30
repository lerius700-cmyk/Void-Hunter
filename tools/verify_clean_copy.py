"""Prove that a directory is an uncontaminated copy of a git tree.

A copy is uncontaminated when it holds EXACTLY the files of the tree and
EXACTLY the bytes of those files: nothing missing, nothing extra, nothing
altered. Eyeballing a tree cannot establish that; hashing every file
against its git blob can.

The copy is usually cut with `git archive`, which writes the blob bytes
verbatim -- no end-of-line conversion, no filters. That is what makes a
byte-for-byte comparison meaningful here.

What counts as contamination
----------------------------
A file that is not in the tree is NOT automatically contamination: a
Python runtime leaves `__pycache__/` and `logs/` behind, and those are
byproducts, not source. The line is the repository's own `.gitignore`:
an extra file that git ignores is a byproduct and is reported separately,
an extra file that git does NOT ignore is contamination.

That distinction is not academic. `Assets/keep kept - Lerius - soundtrack
gameplay_lp8000.wav` is NOT ignored, and a test run inside a copy will
generate it (61 MB) next to the source track -- so it is contamination,
and this tool says so.

Usage:
    python tools/verify_clean_copy.py --tree F:\\AI\\MM\\void-hunter-baseline-v1.8.0
    python tools/verify_clean_copy.py --tree <dir> --ref bloquec-67-goliath-port
    python tools/verify_clean_copy.py --tree <dir> --json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_REF = "bloquec-67-goliath-port"


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


def _expected(repo: Path, ref: str, paths: list[str] | None = None) -> dict[str, str]:
    """{path: blob hash} for every file of the ref.

    `paths` restricts the comparison to a subset of the tree, the same
    subset that was archived into the copy.
    """
    out: dict[str, str] = {}
    args = ["ls-tree", "-r", ref]
    if paths:
        args += ["--", *paths]
    for line in _git_lines(repo, args):
        # "<mode> SP <type> SP <object> TAB <path>" -- the path may hold
        # spaces, so the split is on the TAB, never on whitespace.
        meta, _, path = line.partition("\t")
        if not path:
            continue
        fields = meta.split()
        if fields[0] == "160000":
            continue  # a submodule, not a file of this tree
        out[path] = fields[2]
    return out


def _actual(tree: Path) -> dict[str, str]:
    """{path: blob hash} for every file on disk, hashed the git way.

    `git hash-object --stdin-paths` reads the paths from stdin and writes
    one hash per line, in the same order. It is a single process for the
    whole tree, and it hashes the raw bytes -- which is what `git archive`
    writes.

    The input is written as BYTES on purpose: in text mode Python
    translates every "\\n" into "\\r\\n" on Windows, and git would then
    read a path with a trailing carriage return.
    """
    paths = sorted(
        str(path.relative_to(tree)).replace("\\", "/")
        for path in tree.rglob("*")
        if path.is_file()
    )
    if not paths:
        return {}
    proc = subprocess.run(
        ["git", "-C", str(tree), "hash-object", "--stdin-paths"],
        input=("\n".join(paths) + "\n").encode("utf-8"),
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"git hash-object failed: {proc.stderr.decode('utf-8', 'replace').strip()}"
        )
    hashes = proc.stdout.decode("utf-8", "replace").split()
    if len(hashes) != len(paths):
        raise RuntimeError(
            f"git hash-object returned {len(hashes)} hashes for {len(paths)} paths"
        )
    return dict(zip(paths, hashes))


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

    `paths` restricts the comparison to a subset of the tree; None means
    the whole tree.
    """
    expected = _expected(repo, ref, paths)
    actual = _actual(tree)

    report = CleanCopyReport(tree=tree, ref=ref, checked=len(expected))
    for path, want in expected.items():
        got = actual.get(path)
        if got is None:
            report.missing.append(path)
        elif got != want:
            report.mismatched.append(path)

    unexpected = sorted(set(actual) - set(expected))
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
