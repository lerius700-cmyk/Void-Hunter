"""BLOQUE 75: the Phase 1 gate.

One command that decides whether the enemy sets are ready for Phase 2.
It runs EVERY check and reports all the failures, not just the first.

    python tools/sprite_pipeline/gate.py
    python tools/sprite_pipeline/gate.py --base 773cf08

Exit 0 -> PHASE 1 GATE OK. Exit 1 -> PHASE 1 GATE FAILED: <the list>.

The gate measures the PHASE RANGE (base..HEAD) and NOT ONLY the working
tree: a PNG committed INSIDE the phase is invisible to `git diff HEAD`,
and the phase's own promise is that not one PNG byte changed.
"""
from __future__ import annotations

import argparse
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
from sprite_pipeline.sets import discover_sets  # noqa: E402
from sprite_pipeline.verify_contract import verify as verify_set_contract  # noqa: E402

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

# The base commit of Phase 1: the HEAD of the base branch when the phase
# started, already merged into this branch. The gate measures the RANGE
# base..HEAD, because the phase's promise is about the PHASE and not only
# about the working tree: a PNG committed inside the phase is exactly the
# failure the gate exists to catch.
PHASE_1_BASE = "773cf08"

# The guards the enemy sets must pass. G13 runs them: a green gate means the
# art was not touched, the hitbox is not the canvas, the declared semantics
# are the real ones, the auditor is clean and the anchors are fresh.
#
# The last four guard the NEW src/anim behaviour this phase added: the
# manifest's new fields, the bidirectional COLAPSADO rule, the margin the
# auditor and the repair SHARE, and the auditor's survival on a set with no
# features to detect. G1 catches most distinct/cut_margin regressions
# indirectly, but it cannot catch a margin that is always 0: that case makes
# the enemy audit CLEANER, not dirtier.
GUARD_TESTS = (
    "tests/test_enemy_art_is_untouched.py",
    "tests/test_enemy_hitbox_is_not_the_canvas.py",
    "tests/test_enemy_clip_semantics.py",
    "tests/test_enemy_sets_audit_clean.py",
    "tests/test_enemy_anchors_are_fresh.py",
    "tests/test_enemy_manifest_matches_assets.py",
    "tests/test_enemy_set_discovery.py",
    "tests/test_anim_manifest_new_fields.py",
    "tests/test_distinct_rule.py",
    "tests/test_effective_cut_margin.py",
    "tests/test_audit_runs_on_a_featureless_set.py",
)

# The budget of every subprocess the gate spawns. A subprocess that does not
# finish inside its budget is a GATE FAILURE, not a crash.
GIT_TIMEOUT_S = 120
MYPY_TIMEOUT_S = 300
GUARDS_TIMEOUT_S = 900

# The exit code the gate synthesises for a subprocess that did not finish
# inside its budget. It is the conventional "timeout" code and it lets the
# callers tell a HANG apart from a command that ran and failed.
TIMEOUT_EXIT = 124


