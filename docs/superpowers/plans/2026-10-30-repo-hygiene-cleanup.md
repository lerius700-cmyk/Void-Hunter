# Repo Hygiene & Pristine Baseline — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cut a provably uncontaminated copy of the released game to `F:\AI\MM\void-hunter-baseline-v1.8.0\`, move 13.4 GB of dead build artifacts out of the repository to `F:\AI\MM\_vh_archive_2026-10-30\`, and leave the repository measured, verified and documented.

**Architecture:** Two invariants drive everything. (1) Nothing is deleted — every removal is a *move*, and because source and destination are on the same `F:` volume, every move is an instant rename. (2) The baseline is cut and proven *before* a single byte is moved, because a restore point created after the damage cannot prove it did not cause it. A third property falls out of the first: the moves touch only git-ignored files, so the tracked tree cannot change — which is asserted, not assumed.

**Tech Stack:** PowerShell 5.1 (Windows), Git, Python 3.11 (`F:\AI\MM\void-hunter\.venv\Scripts\python.exe`), pytest, `sf-sm-doctor`, `gstack-review`.

**Spec:** `docs/superpowers/specs/2026-10-30-repo-hygiene-cleanup-design.md` (commit `82e0a38`).

---

## Global Constraints

These apply to EVERY task. They are not restated per task.

