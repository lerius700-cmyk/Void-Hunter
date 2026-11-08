"""Regenerate the STATUS:GENERATED block of CLAUDE.md from real truth anchors.

The block says "auto-block", and the auditor (``sf-sm-doctor``) only READS:
it has no write mode. The real generator is this script.

Every number this script writes comes from a command that the block
lists in its "Fuente (Truth Anchor)" column, so it can be re-measured at
any time instead of being edited by hand.

The scope
---------
This generator owns ELEVEN of the block's rows: the two LOC counts, the
file count, the test count, the silo count, the branch, the version, the
build, and the three disk weights.
The other rows (compliance, remote, tiles, frame counts, videos, sprite
sheets) are measured by other commands and are left alone -- the block
names the command for each one.

The VERSION row used to be one of the unowned ones, and that is how it
came to contradict its own anchor: the row said v1.8.0 and named
`git log --oneline -1` as the thing that measures it -- which is a
COMMIT SUBJECT, not a version. The row is owned here now, because this
file holds the only version in the codebase (there is no version string
anywhere in `src/`), and because a row that no generator owns is a row
that drifts.

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
from repo_budget import repo_root

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
# One source of truth for "where is the repository root": the budget
# tool already asks git, and a heuristic here would disagree with it on
# any worktree that is not under `.worktrees/`.
REPO_ROOT = repo_root(ROOT)

RELEASE_BRANCH = "bloquec-67-goliath-port"
# The interpreter that runs THIS tool: the one that is running it now.
# A hardcoded path to another tree's venv would break on every machine
# that is not that machine.
PY = sys.executable
CLAUDE = ROOT / "CLAUDE.md"

# BLOQUE 75: there is ONE canonical .exe now. The release worktree used
# to carry a byte-identical copy in its own dist/, and that copy was
# archived during the repo cleanup -- so the build row has to name the
# survivor, in the repository root, and the generator has to name it
# too. A block that lies and a generator that agrees with the lie is
# worse than either alone: the next regeneration puts the broken anchor
# back.
VERSION = "v1.9.0"
# The path of the .exe the build row names. It is DERIVED from VERSION:
# writing it out meant two places to bump, while the comment below
# claimed there was only one. Bumping VERSION alone used to leave the row
# naming the PREVIOUS release's binary -- with THAT file's SHA256 --
# under the new version's label.
BINARY_REL = f"dist/void-hunter-{VERSION}.exe"
# The parenthetical of the "Versión" row: what THIS release carries.
# It lives next to VERSION so that a bump is ONE place and not two. A
# row whose text is written by hand NEXT to the constant that measures
# it is exactly how the version drifted in the first place.
RELEASE_NOTE = "BLOQUE 75 — pipeline de sprites + motor de capas del frame"

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

    BLOQUE 76: an ERROR counts as a failure. A test that ERRORED (a
    broken fixture, an exception in a teardown) never ran its body, and
    pytest reports it as "2 passed, 1 error in 0.01s" -- a summary the
    parser used to read as "2 passed, 0 failed". The row then said the
    suite was green while a test had not run at all.
    """
    failed = re.search(r"(\d+) failed", tail)
    errors = re.search(r"(\d+) errors?", tail)
    passed = re.search(r"(\d+) passed", tail)
    skipped = re.search(r"(\d+) skipped", tail)
    failed_count = (int(failed.group(1)) if failed else 0) + (
        int(errors.group(1)) if errors else 0
    )
    return (
        failed_count,
        int(passed.group(1)) if passed else 0,
        int(skipped.group(1)) if skipped else 0,
    )


def parse_pytest_xfailed(tail: str) -> int:
    """How many tests are marked xfail (a KNOWN failure, recorded)."""
    match = re.search(r"(\d+) xfailed", tail)
    return int(match.group(1)) if match else 0


def parse_pytest_failures(output: str) -> list[str]:
    """The test ids pytest reported as FAILED or ERRORED, in order.

    BLOQUE 76: an ERRORED test is named here too. pytest lists it under
    "ERROR <id>" in the short summary; before, the id was invisible and
    the block could not say WHICH test had not run.
    """
    return re.findall(r"^(?:FAILED|ERROR) (\S+)", output, flags=re.MULTILINE)


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
    # BLOQUE 76: the folder travels as an ARGUMENT, not inside the code
    # string. Interpolating it meant a folder name could become code.
    code = (
        "import pathlib, sys; "
        "print(sum(len(p.read_text(encoding='utf-8',errors='ignore').splitlines()) "
        "for p in pathlib.Path(sys.argv[1]).rglob('*.py')))"
    )
    return run([PY, "-c", code, folder])


def pyfiles(folder: str) -> int:
    """Number of .py files under `folder`."""
    # BLOQUE 76: the same argument rule as `loc`, and the same count --
    # the PowerShell pipeline it replaces (`Get-ChildItem -Recurse
    # -Filter *.py`) counted the same files, but reached the folder
    # through a command string.
    code = "import pathlib, sys; print(sum(1 for p in pathlib.Path(sys.argv[1]).rglob('*.py')))"
    return int(run([PY, "-c", code, folder]))


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


def _bundle_entries(exe: Path) -> list[str]:
    """The entries of the frozen bundle, or an empty list.

    Reading the PyInstaller archive is the only way to know what is
    really inside the binary.
    """
    try:
        from PyInstaller.archive.readers import CArchiveReader
    except Exception:
        return []
    try:
        return list(CArchiveReader(str(exe)).toc)
    except Exception:
        return []


