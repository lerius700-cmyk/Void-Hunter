"""BLOQUE 75: the Phase 1 gate.

One command that decides whether the enemy sets are ready for Phase 2.
It runs EVERY check and reports all the failures, not just the first.

    python tools/sprite_pipeline/gate.py

Exit 0 -> PHASE 1 GATE OK. Exit 1 -> PHASE 1 GATE FAILED: <the list>.
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

ROOT = Path(__file__).resolve().parent.parent.parent
for _entry in (str(ROOT), str(ROOT / "tools")):
    if _entry in sys.path:
        sys.path.remove(_entry)
    sys.path.insert(0, _entry)

import pygame  # noqa: E402

from src.anim.manifest import load_set  # noqa: E402
from sprite_pipeline import ensure_display  # noqa: E402
from sprite_pipeline.audit import (  # noqa: E402
    FAIL_STATES,
    audit_set,
    render_anchors_toml,
)
from sprite_pipeline.sets import discover_sets, resolve_set  # noqa: E402

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

# The guards the enemy sets must pass. G13 runs them: a green gate means the
# art was not touched, the hitbox is not the canvas, the declared semantics
# are the real ones, the auditor is clean and the anchors are fresh.
GUARD_TESTS = (
    "tests/test_enemy_art_is_untouched.py",
    "tests/test_enemy_hitbox_is_not_the_canvas.py",
    "tests/test_enemy_clip_semantics.py",
    "tests/test_enemy_sets_audit_clean.py",
    "tests/test_enemy_anchors_are_fresh.py",
    "tests/test_enemy_manifest_matches_assets.py",
    "tests/test_enemy_set_discovery.py",
)


def main() -> int:
    pygame.init()
    ensure_display()

    failures: list[str] = []

    # G1: every enemy set audits clean.
    enemies_root = ROOT / "Assets" / "sprites" / "enemies"
    for name in ENEMY_SETS:
        try:
            anim_set = load_set(name, root=enemies_root)
        except (OSError, ValueError) as exc:
            failures.append(f"G1 {name}: the manifest does not load: {exc}")
            continue
        findings, _ = audit_set(anim_set)
        for finding in findings:
            if finding.state in FAIL_STATES:
                failures.append(
                    f"G1 {name}: {finding.clip}/frame_{finding.frame:02d} "
                    f"{finding.state}: {finding.detail}"
                )
            else:
                failures.append(
                    f"G1 {name}: {finding.clip}/frame_{finding.frame:02d} "
                    f"{finding.state} (WARN): {finding.detail}"
                )

    # G2 + G3: the anchors are fresh and deterministic.
    for name in ENEMY_SETS:
        try:
            anim_set = load_set(name, root=enemies_root)
        except (OSError, ValueError) as exc:
            failures.append(f"G2 {name}: the manifest does not load: {exc}")
            continue
        _, measurements = audit_set(anim_set)
        rendered = render_anchors_toml(anim_set, measurements)
        path = enemies_root / name / "anchors.toml"
        if not path.is_file():
            failures.append(f"G2 {name}: no anchors.toml")
            continue
        on_disk = path.read_text(encoding="utf-8")
        if rendered != on_disk:
            failures.append(f"G2 {name}: the anchors are stale")
        if render_anchors_toml(anim_set, measurements) != rendered:
            failures.append(f"G3 {name}: the anchors are not deterministic")

    # G5: GOLIATH is unharmed.
    goliath = ROOT / "Assets" / "sprites" / "bosses" / "goliath"
    if not (goliath / "anchors.toml").is_file():
        failures.append("G5 goliath: no anchors.toml")

    # G6: discovery finds exactly the 8 sets.
    found = {p.name for p in discover_sets(enemies_root)}
    if found != set(ENEMY_SETS):
        failures.append(f"G6: discovery found {sorted(found)}")

    # G9: the type gate. mypy must RUN and report ZERO errors.
    mypy_cmd = _mypy_command()
    if mypy_cmd is None:
        failures.append(
            "G9: mypy cannot be run -- install the dev requirements "
            "(`python -m pip install -r requirements-dev.txt`) or make `uvx` available"
        )
    else:
        proc = subprocess.run(
            [*mypy_cmd, "src/anim/"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        if proc.returncode != 0:
            failures.append(f"G9: mypy reported errors:\n{proc.stdout.strip()}")

    # G11: not one PNG changed since the last commit.
    proc = subprocess.run(
        ["git", "diff", "--stat", "HEAD", "--", "*.png"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.stdout.strip():
        failures.append(f"G11: PNG files changed:\n{proc.stdout.strip()}")

    # G13: the enemy guards are green.
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            *GUARD_TESTS,
            "-q",
            "--no-header",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=900,
    )
    if proc.returncode != 0:
        failures.append(f"G13: the enemy guards are red:\n{proc.stdout[-4000:]}")

    if failures:
        print("PHASE 1 GATE FAILED:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("PHASE 1 GATE OK")
    return 0


def _mypy_command() -> list[str] | None:
    """The command that runs mypy, or None when it cannot be run.

    `python -m mypy` when mypy is installed in the interpreter; otherwise
    `uvx mypy`, which fetches mypy into uv's cache WITHOUT touching the
    user's Python installation.

    The `uvx` branch adds `--python-executable`: uv's ephemeral environment
    does NOT have pygame installed, so mypy would report
    `import-not-found` for pygame -- and with pygame untyped, strict mode
    also reports a spurious `no-any-return` on `src/anim/measure.py`.
    `--python-executable` points mypy at the interpreter that HAS pygame
    (pygame 2.6 ships the .pyi stubs), so the check measures the CODE and
    not the environment. Nothing is installed on the user's machine: mypy
    still comes from uv's cache.
    """
    if importlib.util.find_spec("mypy") is not None:
        return [sys.executable, "-m", "mypy"]
    uvx = shutil.which("uvx")
    if uvx:
        return [uvx, "mypy", "--python-executable", sys.executable]
    return None


if __name__ == "__main__":
    raise SystemExit(main())
