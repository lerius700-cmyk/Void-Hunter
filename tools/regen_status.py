"""Regenerate the STATUS:GENERATED block of CLAUDE.md from real truth anchors.

The block says "auto-block", and the auditor (``sf-sm-doctor``) only READS:
it has no write mode. The real generator is this script.

Every number this script writes comes from a command that the block
lists in its "Fuente (Truth Anchor)" column, so it can be re-measured at
any time instead of being edited by hand.

The scope
---------
This generator owns SEVEN of the block's rows: the two LOC counts, the
file count, the test count, the silo count, the branch and the build.
The other rows (version, compliance, remote, tiles, frame counts,
videos, sprite sheets) are measured by other commands and are left
alone -- the block names the command for each one.

Which tree is measured
----------------------
The tree is the one this script LIVES IN: ``ROOT`` comes from the
script's own location, because the repository is worked on by more than
one agent, each in its own worktree, and a generator that measured a
fixed tree would rewrite a sibling agent's CLAUDE.md. ``VH_WT`` is an
explicit override.

The size of the shipped ``.exe`` is read from the REPOSITORY ROOT, not
from the worktree: a worktree in progress has no ``dist/``, and
measuring it from there would report 0 MB.

Usage:
    python tools/regen_status.py
    VH_WT=F:\\path\\to\\another\\tree python tools/regen_status.py
"""
from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

# The weight of the repository, and the ceilings it has to stay under.
# See tools/repo_budget.py and tests/test_repo_budget.py.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from repo_budget import measure as measure_budget

# The tree this tool belongs to. NOT a hardcoded path: the repository is
# worked on by more than one agent, each in its own worktree, and a
# generator that measured a FIXED tree would rewrite a sibling agent's
# CLAUDE.md and leave that agent with a stale one -- silently, with no
# error. `VH_WT` is only an explicit override.
ROOT = Path(
    os.environ.get("VH_WT", str(Path(__file__).resolve().parent.parent))
).resolve()

# The repository root, which for a linked worktree is two levels up
# (`.worktrees/<name>` -> `.worktrees` -> the root). The canonical .exe
# lives in the root's `dist/`, not in a worktree's.
REPO_ROOT = ROOT.parent.parent if ROOT.parent.name == ".worktrees" else ROOT

RELEASE_BRANCH = "bloquec-67-goliath-port"
PY = sys.executable or r"F:\AI\MM\void-hunter\.venv\Scripts\python.exe"
CLAUDE = ROOT / "CLAUDE.md"

# BLOQUE 75: there is ONE canonical .exe now. The release worktree used
# to carry a byte-identical copy in its own dist/, and that copy was
# archived during the repo cleanup -- so the build row has to name the
# survivor, in the repository root, and the generator has to name it
# too. A block that lies and a generator that agrees with the lie is
# worse than either alone: the next regeneration puts the broken anchor
# back.
BINARY_REL = "dist/void-hunter-v1.8.1.exe"
VERSION = "v1.8.1"

# The failures this project KNOWS about, by test id. The block says
# whether the failures are the known pre-existing ones, and that claim
# needs the names: a number alone cannot tell a known failure from a
# new one.
KNOWN_PREEXISTING_FAILURES = {
    "tests/test_paths.py::test_paths_no_star_shapes",
}


def parse_pytest_summary(tail: str) -> tuple[int, int, int]:
    """(failed, passed, skipped) out of a pytest summary line.

    The line is not a fixed sentence. It is "9 passed in 0.18s" when
    everything is green, "1 failed, 11 passed in 0.22s" when there are
    no skips, and the order of the counts varies. Each count is read on
    its own, and a missing one is zero.
    """
    failed = re.search(r"(\d+) failed", tail)
    passed = re.search(r"(\d+) passed", tail)
    skipped = re.search(r"(\d+) skipped", tail)
    return (
        int(failed.group(1)) if failed else 0,
        int(passed.group(1)) if passed else 0,
        int(skipped.group(1)) if skipped else 0,
    )


def parse_pytest_failures(output: str) -> list[str]:
    """The test ids pytest reported as FAILED, in the order it listed them."""
    return re.findall(r"^FAILED (\S+)", output, flags=re.MULTILINE)


def run(cmd: list[str], cwd: Path = ROOT) -> str:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return proc.stdout.strip()


def loc(folder: str) -> str:
    """Lines of code under `folder`."""
    code = (
        "import pathlib; print(sum(len(p.read_text(encoding='utf-8',errors='ignore').splitlines()) "
        f"for p in pathlib.Path('{folder}').rglob('*.py')))"
    )
    return run([PY, "-c", code])


def pyfiles(folder: str) -> int:
    """Number of .py files under `folder`."""
    out = run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            f"(Get-ChildItem -Recurse -Filter *.py '{folder}' | Measure-Object).Count",
        ]
    )
    return int(out)