# The sets whose manifest AND anchors the frozen bundle has to carry.
# BLOQUE 75 Phase 2: the enemy manifests are LOAD-BEARING at runtime --
# the runtime reads them every frame to draw the enemies. Before Phase 2
# only GOLIATH's two files were checked, so a bundle with the boss's
# manifest and none of the enemies' would have passed, and the enemies
# would have fallen back silently.
BUNDLED_SETS = (
    "Assets/sprites/bosses/goliath",
    "Assets/sprites/enemies/cruiser",
    "Assets/sprites/enemies/drone",
    "Assets/sprites/enemies/heavy",
    "Assets/sprites/enemies/kamikaze",
    "Assets/sprites/enemies/mine_asteroid",
    "Assets/sprites/enemies/scout",
    "Assets/sprites/enemies/sniper",
    "Assets/sprites/enemies/turret",
)


def frozen_assets_verified(entries: list[str]) -> bool:
    """Whether the bundle carries the manifest AND the anchors of every set.

    Pure on purpose: the reading of the bundle needs PyInstaller and a real
    .exe, and the DECISION does not.
    """
    normalised = {entry.replace("\\", "/") for entry in entries}
    for set_dir in BUNDLED_SETS:
        for name in ("manifest.toml", "anchors.toml"):
            wanted = f"{set_dir}/{name}"
            if not any(entry.endswith(wanted) for entry in normalised):
                return False
    return True


def _frozen_assets_verified(exe: Path) -> bool:
    """Whether the bundle really carries the nine sets.

    The row used to claim this without checking. A claim the generator
    does not verify is exactly the kind of lie this tool exists to
    prevent: the block says "verificado con los 9 sets ... manifest y
    anchors dentro del bundle" and nothing had ever looked.
    """
    return frozen_assets_verified(_bundle_entries(exe))


def _build_row(exe: Path, exe_mb: float) -> str:
    """The build row, honest about what is actually true.

    The artifact is a build output: it is gitignored, and a machine
    that has not built it does not have it. Claiming "reconstruido" for
    a file that is not there would be a lie the block tells on every
    fresh checkout -- and so would claiming that the frozen path was
    verified when nothing checked.
    """
    if not exe.is_file():
        return (
            f"**no está en esta máquina** — el build de {VERSION} se reconstruye "
            f"con PyInstaller y queda en `{BINARY_REL}`"
        )
    if _frozen_assets_verified(exe):
        frozen = (
            "— el path congelado (`<_MEIPASS>/Assets/sprites`) verificado "
            "con los 9 sets (GOLIATH + 8 enemigos), manifest y anchors "
            "dentro del bundle"
        )
    else:
        frozen = (
            "— el path congelado NO se pudo verificar: el bundle no se pudo leer "
            "o no contiene los 9 sets (manifest + anchors)"
        )
    return (
        f"**reconstruido** para {VERSION} ({exe_mb} MB) en `{BINARY_REL}` "
        f"{frozen}; SHA256 `{_sha256(exe)}`"
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
    xfailed = parse_pytest_xfailed(tail)
    # The xfailed tests ARE part of the suite: the row's TEXT names them
    # ("+ N xfail (fallo conocido)"), so the total has to count them too.
    # Without this the parts of the row did not add up to its own total
    # -- 3.123 + 1 + 6 is 3.130, and the row used to say 3.129.
    total = failed + passed + skipped + xfailed
    if total == 0:
        print(f"could not read the pytest summary: {tail}")
        return 1
    failure_ids = parse_pytest_failures(output)
    unknown = [f for f in failure_ids if f not in KNOWN_PREEXISTING_FAILURES]

    print(f"src LOC={src_loc} files={src_files} | tests LOC={tests_loc}")
    print(
        f"suite: {passed} pass / {failed} fail / {skipped} skipped "
        f"/ {xfailed} xfailed ({total})"
    )
    print(f"silos={n_silos} exe={exe_mb}MB branch={branch}")
    if failure_ids:
        print(f"failing: {', '.join(failure_ids)}")

    # The label says whether the failures are the KNOWN ones. A number
    # alone cannot tell a known failure from a new one, so the names are
    # what the label is built from.
    if failed == 0:
        fail_label = "0 fail"
        if xfailed:
            fail_label += f" + {xfailed} xfail (fallo conocido)"
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
        # The version is a CONSTANT of this file, so the row is written
        # from that constant. The row used to be written by hand and it
        # contradicted its own anchor: it said v1.8.0 and named
        # `git log --oneline -1`, which measures a COMMIT SUBJECT.
        "Versión": f"{VERSION} ({RELEASE_NOTE})",
        "Rama": branch,
        "Build .exe": _build_row(exe, exe_mb),
    }

    # The SOURCE column of a row is usually the command that measures the
    # value, and it is preserved from the block. When the thing being
    # measured MOVES, the source moves with it -- so the generator owns
    # both columns for the rows whose subject moved.
    sources = {
        # RELATIVE to the repository root: an absolute path names one
        # machine and resolves nowhere else (the CI included).
        "Build .exe": f"`Get-Item {BINARY_REL}` (raiz del repo)",
        "Peso del arbol trackeado": "`python tools/repo_budget.py`",
        "Salida de build (dist/)": "`python tools/repo_budget.py`",
        "Historia (.git/)": "`python tools/repo_budget.py`",
        # The anchor of the version has to MEASURE the version. It used
        # to name `git log --oneline -1`, which measures a commit
        # subject -- and the row it was supposed to back said v1.8.0
        # while the commit it named said v1.9.0. This command imports
        # the constant the row is written from, so the row and its
        # anchor cannot disagree.
        "Versión": (
            "`python -c \"import sys; sys.path.insert(0,'tools'); "
            "from regen_status import VERSION; print(VERSION)\"`"
        ),
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
