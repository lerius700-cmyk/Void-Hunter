"""BLOQUE 75: not one PNG byte may change.

The repair writes PNGs for CORTADO and LADO_EQUIVOCADO. With
`cut_margin = 0` and no sided feature declared, neither can fire on an
enemy set -- so the repair has nothing to write. This test proves it on
every run, on a COPY: the repository is never written to.
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from sprite_pipeline.sets import discover_sets

ENEMY_SETS = (
    "scout",
    "cruiser",
    "drone",
    "heavy",
    "kamikaze",
    "sniper",
    "turret",
    "mine_asteroid",
)

# The pipeline is an offline tool: it has to finish. A hung run would eat
# CI's whole timeout budget with no diagnostic. The house pattern is
# tools/smoke.py's `_run(..., timeout=120)`.
PIPELINE_TIMEOUT_S = 120


def _md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def _png_digests(root: Path) -> dict[str, str]:
    return {
        str(p.relative_to(root)): _md5(p)
        for p in sorted(root.rglob("*.png"))
    }


@pytest.mark.parametrize("name", ENEMY_SETS)
def test_the_fix_run_changes_no_png(tmp_path: Path, name: str) -> None:
    enemies_root = ROOT / "Assets" / "sprites" / "enemies"
    copy_root = tmp_path / "sets"
    copy_root.mkdir()
    shutil.copytree(enemies_root / name, copy_root / name)

    before = _png_digests(copy_root)
    assert before, "the set has no PNGs to protect"

    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "sprite_pipeline" / "run.py"),
            name,
            "--root",
            str(copy_root),
            "--fix",
        ],
        capture_output=True,
        cwd=str(ROOT),
        timeout=PIPELINE_TIMEOUT_S,
    )
    # The guard has TWO halves: the --fix run HAPPENED, and it changed no
    # PNG. Only the second was checked, and without this a pipeline that
    # crashed (or never ran) would leave the PNGs untouched and the test
    # would pass GREEN on nothing. `run.py` exits 1 when the audit still
    # has a FAIL and 2 when the manifest does not parse, so the exit code
    # is the verdict; the stderr tells a crash apart from a finding.
    assert proc.returncode == 0, (
        f"{name}: the --fix run failed (exit {proc.returncode})\n"
        f"--- stderr ---\n{proc.stderr.decode('utf-8', 'replace')}"
        f"--- stdout ---\n{proc.stdout.decode('utf-8', 'replace')}"
    )
    after = _png_digests(copy_root)
    assert after == before, f"{name}: the --fix run rewrote a PNG"


def test_the_repository_ships_exactly_the_eight_enemy_sets() -> None:
    """The shipped tree is not a scratch pad: it holds exactly 8 sets."""
    enemies_root = ROOT / "Assets" / "sprites" / "enemies"
    found = {p.name for p in discover_sets(enemies_root)}
    assert found == set(ENEMY_SETS)