- **PowerShell only.** No `&&`, no `ls -la`, no `head`/`tail`/`grep`/`wc`. Use `;`, `Get-ChildItem`, `Select-Object`, `Select-String`. Start multi-statement scripts with `$ErrorActionPreference = 'Stop'`.
- **Never delete.** `Remove-Item -Recurse -Force` is blocked by the harness and is forbidden by the design. Every removal is `Move-Item`.
- **Never touch `.worktrees\bloquec-75-migration-spec\`.** A second agent is working there right now.
- **Never commit to `master` or to `bloquec-67-goliath-port`.** Commits land on `bloquec-75-sprite-migration` only, in the worktree `F:\AI\MM\void-hunter\.worktrees\bloquec-75-sprite-migration`.
- **The four `Assets/*.wav` stay tracked.** Decision D1. Do not `git rm` them, do not gitignore them, do not regenerate them.
- **Do not regenerate art, do not touch `GOLIATH_SHIELD_*` constants.** This plan moves files; it does not touch the game.
- **The venv is `F:\AI\MM\void-hunter\.venv\Scripts\python.exe`.** The baseline copy has no venv and does not need one.
- **Tests:** `python -m pytest tests/ --tb=no` (pyproject already sets the verbosity; do not add `-q`).
- **Commit prefix convention:** `feat:` / `fix:` / `chore:` / `docs:` followed by `BLOQUE 75`.
- **Code, comments and technical docs in English.** Chat with the user in Spanish.

---

## File Structure

| Path | Responsibility | Task |
|---|---|---|
| `F:\AI\MM\void-hunter-baseline-v1.8.0\` | The pristine copy. Not in the repository. | 1 |
| `tools/verify_clean_copy.py` | **New.** Proves a directory is an uncontaminated copy of a git tree: same file set, same bytes. | 2 |
| `tests/test_verify_clean_copy.py` | **New.** Unit tests for the tool, both directions. | 2 |
| `F:\AI\MM\_vh_archive_2026-10-30\` | Everything removed from the working tree, plus `MANIFEST.md`. | 3 |
| `tools/regen_status.py` | **Modified.** The build row's truth anchor moves with the binary. | 4 |
| `tests/test_status_truth_anchors.py` | **New.** Asserts the truth anchors of the STATUS block resolve. | 4 |
| `docs/arch/MAINTENANCE-CLEANUP-2026-10-30.md` | **New.** What was archived, why, how to restore. | 5 |
| `F:\AI\MM\_vh_archive_2026-10-30\MANIFEST.md` | Same content, lives with the archive. | 5 |
| `.synapse` | **Modified.** Objective, last action, verification timestamp. | 5 |
| `CLAUDE.md` | **Modified.** The `STATUS:GENERATED` block, regenerated. | 5 |

---

### Task 1: Cut and prove the pristine baseline

**Files:**
- Create: `F:\AI\MM\void-hunter-baseline-v1.8.0\` (2,267 files, 271 MB, outside the repository)

**Interfaces:**
- Consumes: the `bloquec-67-goliath-port` git tree.
- Produces: a directory that Tasks 3+ can restore from, and that Task 2's tool will be written against.

- [ ] **Step 1: Record the "before" truth anchors**

Run from `F:\AI\MM\void-hunter`:

```powershell
$root = 'F:\AI\MM\void-hunter'
"{0:N2} GB" -f ((Get-ChildItem $root -Recurse -File -Force | Measure-Object Length -Sum).Sum / 1GB)
git -C $root worktree list
git -C $root log --oneline -1 bloquec-67-goliath-port
```

Expected: `15.70 GB`, three worktrees listed, release line at `5d12b10`.

- [ ] **Step 2: Capture the expected file list and blob hashes**

```powershell
$root = 'F:\AI\MM\void-hunter'
git -C $root ls-tree -r bloquec-67-goliath-port | Out-File -Encoding utf8 "$env:TEMP\vh_expected_tree.txt"
(Get-Content "$env:TEMP\vh_expected_tree.txt" | Measure-Object).Count
```

Expected: `2267`.

- [ ] **Step 3: Cut the archive**

```powershell
$root = 'F:\AI\MM\void-hunter'
$dest = 'F:\AI\MM\void-hunter-baseline-v1.8.0'
if (Test-Path $dest) { throw "the baseline already exists: $dest" }
New-Item -ItemType Directory -Force -Path $dest | Out-Null
git -C $root archive --format=tar bloquec-67-goliath-port -o "$env:TEMP\vh_baseline.tar"
tar -xf "$env:TEMP\vh_baseline.tar" -C $dest
```

Expected: no errors. `tar` is the Windows 10+ bsdtar, shipped with the OS.

- [ ] **Step 4: Verify the file set is exactly the git tree**

```powershell
$dest = 'F:\AI\MM\void-hunter-baseline-v1.8.0'
$actual = Get-ChildItem $dest -Recurse -File -Force | ForEach-Object { $_.FullName.Substring($dest.Length + 1).Replace('\','/') }
$expected = Get-Content "$env:TEMP\vh_expected_tree.txt" | ForEach-Object { ($_ -split '\s+',5)[4] }
"actual=$($actual.Count) expected=$($expected.Count)"
Compare-Object ($actual | Sort-Object) ($expected | Sort-Object) | Format-Table -AutoSize
```

Expected: `actual=2267 expected=2267` and **no output** from `Compare-Object` (no `<=` / `=>` side indicators). Any difference means the copy is contaminated — stop and re-cut.

- [ ] **Step 5: Verify the bytes match the blobs**

```powershell
$dest = 'F:\AI\MM\void-hunter-baseline-v1.8.0'
Push-Location $dest
Get-ChildItem . -Recurse -File -Force | ForEach-Object { $_.FullName.Substring($dest.Length + 1) } | & git -C $dest hash-object --stdin-paths
Pop-Location
```

Expected: 2,267 hashes, in the same order as `git ls-tree -r`, each matching the blob hash on the corresponding `ls-tree` line. A mismatch means the archive was altered — re-cut rather than patch.

- [ ] **Step 6: Verify the copy boots**

```powershell
$py = 'F:\AI\MM\void-hunter\.venv\Scripts\python.exe'
Push-Location 'F:\AI\MM\void-hunter-baseline-v1.8.0'
& $py main.py --check
Pop-Location
```

Expected: `BLOQUE 16: full game with 15 scenes, 18 waves, 4 bosses.` and exit 0. **If it fails: stop and use systematic-debugging. Do not "fix" the copy — re-cut it and find out why.**

- [ ] **Step 7: Verify the copy tests**

```powershell
$py = 'F:\AI\MM\void-hunter\.venv\Scripts\python.exe'
Push-Location 'F:\AI\MM\void-hunter-baseline-v1.8.0'
& $py -m pytest tests/ --tb=no
Pop-Location
```

Expected: `2 failed`? No — expected `1 failed, 2886 passed, 6 skipped`. The single failure is the known pre-existing `tests/test_paths.py::test_paths_no_star_shapes`.

- [ ] **Step 8: Verify the sprite contract guard works from the copy**

```powershell
$py = 'F:\AI\MM\void-hunter\.venv\Scripts\python.exe'
Push-Location 'F:\AI\MM\void-hunter-baseline-v1.8.0'
& $py tools\sprite_pipeline\verify_contract.py goliath
Pop-Location
```

Expected: `CONTRACT OK`, exit 0.

- [ ] **Step 9: Record the baseline's identity**

```powershell
$dest = 'F:\AI\MM\void-hunter-baseline-v1.8.0'
"{0:N1} MB / {1} archivos" -f ((Get-ChildItem $dest -Recurse -File -Force | Measure-Object Length -Sum).Sum/1MB), (Get-ChildItem $dest -Recurse -File -Force | Measure-Object).Count
```

Expected: `271.4 MB / 2267 archivos`. Write both numbers into the Task 5 document.

---

### Task 2: Build the tool that proves a copy is uncontaminated

**Files:**
- Create: `tools/verify_clean_copy.py`
- Test: `tests/test_verify_clean_copy.py`

**Interfaces:**
- Consumes: a directory path and a git ref.
- Produces: `verify_clean_copy(tree: Path, ref: str, repo: Path) -> CleanCopyReport` and a CLI. Later tasks and future sessions call it to re-verify the baseline.

- [ ] **Step 1: Write the failing test**

Create `tests/test_verify_clean_copy.py`:

```python
"""BLOQUE 75: a copy of the tree must be provably uncontaminated.

`F:\\AI\\MM\\void-hunter-baseline-v1.8.0` is the restore point for the
BLOQUE 75 migration. "It looks clean" is not a property anyone can check
by eye: the check is that the copy contains EXACTLY the files of a git
tree, with EXACTLY the bytes of those files.

This module exercises the tool in both directions: green on a copy that
was cut with `git archive`, red on a copy with an extra file and red on
a copy whose bytes were tampered with.
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

from verify_clean_copy import verify  # noqa: E402

REF = "bloquec-67-goliath-port"


def _cut(tmp_path: Path, subpaths: list[str]) -> Path:
    """Cut a copy of `subpaths` of the ref, the way `git archive` does."""
    dest = tmp_path / "copy"
    dest.mkdir()
    tar = tmp_path / "copy.tar"
    subprocess.run(
        ["git", "-C", str(ROOT), "archive", "--format=tar", REF, *subpaths],
        check=True,
        stdout=tar.open("wb"),
    )
    subprocess.run(
        ["tar", "-xf", str(tar), "-C", str(dest)], check=True, capture_output=True
    )
    return dest


def test_a_clean_copy_verifies(tmp_path: Path):
    """The happy path: a copy cut with `git archive` passes."""
    copy = _cut(tmp_path, ["src", "docs"])
    report = verify(copy, REF, ROOT)
    assert report.ok, report.describe()
    assert report.missing == []
    assert report.extra == []
    assert report.mismatched == []
    assert report.checked > 0


def test_an_extra_file_is_detected(tmp_path: Path):
    """A file that is not in the tree is contamination."""
    copy = _cut(tmp_path, ["src", "docs"])
    (copy / "not_in_the_tree.txt").write_text("leftover", encoding="utf-8")
    report = verify(copy, REF, ROOT)
    assert not report.ok
    assert "not_in_the_tree.txt" in report.extra


def test_a_missing_file_is_detected(tmp_path: Path):
    """A file the tree declares but the copy lacks is damage."""
    copy = _cut(tmp_path, ["src", "docs"])
    victim = next(p for p in copy.rglob("*.py"))
    victim.unlink()
    report = verify(copy, REF, ROOT)
    assert not report.ok
    assert any("missing" in m for m in report.describe())


def test_tampered_bytes_are_detected(tmp_path: Path):
    """Same file set, different bytes: still contamination."""
    copy = _cut(tmp_path, ["src", "docs"])
    victim = next(p for p in copy.rglob("*.py"))
    victim.write_text(victim.read_text(encoding="utf-8") + "\n# tampered\n", encoding="utf-8")
    report = verify(copy, REF, ROOT)
    assert not report.ok
    assert report.mismatched
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `F:\AI\MM\void-hunter\.venv\Scripts\python.exe -m pytest tests\test_verify_clean_copy.py --tb=short`

Expected: FAIL with `ModuleNotFoundError: No module named 'verify_clean_copy'`.

- [ ] **Step 3: Write the implementation**

Create `tools/verify_clean_copy.py`:

```python
"""Prove that a directory is an uncontaminated copy of a git tree.

A copy is uncontaminated when it holds EXACTLY the files of the tree and
EXACTLY the bytes of those files: nothing missing, nothing extra, nothing
altered. Eyeballing a tree cannot establish that; hashing every file
against its git blob can.

The copy is usually cut with `git archive`, which writes the blob bytes
verbatim -- no end-of-line conversion, no filters. That is what makes a
byte-for-byte comparison meaningful here.

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


@dataclass
class CleanCopyReport:
    """The verdict of one comparison."""

    tree: Path
    ref: str
    checked: int = 0
    missing: list[str] = field(default_factory=list)
    extra: list[str] = field(default_factory=list)
    mismatched: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True when the copy is exactly the tree."""
        return not (self.missing or self.extra or self.mismatched)

    def describe(self) -> str:
        """A human-readable report of everything that is wrong."""
        lines = [f"tree={self.tree} ref={self.ref} checked={self.checked}"]
        for label, items in (
            ("missing", self.missing),
            ("extra", self.extra),
            ("mismatched", self.mismatched),
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


def _expected(repo: Path, ref: str) -> dict[str, str]:
    """{path: blob hash} for every file of the ref."""
    out: dict[str, str] = {}
    for line in _git_lines(repo, ["ls-tree", "-r", ref]):
        parts = line.split(None, 4)
        if len(parts) < 5:
            continue
        meta, path = parts[3], parts[4]
        if meta.startswith("160000"):
            continue  # a submodule, not a file of this tree
        out[path] = meta.split()[1]
    return out


def _actual(tree: Path) -> dict[str, str]:
    """{path: blob hash} for every file on disk, hashed the git way.

    `git hash-object --stdin-paths` reads the paths from stdin and writes
    one hash per line, in the same order. It is a single process for the
    whole tree, and it hashes the raw bytes -- which is what `git archive`
    writes.
    """
    paths: list[str] = []
    for path in sorted(tree.rglob("*")):
        if path.is_file():
            paths.append(str(path.relative_to(tree)).replace("\\", "/"))
    if not paths:
        return {}
    proc = subprocess.run(
        ["git", "-C", str(tree), "hash-object", "--stdin-paths"],
        input="\n".join(paths) + "\n",
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git hash-object failed: {proc.stderr.strip()}")
    hashes = proc.stdout.split()
    if len(hashes) != len(paths):
        raise RuntimeError(
            f"git hash-object returned {len(hashes)} hashes for {len(paths)} paths"
        )
    return dict(zip(paths, hashes))


def verify(tree: Path, ref: str, repo: Path) -> CleanCopyReport:
    """Compare `tree` against the git tree `ref`."""
    expected = _expected(repo, ref)
    actual = _actual(tree)

    report = CleanCopyReport(tree=tree, ref=ref, checked=len(expected))
    for path, want in expected.items():
        got = actual.get(path)
        if got is None:
            report.missing.append(path)
        elif got != want:
            report.mismatched.append(path)
    for path in actual:
        if path not in expected:
            report.extra.append(path)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tree", required=True, help="the directory to verify")
    parser.add_argument("--ref", default="bloquec-67-goliath-port")
    parser.add_argument("--repo", default=str(Path(__file__).resolve().parent.parent))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = verify(Path(args.tree), args.ref, Path(args.repo))
    if args.json:
        print(
            json.dumps(
                {
                    "tree": str(report.tree),
                    "ref": report.ref,
                    "checked": report.checked,
                    "missing": report.missing,
                    "extra": report.extra,
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
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `F:\AI\MM\void-hunter\.venv\Scripts\python.exe -m pytest tests\test_verify_clean_copy.py --tb=short`

Expected: `4 passed`.

- [ ] **Step 5: Run the tool against the real baseline**

Run:

```powershell
F:\AI\MM\void-hunter\.venv\Scripts\python.exe tools\verify_clean_copy.py --tree F:\AI\MM\void-hunter-baseline-v1.8.0
```

Expected: `checked=2267`, no missing/extra/mismatched, `CLEAN COPY OK`, exit 0.

- [ ] **Step 6: Commit**

```bash
git add tools/verify_clean_copy.py tests/test_verify_clean_copy.py
git commit -m "test: BLOQUE 75 - la herramienta que prueba que una copia del arbol esta limpia"
```

---

### Task 3: Move the dead artifacts out of the repository

**Files:**
- Move: everything listed below into `F:\AI\MM\_vh_archive_2026-10-30\`

**Interfaces:**
- Consumes: the verified baseline from Task 1 (the restore point exists BEFORE anything moves).
- Produces: a repository of ~2.3 GB and an archive of ~13.4 GB, every move verified.

- [ ] **Step 1: Create the archive skeleton and record the "before" size**

```powershell
$ErrorActionPreference = 'Stop'
$root = 'F:\AI\MM\void-hunter'
$wt   = 'F:\AI\MM\void-hunter\.worktrees\bloquec-67-goliath-port'
$arch = 'F:\AI\MM\_vh_archive_2026-10-30'
if (Test-Path $arch) { throw "the archive already exists: $arch" }
New-Item -ItemType Directory -Force -Path $arch | Out-Null
"{0:N2} GB before" -f ((Get-ChildItem $root -Recurse -File -Force | Measure-Object Length -Sum).Sum / 1GB)
```

Expected: `15.70 GB before`.

- [ ] **Step 2: Move the 24 stale entries of `dist/`, keeping `void-hunter-v1.8.0.exe`**

```powershell
$root = 'F:\AI\MM\void-hunter'
$arch = 'F:\AI\MM\_vh_archive_2026-10-30'
New-Item -ItemType Directory -Force -Path "$arch\dist_old_builds" | Out-Null
Get-ChildItem "$root\dist" -Force | Where-Object { $_.Name -ne 'void-hunter-v1.8.0.exe' } |
    ForEach-Object { Move-Item $_.FullName "$arch\dist_old_builds" -Force }
Get-ChildItem "$root\dist" -Force | Select-Object -ExpandProperty Name
```

Expected: exactly one entry left, `void-hunter-v1.8.0.exe`.

- [ ] **Step 3: Move the dead v1.1.x release zips, keeping `release/videos/`**

```powershell
$root = 'F:\AI\MM\void-hunter'
$arch = 'F:\AI\MM\_vh_archive_2026-10-30'
New-Item -ItemType Directory -Force -Path "$arch\release_v1.1.x_zips" | Out-Null
Get-ChildItem "$root\release" -Force -File -Filter *.zip | ForEach-Object { Move-Item $_.FullName "$arch\release_v1.1.x_zips" -Force }
Get-ChildItem "$root\release" -Force | Select-Object -ExpandProperty Name
```

Expected: `videos` remains (plus any non-zip file that was there).

- [ ] **Step 4: Move the release worktree's `dist/` and `build/`**

```powershell
$wt   = 'F:\AI\MM\void-hunter\.worktrees\bloquec-67-goliath-port'
$arch = 'F:\AI\MM\_vh_archive_2026-10-30'
New-Item -ItemType Directory -Force -Path "$arch\build_cache" | Out-Null
Move-Item "$wt\dist" "$arch\dist_release_wt" -Force
if (Test-Path "$wt\build") { Move-Item "$wt\build" "$arch\build_cache\build_release_wt" -Force }
```

Expected: both gone from the worktree, present in the archive.

- [ ] **Step 5: Move the root `build/` cache and `_archive_v1.6.2/`**

```powershell
$root = 'F:\AI\MM\void-hunter'
$arch = 'F:\AI\MM\_vh_archive_2026-10-30'
if (Test-Path "$root\build") { Move-Item "$root\build" "$arch\build_cache\build_root" -Force }
if (Test-Path "$root\_archive_v1.6.2") { Move-Item "$root\_archive_v1.6.2" "$arch\archive_v1.6.2" -Force }
```

Expected: both gone from the root, present in the archive.

- [ ] **Step 6: Move the regenerable art intermediates**

```powershell
$root = 'F:\AI\MM\void-hunter'
$arch = 'F:\AI\MM\_vh_archive_2026-10-30'
New-Item -ItemType Directory -Force -Path "$arch\assets_intermediates" | Out-Null
foreach ($d in '_strips','_base','_seed','_test','_mask','gifs') {
    $p = "$root\Assets\sprites\bosses\goliath\$d"
    if (Test-Path $p) { Move-Item $p "$arch\assets_intermediates\$d" -Force }
}
Get-ChildItem "$arch\assets_intermediates" -Force | Select-Object -ExpandProperty Name
```

Expected: `_strips` and `_base` at least. These are git-ignored intermediates regenerated by `tools/redesign_bosses/`.

- [ ] **Step 7: Move the verification captures and the logs**

```powershell
$root = 'F:\AI\MM\void-hunter'
$arch = 'F:\AI\MM\_vh_archive_2026-10-30'
New-Item -ItemType Directory -Force -Path "$arch\playtest_out_logs" | Out-Null
if (Test-Path "$root\tools\playtest_out") { Move-Item "$root\tools\playtest_out" "$arch\playtest_out_logs\playtest_out" -Force }
if (Test-Path "$root\logs") { Move-Item "$root\logs" "$arch\playtest_out_logs\logs" -Force }
```

Expected: both gone from the root, present in the archive.

- [ ] **Step 8: Move the session scratch — ONLY if the other agent is not using it**

The scratch folder `_srcrefs` is shared between agents on this machine. Move it only when nothing in it was touched in the last 60 minutes.

```powershell
$scratch = 'F:\AI\MM\void-hunter\.worktrees\_srcrefs'
$arch = 'F:\AI\MM\_vh_archive_2026-10-30'
$recent = @(Get-ChildItem $scratch -Recurse -File -Force -ErrorAction SilentlyContinue |
    Where-Object { $_.LastWriteTime -gt (Get-Date).AddMinutes(-60) })
if ($recent.Count -gt 0) {
    "SKIP: $($recent.Count) files touched in the last hour -- the other agent may be using it"
} elseif (Test-Path $scratch) {
    Move-Item $scratch "$arch\srcrefs_scratch" -Force
    "moved"
} else { "nothing to move" }
```

Expected: `moved`, or `SKIP` — in which case that block stays where it is and the final size is ~200 MB higher. **Do not force this move.**

- [ ] **Step 9: Verify every move landed**

```powershell
$root = 'F:\AI\MM\void-hunter'
$arch = 'F:\AI\MM\_vh_archive_2026-10-30'
"{0:N2} GB after" -f ((Get-ChildItem $root -Recurse -File -Force | Measure-Object Length -Sum).Sum / 1GB)
"{0:N2} GB archived" -f ((Get-ChildItem $arch -Recurse -File -Force | Measure-Object Length -Sum).Sum / 1GB)
foreach ($d in 'dist_old_builds','release_v1.1.x_zips','dist_release_wt','build_cache','archive_v1.6.2','assets_intermediates','playtest_out_logs') {
    if (-not (Test-Path "$arch\$d")) { throw "MISSING ARCHIVE BLOCK: $d" }
}
"archive blocks OK"
```

Expected: `~2.3 GB after`, `~13.4 GB archived`, `archive blocks OK`.

- [ ] **Step 10: Verify the repository still works**

```powershell
$root = 'F:\AI\MM\void-hunter'
git -C $root status --short
```

Expected: **empty**. Every moved path is git-ignored, so the tracked tree cannot have changed. If `git status` is NOT empty, stop and use systematic-debugging — something tracked was moved.

- [ ] **Step 11: Verify the release worktree still works**

```powershell
$wt = 'F:\AI\MM\void-hunter\.worktrees\bloquec-67-goliath-port'
git -C $wt status --short
F:\AI\MM\void-hunter\.venv\Scripts\python.exe -m pytest "$wt\tests" --tb=no
```

Expected: empty status, `1 failed, 2886 passed, 6 skipped` (the pre-existing failure).

---

### Task 4: Consolidate the binary and move its truth anchor

**Files:**
- Modify: `tools/regen_status.py` (the `RELEASE_WT` / build row)
- Create: `tests/test_status_truth_anchors.py`

**Interfaces:**
- Consumes: the surviving `dist/void-hunter-v1.8.0.exe`.
- Produces: a `STATUS:GENERATED` block whose build row resolves to a file that exists.

- [ ] **Step 1: Write the failing test**

Create `tests/test_status_truth_anchors.py`:

```python
"""BLOQUE 75: the truth anchors of the STATUS block must resolve.

The STATUS block of CLAUDE.md is auto-generated and claims to carry, for
each metric, the command that measures it. A truth anchor that points at
a path that no longer exists is worse than no block at all: it looks
verifiable and is not.

This module reads the block and checks that the file each truth anchor
names actually exists.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _status_rows() -> list[tuple[str, str, str]]:
    """(metric, value, source) for every row of the STATUS table."""
    text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    start = text.index("STATUS:GENERATED")
    rows = []
    for line in text[start:].splitlines():
        match = re.match(r"^\| ([^|]+?) \| (.*?) \| (.*?) \|$", line)
        if match and match.group(1).strip() not in ("Métrica", "---------"):
            rows.append(
                (match.group(1).strip(), match.group(2).strip(), match.group(3).strip())
            )
        elif rows and line.startswith("---"):
            break
    return rows


def test_the_status_block_has_rows():
    """The block is present and parseable. If this fails, the block moved."""
    rows = _status_rows()
    assert rows, "the STATUS block of CLAUDE.md could not be parsed"
    metrics = {metric for metric, _, _ in rows}
    assert "Tests (tests/)" in metrics
    assert "Rama" in metrics


def test_the_build_truth_anchor_resolves():
    """The build row names a file that exists.

    This is the anchor that broke when the duplicated v1.8.0 binary was
    archived: the row pointed at the release worktree's `dist/`, and that
    copy no longer exists.
    """
    rows = dict((metric, source) for metric, _, source in _status_rows())
    source = rows["Build .exe"]
    match = re.search(r"`([^`]*void-hunter[^`]*)`", source)
    assert match, f"the build row names no file: {source!r}"
    path = match.group(1).replace("\\", "/")
    resolved = (ROOT / path).resolve()
    assert resolved.is_file(), (
        f"the build truth anchor points at {path}, which does not exist"
    )


def test_the_generator_writes_the_same_path_the_block_shows():
    """`tools/regen_status.py` and the block agree.

    The generator is what rewrites the block. If it still names the old
    path, the next regeneration silently puts the broken anchor back.
    """
    generator = (ROOT / "tools" / "regen_status.py").read_text(encoding="utf-8")
    rows = dict((metric, source) for metric, _, source in _status_rows())
    match = re.search(r"`([^`]*void-hunter[^`]*)`", rows["Build .exe"])
    assert match
    needle = Path(match.group(1).replace("\\", "/")).name
    assert needle in generator, (
        f"the generator does not mention {needle!r}: it would rewrite the "
        "build row with a different path"
    )
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `F:\AI\MM\void-hunter\.venv\Scripts\python.exe -m pytest tests\test_status_truth_anchors.py --tb=short`

Expected: FAIL on `test_the_build_truth_anchor_resolves` (the row still points at `../bloquec-67-goliath-port/dist/void-hunter.exe`, which Task 3 archived).

- [ ] **Step 3: Update the generator**

In `tools/regen_status.py`, replace the `RELEASE_WT` constant and the build row:

```python
ROOT = Path(
    os.environ.get(
        "VH_WT",
        r"F:\AI\MM\void-hunter\.worktrees\bloquec-75-sprite-migration",
    )
)
# BLOQUE 75: the release binary lives at the repository root. The copy that
# used to sit in the release worktree's dist/ was byte-identical and was
# archived; there is ONE canonical .exe now, and this is its path.
RELEASE_BRANCH = "bloquec-67-goliath-port"
BINARY_REL = "dist/void-hunter-v1.8.0.exe"
```

and the measurement:

```python
    exe = ROOT.parent.parent / BINARY_REL
    exe_mb = round(exe.stat().st_size / 1024 / 1024, 1) if exe.is_file() else 0
```

and the row:

```python
        "Build .exe": (
            f"**reconstruido** para v1.8.0 ({exe_mb} MB) en `dist/void-hunter-v1.8.0.exe` "
            "— el path congelado (`<_MEIPASS>/Assets/sprites/bosses`) verificado con "
            "el manifest y los anchors dentro del bundle; SHA256 "
            f"`{_sha256(exe)}`"
        ),
```

and add the helper next to the other helpers:

```python
def _sha256(path: Path) -> str:
    """The SHA256 of a file, or 'n/d' when it is not there."""
    if not path.is_file():
        return "n/d"
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()
```

and add `import hashlib` to the imports.

- [ ] **Step 4: Regenerate the block and run the test**

```powershell
cd F:\AI\MM\void-hunter\.worktrees\bloquec-75-sprite-migration
F:\AI\MM\void-hunter\.venv\Scripts\python.exe tools\regen_status.py
F:\AI\MM\void-hunter\.venv\Scripts\python.exe -m pytest tests\test_status_truth_anchors.py --tb=short
```

Expected: the generator reports `rows updated: 7`, and the test passes.

- [ ] **Step 5: Commit**

```bash
git add tools/regen_status.py tests/test_status_truth_anchors.py CLAUDE.md
git commit -m "fix: BLOQUE 75 - el binario v1.8.0 canonico y su truth anchor"
```

---

### Task 5: Document the cleanup

**Files:**
- Create: `docs/arch/MAINTENANCE-CLEANUP-2026-10-30.md`
- Create: `F:\AI\MM\_vh_archive_2026-10-30\MANIFEST.md`
- Modify: `.synapse`

**Interfaces:**
- Consumes: the measured before/after numbers from Tasks 1, 3 and 4.
- Produces: the record of what moved, where it went and how to bring it back.

- [ ] **Step 1: Measure the final numbers**

```powershell
$root = 'F:\AI\MM\void-hunter'
$arch = 'F:\AI\MM\_vh_archive_2026-10-30'
$dest = 'F:\AI\MM\void-hunter-baseline-v1.8.0'
"root   : {0:N2} GB" -f ((Get-ChildItem $root -Recurse -File -Force | Measure-Object Length -Sum).Sum / 1GB)
"archive: {0:N2} GB" -f ((Get-ChildItem $arch -Recurse -File -Force | Measure-Object Length -Sum).Sum / 1GB)
"baseline: {0:N1} MB / {1} archivos" -f ((Get-ChildItem $dest -Recurse -File -Force | Measure-Object Length -Sum).Sum/1MB), (Get-ChildItem $dest -Recurse -File -Force | Measure-Object).Count
Get-ChildItem $arch -Force | ForEach-Object {
    $s = if ($_.PSIsContainer) { (Get-ChildItem $_.FullName -Recurse -File -Force | Measure-Object Length -Sum).Sum } else { $_.Length }
    "{0,-26} {1,8:N1} MB" -f $_.Name, ($s/1MB)
}
```

- [ ] **Step 2: Write the repository document**

Create `docs/arch/MAINTENANCE-CLEANUP-2026-10-30.md`. It must contain, with the numbers from Step 1:

- What the repository weighed before (15.70 GB) and after, and the archive's size.
- The table of the archive blocks: name, what it was, its size, why it went.
- The baseline: where it is, how many files, how it was cut, and the four checks it passed.
- The one command that verifies it:
  `python tools\verify_clean_copy.py --tree F:\AI\MM\void-hunter-baseline-v1.8.0`
- The restore procedure, one `Move-Item` per block.
- The SHA256 of the surviving binary.
- An explicit note that the four `Assets/*.wav` are 281 MB of the tracked tree on purpose (decision D1), and that `_lp600`/`_lp8000` are generated output kept tracked by that decision.

- [ ] **Step 3: Write the archive manifest**

Create `F:\AI\MM\_vh_archive_2026-10-30\MANIFEST.md` with the same table plus the original path of every block, so the archive is self-describing even if the repository is lost.

- [ ] **Step 4: Update `.synapse`**

Set `short_term_memory.current_objective` to the state after the cleanup, `short_term_memory.last_successful_action` to what was verified, and refresh `last_verification_utc` to the UTC timestamp of the last real run. Keep `active_context_pointers` as it is — the three routes it names still resolve.

- [ ] **Step 5: Regenerate the STATUS block**

```powershell
cd F:\AI\MM\void-hunter\.worktrees\bloquec-75-sprite-migration
F:\AI\MM\void-hunter\.venv\Scripts\python.exe tools\regen_status.py
```

Expected: `rows updated: 7` and `git diff -- CLAUDE.md` shows only the metrics that genuinely moved.

- [ ] **Step 6: Commit**

```bash
git add docs/arch/MAINTENANCE-CLEANUP-2026-10-30.md .synapse CLAUDE.md
git commit -m "docs: BLOQUE 75 - registro de la limpieza de integridad y el baseline limpio"
```

---

### Task 6: Final gates

**Files:**
- No file changes. This task produces evidence.

**Interfaces:**
- Consumes: everything the previous five tasks produced.
- Produces: the proof that the cleanup did not break the project.

- [ ] **Step 1: The suite**

```powershell
cd F:\AI\MM\void-hunter\.worktrees\bloquec-75-sprite-migration
F:\AI\MM\void-hunter\.venv\Scripts\python.exe -m pytest tests/ --tb=no
```

Expected: `2 failed`? No — expected `1 failed, 2900 passed, 6 skipped`: the pre-existing `tests/test_paths.py::test_paths_no_star_shapes` plus the new tests from Tasks 2 and 4.

- [ ] **Step 2: The type checker**

```powershell
F:\AI\MM\void-hunter\.venv\Scripts\python.exe -m mypy src\anim\
```

Expected: `Success: no issues found in 6 source files`.

- [ ] **Step 3: The sprite contract guard**

```powershell
F:\AI\MM\void-hunter\.venv\Scripts\python.exe tools\sprite_pipeline\verify_contract.py goliath
```

Expected: `CONTRACT OK`, exit 0.

- [ ] **Step 4: The game boots**

```powershell
F:\AI\MM\void-hunter\.venv\Scripts\python.exe main.py --check
```

Expected: `BLOQUE 16: full game with 15 scenes, 18 waves, 4 bosses.`

- [ ] **Step 5: The structural audit**

```powershell
$env:PYTHONUTF8 = '1'
F:\AI\MM\void-hunter\.venv\Scripts\python.exe "C:\Users\Lerius\.minimax\skills\sf-sm-doctor\scripts\audit_sf_sm.py" --perfil=lite .
```

Expected: `>>> SF COMPLIANCE (lite): 7/7 <<<` and exit 0. `PYTHONUTF8=1` is required: the auditor reads the files with the system encoding and dies on the repository's Spanish text otherwise.

- [ ] **Step 6: The baseline is still uncontaminated**

```powershell
F:\AI\MM\void-hunter\.venv\Scripts\python.exe tools\verify_clean_copy.py --tree F:\AI\MM\void-hunter-baseline-v1.8.0
```

Expected: `CLEAN COPY OK`, exit 0.

- [ ] **Step 7: The tree is clean and the other agent was not touched**

```powershell
git -C F:\AI\MM\void-hunter status --short
git -C F:\AI\MM\void-hunter\.worktrees\bloquec-75-sprite-migration status --short
git -C F:\AI\MM\void-hunter\.worktrees\bloquec-75-migration-spec log --oneline -1
git -C F:\AI\MM\void-hunter worktree list
```

Expected: both statuses empty, the other agent's worktree still on its own branch, three worktrees listed.

- [ ] **Step 8: The diff review**

Run `gstack-review` against the branch base (`bloquec-67-goliath-port`) for the commits of this plan. Expected: no blocking finding. Fix what it finds before declaring the work done.

- [ ] **Step 9: The completion table**

Report, with the command that produced each number:

| Claim | Command | Value |
|---|---|---|
| Repository size | `Get-ChildItem ... -Recurse -File \| Measure-Object Length -Sum` | |
| Archive size | same, on the archive | |
| Baseline size and file count | same, on the baseline | |
| Suite | `pytest tests/ --tb=no` | |
| Types | `mypy src/anim/` | |
| Sprite contract | `verify_contract.py goliath` | |
| Game boot | `main.py --check` | |
| Structure | `audit_sf_sm.py --perfil=lite .` | |
| Baseline purity | `verify_clean_copy.py --tree ...` | |

---

## Self-Review

**1. Spec coverage.** Every section of the design doc maps to a task: the
baseline and its four checks → Task 1; the archive and its eight blocks →
Task 3; the single binary and its truth anchor → Task 4; the documentation
and the `.synapse` → Task 5; the four gates → Task 6. The "what is not
touched" list is enforced by the constraints in Task 3's steps and by
Step 7 of Task 6. The proof that a copy is uncontaminated — which the
design asks for and which no step in the design implemented — is Task 2.

**2. Placeholder scan.** No `TBD`, no `TODO`, no "similar to Task N". Every
command is spelled out with its full path. The only judgement call in
the plan is Task 3 Step 8, where the scratch folder is moved only if
nothing touched it in the last hour; that is a deliberate conditional with
a stated default (skip), not a gap.

**3. Type consistency.** `verify_clean_copy.verify(tree: Path, ref: str,
repo: Path) -> CleanCopyReport` is the same signature in the test and in
the implementation. `CleanCopyReport.ok`, `.describe()`, `.missing`,
`.extra`, `.mismatched` and `.checked` are the attributes the tests read.
`tools/regen_status.py` keeps its `main()` signature; the new helper is
`_sha256(path: Path) -> str` and is called only from the row it feeds.

**4. Risk of the plan itself.** The plan's own failure mode would be
moving something that matters. That is why Task 1 comes first and why
Task 3's steps verify each move, and why Task 3 Step 10 asserts the
tracked tree is untouched.