def _run(cmd: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    """Run a command with a hard timeout, in the repository.

    A `subprocess.TimeoutExpired` escaping as a traceback would break the
    gate's own contract: the gate must print "PHASE 1 GATE FAILED:" and
    list what went wrong EVEN WHEN what went wrong is a hang. A timeout
    is reported as a normal failure instead.
    """
    try:
        return subprocess.run(
            cmd,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=TIMEOUT_EXIT,
            stdout="",
            stderr=f"timed out after {timeout}s",
        )


def _git(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a git command in the repository, with the gate's git budget."""
    return _run(["git", *args], GIT_TIMEOUT_S)


def _describe(proc: subprocess.CompletedProcess[str]) -> str:
    """What the command said, in one chunk: its output, or why it had none."""
    if proc.returncode == TIMEOUT_EXIT:
        return proc.stderr.strip() or "timed out"
    return proc.stdout.strip() or proc.stderr.strip() or "(no output)"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="The BLOQUE 75 Phase 1 gate: every check, every failure."
    )
    parser.add_argument(
        "--base",
        default=PHASE_1_BASE,
        help="the base commit of Phase 1 (the range the gate measures)",
    )
    args = parser.parse_args(argv)
    base = args.base

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
        # G3: the anchors are deterministic. The property that matters is
        # that TWO INDEPENDENT audits produce the same text. Rendering the
        # SAME measurements twice could only fail if the renderer itself
        # were nondeterministic -- and the measurement is the thing that can
        # actually drift.
        try:
            _, second_measurements = audit_set(anim_set)
        except Exception as exc:  # noqa: BLE001 - the message is the point
            failures.append(
                f"G3 {name}: the set could not be audited a second time: {exc}"
            )
            continue
        if render_anchors_toml(anim_set, second_measurements) != rendered:
            failures.append(f"G3 {name}: the anchors are not deterministic")

    # G5: GOLIATH is unharmed. TWO halves:
    #
    #   1. its assets did not change inside the phase -- a diff over the
    #      PHASE RANGE, not over the working tree; and
    #   2. the auditor still holds it to its CONTRACT. This phase changed
    #      the code path that REPAIRS GOLIATH (repair.py takes its margin
    #      from effective_cut_margin), so a regression there could rewrite
    #      GOLIATH's PNGs while this gate stayed green.
    #
    # The contract is NOT re-invented here: verify_contract.py already owns
    # it, so the gate calls that module's own verification entry point.
    goliath_dir = ROOT / "Assets" / "sprites" / "bosses" / "goliath"
    for required in ("manifest.toml", "anchors.toml"):
        if not (goliath_dir / required).is_file():
            failures.append(f"G5 goliath: no {required}")

    bosses = _git(
        ["diff", "--stat", f"{base}..HEAD", "--", "Assets/sprites/bosses/"]
    )
    if bosses.returncode != 0:
        failures.append(
            f"G5 goliath: the git command failed (exit {bosses.returncode}): "
            f"{_describe(bosses)}"
        )
    elif bosses.stdout.strip():
        failures.append(
            f"G5 goliath: the boss assets changed inside the phase "
            f"({base}..HEAD):\n{bosses.stdout.strip()}"
        )

    goliath_failures, _report = verify_set_contract("goliath", None)
    for line in goliath_failures:
        failures.append(f"G5 goliath: {line}")

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
        proc = _run([*mypy_cmd, "src/anim/"], MYPY_TIMEOUT_S)
        if proc.returncode != 0:
            failures.append(f"G9: mypy reported errors:\n{_describe(proc)}")

    # G11: not one PNG changed -- neither inside the phase nor in the
    # working tree. The two are SEPARATE checks and both are reported:
    #
    #   * the RANGE check is the one that matters for the phase's promise
    #     (a PNG committed inside the phase is invisible to `git diff HEAD`);
    #   * the WORKING TREE check catches the PNG that was edited and not
    #     committed yet.
    base_check = _git(["rev-parse", "--verify", "--quiet", f"{base}^{{commit}}"])
    if base_check.returncode != 0:
        failures.append(
            f"G11: the base commit {base!r} does not exist in this repository "
            f"-- the phase range cannot be measured"
        )

    png_range = _git(["diff", "--stat", f"{base}..HEAD", "--", "*.png"])
    if png_range.returncode != 0:
        failures.append(
            f"G11: the git command failed (exit {png_range.returncode}): "
            f"{_describe(png_range)}"
        )
    elif png_range.stdout.strip():
        failures.append(
            f"G11: PNG files changed inside the phase ({base}..HEAD):\n"
            f"{png_range.stdout.strip()}"
        )

    png_tree = _git(["diff", "--stat", "HEAD", "--", "*.png"])
    if png_tree.returncode != 0:
        failures.append(
            f"G11: the git command failed (exit {png_tree.returncode}): "
            f"{_describe(png_tree)}"
        )
    elif png_tree.stdout.strip():
        failures.append(
            f"G11: PNG files changed in the working tree:\n{png_tree.stdout.strip()}"
        )

    # G13: the enemy guards are green.
    proc = _run(
        [
            sys.executable,
            "-m",
            "pytest",
            *GUARD_TESTS,
            "-q",
            "--no-header",
        ],
        GUARDS_TIMEOUT_S,
    )
    if proc.returncode != 0:
        detail = _describe(proc)
        failures.append(f"G13: the enemy guards are red:\n{detail[-4000:]}")

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