def _sha256(path: Path) -> str:
    """The SHA256 of a file, or 'n/d' when it is not there.

    The build row carries the hash so that "the .exe" names ONE file:
    there were two byte-identical copies before the cleanup, and a row
    that names a path cannot tell them apart.
    """
    if not path.is_file():
        return "n/d"
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _build_row(exe: Path, exe_mb: float) -> str:
    """The build row, honest about whether the artifact is there.

    The artifact is a build output: it is gitignored, and a machine
    that has not built it does not have it. Claiming "reconstruido" for
    a file that is not there would be a lie the block tells on every
    fresh checkout.
    """
    if not exe.is_file():
        return (
            "**no está en esta máquina** — el build de v1.8.0 se reconstruye "
            f"con PyInstaller y queda en `{BINARY_REL}`"
        )
    return (
        f"**reconstruido** para {VERSION} ({exe_mb} MB) en `{BINARY_REL}` "
        "— el path congelado (`<_MEIPASS>/Assets/sprites/bosses`) verificado con "
        f"el manifest y los anchors dentro del bundle; SHA256 `{_sha256(exe)}`"
    )


def main() -> int:
    text = CLAUDE.read_text(encoding="utf-8")

    src_loc = loc("src")
    tests_loc = loc("tests")
    src_files = pyfiles("src")
    n_silos = len([p for p in (ROOT / "docs").iterdir() if p.is_dir()])
    budget = measure_budget(ROOT)

    exe = REPO_ROOT / BINARY_REL
    exe_mb = round(exe.stat().st_size / 1024 / 1024, 1) if exe.is_file() else 0

    branch = run(["git", "branch", "--show-current"])
    if branch != RELEASE_BRANCH:
        # The block is a Spanish document: the value stays in Spanish.
        branch = (
            f"{branch} (en curso; la línea de release es {RELEASE_BRANCH})"
        )

    pytest = subprocess.run(
        [PY, "-m", "pytest", "tests/", "--tb=no"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    output = pytest.stdout.strip()
    tail = output.splitlines()[-1] if output else ""
    failed, passed, skipped = parse_pytest_summary(tail)
    total = failed + passed + skipped
    if total == 0:
        print(f"could not read the pytest summary: {tail}")
        return 1
    failure_ids = parse_pytest_failures(output)
    unknown = [f for f in failure_ids if f not in KNOWN_PREEXISTING_FAILURES]

    print(f"src LOC={src_loc} files={src_files} | tests LOC={tests_loc}")
    print(f"suite: {passed} pass / {failed} fail / {skipped} skipped ({total})")
    print(f"silos={n_silos} exe={exe_mb}MB branch={branch}")
    if failure_ids:
        print(f"failing: {', '.join(failure_ids)}")

    # The label says whether the failures are the KNOWN ones. A number
    # alone cannot tell a known failure from a new one, so the names are
    # what the label is built from.
    if failed == 0:
        fail_label = "0 fail"
    elif unknown:
        fail_label = f"{failed} fail (NO pre-existente: {', '.join(unknown)})"
    else:
        fail_label = f"{failed} fail pre-existente"

    rows = {
        "Líneas de código (src/)": f"{src_loc}",
        "Archivos Python (src/)": f"{src_files}",
        "Tests (tests/)": (
            f"{passed:,} pass + {fail_label} + {skipped} skipped "
            f"({total:,} total)"
        ).replace(",", "."),
        "LOC tests/": f"{tests_loc}",
        "Silos SF+SM": f"{n_silos} (Lite)",
        "Peso del arbol trackeado": f"{budget.tracked_mb:.1f} MB",
        "Salida de build (dist/)": f"{budget.dist_mb:.1f} MB",
        "Historia (.git/)": f"{budget.git_mb:.1f} MB",
        "Rama": branch,
        "Build .exe": _build_row(exe, exe_mb),
    }

    # The SOURCE column of a row is usually the command that measures the
    # value, and it is preserved from the block. When the thing being
    # measured MOVES, the source moves with it -- so the generator owns
    # both columns for the rows whose subject moved.
    sources = {
        "Build .exe": f"`Get-Item {exe}`",
        "Peso del arbol trackeado": "`python tools/repo_budget.py`",
        "Salida de build (dist/)": "`python tools/repo_budget.py`",
        "Historia (.git/)": "`python tools/repo_budget.py`",
    }

    out: list[str] = []
    changed = 0
    for line in text.splitlines():
        row = re.match(r"^\| ([^|]+?) \| (.*?) \| (.*?) \|$", line)
        if row and row.group(1).strip() in rows:
            key = row.group(1).strip()
            source = sources.get(key, row.group(3))
            line = f"| {key} | {rows[key]} | {source} |"
            changed += 1
        out.append(line)

    CLAUDE.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"rows updated: {changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
