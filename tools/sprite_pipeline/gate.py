"""BLOQUE 75: the gate of the enemy pipeline.

One command that decides whether a phase of the pipeline is done. It runs
EVERY check and reports all the failures, not just the first.

    python tools/sprite_pipeline/gate.py
    python tools/sprite_pipeline/gate.py --base 773cf08
    python tools/sprite_pipeline/gate.py --phase 2
    python tools/sprite_pipeline/gate.py --phase 2 --base e619527

Exit 0 -> PHASE <n> GATE OK. Exit 1 -> PHASE <n> GATE FAILED: <the list>.

The base commit of the phase comes from --base, else from the
PHASE<n>_BASE environment variable, else from the PHASE_<n>_BASE constant
in this file.

The gate measures the PHASE RANGE (base..HEAD) and NOT ONLY the working
tree: a PNG committed INSIDE the phase is invisible to `git diff HEAD`,
and the phase's own promise is that not one PNG byte changed.

PHASE 1 (the default, so a bare `gate.py` keeps meaning Phase 1) guards
the ENEMY SETS: the audit, the anchors, the discovery, the type gate and
the art. PHASE 2 guards the LAYERED RENDERING ENGINE: the golden frames,
the reproducible capture, the type gate of src/render/ and src/anim/, the
pinned layer order and the art.

A SKIPPED test is not a pass: the checks that run pytest read its junit
XML and require skipped == 0, because `pytest -q` exits 0 when every
case was skipped.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
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
#
# It can be pointed elsewhere WITHOUT editing this file: the PHASE1_BASE
# environment variable, or the --base argument. See resolve_base.
PHASE_1_BASE = "773cf08"

# The base commit of Phase 2: the HEAD of the release line when Phase 2
# started -- Phase 1 was already merged there, so the Phase 2 range
# (e619527..HEAD) holds ONLY the work of this phase.
#
# The range holds the six golden frames, which are PROOF FIXTURES and not
# art: P2-G5 excludes `tools/golden/` from its range half, exactly as the
# Phase 1 gate's G11 already does.
#
# It can be pointed elsewhere WITHOUT editing this file: the PHASE2_BASE
# environment variable, or the --base argument. See resolve_base.
PHASE_2_BASE = "e619527"

# G5's RANGE diff must not report the GENERATED measurement: the anchors
# are produced by the auditor FROM the art, and Phase 2 changed their
# HEADER (the header used to name a test file that only protected
# GOLIATH). A generated file is validated by FRESHNESS -- G5's second
# half, verify_contract -> anchors_fresh -- not by "did it change?".
# The manifest and the PNGs stay in the range: those are the SPEC and
# the ART, and the promise is about them.
#
# The exclusion is LITERAL, not a glob: only GOLIATH's freshness is
# checked by the gate's second half, so excluding the anchors of a boss
# that does not exist yet would open a hole with nothing behind it.
GOLIATH_ASSETS_PATHSPEC = (
    "Assets/sprites/bosses/",
    ":!Assets/sprites/bosses/goliath/anchors.toml",
)

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

# How many cases those guards are. The gate reads the junit XML and
# requires EXACTLY this many, with zero failures, zero errors and ZERO
# skips -- like its Phase 2 siblings (P2-G1, P2-G4) already do.
#
# BLOQUE 76: G13 used to be validated by the EXIT CODE alone. `pytest`
# exits 0 when every case was SKIPPED, so a guard that stopped running
# (a `pytestmark = pytest.mark.skipif(True, ...)` left behind, a missing
# file, an import that swallows) left the gate green with the art check
# never executed. A skipped test is not a pass -- the gate's own docstring
# says so, and now it is enforced.
#
# The number is a PROMISE, not a snapshot: adding a case to a guard means
# updating it here, and forgetting to update it makes the gate red with a
# message that says exactly what happened.
GUARD_TEST_CASES = 84

# The budget of every subprocess the gate spawns. A subprocess that does not
# finish inside its budget is a GATE FAILURE, not a crash.
#
# The budgets are sized so that the WHOLE gate fits inside the CI job's
# budget EVEN WHEN EVERY subprocess hangs. That way the symptom a CI reader
# sees is the gate's OWN documented failure -- "G13: the enemy guards are
# red: timed out after 300s" -- and not the job's timeout with no
# diagnosis at all.
#
# The arithmetic, as of BLOQUE 76 (the job's clock is 45 minutes = 2700 s):
#
#   Phase 1   4 git x 60 s + mypy 300 s + guards 300 s   =  840 s
#   Phase 2   3 git x 60 s + 4 x 300 s                    = 1380 s
#   runner    2 git x 60 s (the merge-base checks)        =  120 s
#                                                        --------
#   worst case                                           = 2340 s  (39 min)
#
# 2340 s < 2700 s: the gate's own diagnosis ALWAYS lands before the job's
# wall clock. When the sum was 2340 s against a 1500 s job, a hang could
# still take the job down with no diagnosis -- the exact outcome these
# budgets exist to prevent.
#
# A git call that takes a minute is hung (the healthy ones take
# milliseconds), and the guards run in ~3 s (the art guard alone is 8 cases
# with a 60 s budget each), so 300 s is a generous hang guard.
GIT_TIMEOUT_S = 60
MYPY_TIMEOUT_S = 300
GUARDS_TIMEOUT_S = 300

# The budget of the Phase 2 capture. The harness builds a scene and ticks
# it 180..420 times per frame, and `--check` captures EVERY frame TWICE,
# so this is the most expensive thing the gate does.
GOLDEN_TIMEOUT_S = 300

# ---------------------------------------------------------------------------
# BLOQUE 75 Fase 2: what the Phase 2 gate checks.
#
# P2-G1: the golden frames are pixel-identical to the committed ones. The
# proof is ONE parametrized test -- six cases, one per frame -- and it
# SKIPS a case when its golden is missing. `pytest -q` exits 0 when every
# case was skipped, so the gate reads the junit XML and requires
# skipped == 0: a SKIPPED test is not a pass.
GOLDEN_TEST = (
    "tests/test_layer_stack_renders_identical_frames.py"
    "::test_the_frame_is_pixel_identical"
)
GOLDEN_TEST_CASES = 6

# P2-G4: the layer order is DATA, not code, and the order is pinned here.
LAYER_ORDER_TEST = "tests/test_layer_stack_order.py"
LAYER_ORDER_TEST_CASES = 3

# The six frames the proof needs. P2-G2 must see EVERY one of them in the
# harness' own "GOLDENS MATCH:" line: an exit code alone would not say
# WHICH frames were compared.
GOLDEN_FRAME_NAMES = ("boss", "enemies", "firing", "hud", "mine_open", "shake")

# The reproducible capture harness.
GOLDEN_HARNESS = "tools/capture/layerstack_frames.py"

# The type gates of this phase: `src/anim/` (the compositor) and
# `src/render/` (the layer stack). `mypy src/` as a whole is NOT clean
# (the pre-existing errors of src/ui/ and src/core/ are not this phase's
# business), so the gate names the two directories it owns.
MYPY_TARGETS = ("src/render/", "src/anim/")

# The exit code the gate synthesises for a subprocess that did not finish
# inside its budget. It is the conventional "timeout" code and it lets the
# callers tell a HANG apart from a command that ran and failed.
TIMEOUT_EXIT = 124


def _run(
    cmd: list[str],
    timeout: int,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a command with a hard timeout, in the repository.

    A `subprocess.TimeoutExpired` escaping as a traceback would break the
    gate's own contract: the gate must print "PHASE 1 GATE FAILED:" and
    list what went wrong EVEN WHEN what went wrong is a hang. A timeout
    is reported as a normal failure instead.

    `cwd` defaults to the repository root; the tests point it at a
    temporary repository so they can exercise the gate's own commands.
    """
    try:
        return subprocess.run(
            cmd,
            cwd=str(ROOT if cwd is None else cwd),
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


def _git(
    args: list[str],
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a git command in the repository, with the gate's git budget."""
    return _run(["git", *args], GIT_TIMEOUT_S, cwd=cwd)


def _range_commit_count(base: str, repo: Path | None = None) -> int | None:
    """How many commits the phase range holds, or None if git cannot say.

    The range is the gate's promise: "not one PNG byte changed inside the
    phase". A range with ZERO commits measures nothing, so the gate would
    report OK while the promise was never checked -- so the count is read
    and the empty range is a failure.

    None means git could not answer (an unresolvable base, a shallow
    clone). That is NOT an empty range: the phase reports an unresolvable
    base itself, with a better message than this one could give.
    """
    proc = _git(["rev-list", "--count", f"{base}..HEAD"], cwd=repo)
    if proc.returncode != 0:
        return None
    try:
        return int(proc.stdout.strip())
    except ValueError:
        return None


def _goliath_assets_diff(
    base: str,
    repo: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """The stat of GOLIATH's assets that changed inside the phase range.

    The SAME command, with the SAME pathspec, that G5's range half runs
    -- in `repo`, which is the gate's own root unless a caller says
    otherwise. The test calls it with a temporary repository, so it
    exercises the gate's OWN pathspec instead of a copy of it.
    """
    return _git(
        ["diff", "--stat", f"{base}..HEAD", "--", *GOLIATH_ASSETS_PATHSPEC],
        cwd=repo,
    )


def _describe(proc: subprocess.CompletedProcess[str]) -> str:
    """What the command said, in one chunk: its output, or why it had none."""
    if proc.returncode == TIMEOUT_EXIT:
        return proc.stderr.strip() or "timed out"
    return proc.stdout.strip() or proc.stderr.strip() or "(no output)"


def _phase_base(phase: int) -> str:
    """The base commit constant of the phase."""
    if phase == 2:
        return PHASE_2_BASE
    return PHASE_1_BASE


def resolve_base(argument: str | None, phase: int = 1) -> str:
    """The commit the phase range is measured from.

    The precedence is, from the strongest to the weakest:

      1. the `--base` argument -- an explicit request from the caller;
      2. the PHASE<n>_BASE environment variable -- lets a checkout that
         legitimately lacks the constant's commit run the gate without
         editing the code (a CI job can point the gate at its own base);
      3. the PHASE_<n>_BASE constant in this file.

    The argument wins over the environment variable so the gate can be
    pointed at another base -- or at a deliberately wrong one -- from the
    command line.
    """
    if argument:
        return argument
    return os.environ.get(f"PHASE{phase}_BASE") or _phase_base(phase)


def _missing_base_failure(base: str, phase: int, range_checks: str) -> str:
    """The failure the gate reports when the base commit is not there.

    A missing base is an ENVIRONMENT failure, not a phase failure: a wrong
    constant or a shallow clone. The range checks are NOT silently
    skipped -- the message says they did not run and the gate goes red.
    """
    return (
        f"the base commit {base!r} is not in this repository, so the "
        f"phase range ({base}..HEAD) could not be measured: the range "
        f"checks ({range_checks}) did NOT run and the gate FAILS rather than "
        f"skipping them. Either PHASE_{phase}_BASE is wrong, or this clone is "
        f"shallow -- `git fetch --unshallow` (or `git fetch --depth=0`) "
        f"brings the history the phase-range checks need."
    )


def _junit_counts(xml_path: Path) -> dict[str, int]:
    """The totals pytest wrote into its junit XML.

    pytest 9 writes the counts on the `<testsuite>` elements; the
    `<testsuites>` root carries only a NAME, so the totals are the SUM
    over the suites -- reading the root's attributes would read nothing.
    """
    root = ET.parse(xml_path).getroot()
    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    for suite in root.iter("testsuite"):
        for key in totals:
            totals[key] += int(suite.get(key, "0"))
    return totals


def _is_inside_the_repository(path: Path) -> bool:
    """Whether the path lives inside the repository (constraint L7)."""
    try:
        path.resolve().relative_to(ROOT.resolve())
    except ValueError:
        return False
    return True


def _run_pytest_with_junit(
    targets: list[str],
    expected_tests: int,
    timeout: int,
) -> list[str]:
    """Run pytest and return the problems (empty when the run is green).

    The junit XML is READ, not the exit code: `pytest -q` exits 0 when
    every case was SKIPPED, and a skipped test is not a pass. So the gate
    requires the expected number of cases, zero failures, zero errors and
    ZERO skips.

    The XML is written OUTSIDE the repository (L7) and the temporary
    directory is removed when this returns.
    """
    with tempfile.TemporaryDirectory(prefix="b75-gate-") as tmp:
        xml_path = Path(tmp) / "junit.xml"
        if _is_inside_the_repository(xml_path):
            return [
                "the junit XML would be written INSIDE the repository (L7): "
                f"{xml_path}"
            ]
        proc = _run(
            [
                sys.executable,
                "-m",
                "pytest",
                *targets,
                "-q",
                "--no-header",
                f"--junitxml={xml_path}",
            ],
            timeout,
        )
        if proc.returncode != 0:
            return [f"pytest exited {proc.returncode}:\n{_describe(proc)[-4000:]}"]
        if not xml_path.is_file():
            return ["pytest wrote no junit XML: the result cannot be read"]
        try:
            totals = _junit_counts(xml_path)
        except (ET.ParseError, OSError, ValueError) as exc:
            return [f"the junit XML could not be read: {exc}"]
        problems: list[str] = []
        if totals["tests"] != expected_tests:
            problems.append(
                f"expected {expected_tests} test cases, pytest ran "
                f"{totals['tests']}"
            )
        if totals["failures"]:
            problems.append(f"{totals['failures']} case(s) FAILED")
        if totals["errors"]:
            problems.append(f"{totals['errors']} case(s) ERRORED")
        if totals["skipped"]:
            problems.append(
                f"{totals['skipped']} case(s) were SKIPPED: a skipped test "
                "is not a pass"
            )
        return problems


def _missing_golden_names(output: str) -> list[str]:
    """The golden frames the harness did NOT report as matching.

    The harness prints "GOLDENS MATCH: <the frames it compared>". The
    gate reads that line instead of trusting the exit code: a harness
    that compared ONE frame and exited 0 is not a proof of six.
    """
    reported: set[str] = set()
    for line in output.splitlines():
        if line.startswith("GOLDENS MATCH:"):
            reported = {
                name.strip() for name in line.split(":", 1)[1].split(",")
            }
    return [name for name in GOLDEN_FRAME_NAMES if name not in reported]


def _print_verdict(phase: int, failures: list[str]) -> int:
    """Print the verdict and return the exit code."""
    if failures:
        print(f"PHASE {phase} GATE FAILED:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print(f"PHASE {phase} GATE OK")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="The BLOQUE 75 gate: every check, every failure."
    )
    parser.add_argument(
        "--base",
        default=None,
        metavar="BASE",
        help=(
            "the base commit of the phase (the range the gate measures). "
            "Precedence: --base, then the PHASE<n>_BASE environment variable, "
            "then the PHASE_<n>_BASE constant in this file"
        ),
    )
    parser.add_argument(
        "--phase",
        type=int,
        choices=(1, 2),
        default=1,
        help=(
            "which phase's gate to run: 1 = the enemy sets (the default, so "
            "a bare `gate.py` keeps meaning Phase 1), 2 = the layered "
            "rendering engine"
        ),
    )
    args = parser.parse_args(argv)
    base = resolve_base(args.base, args.phase)

    # BLOQUE 76: an EMPTY range measures NOTHING.
    #
    # The range is how the gate sees a PNG committed INSIDE the phase:
    # the working-tree check (`git diff HEAD`) is blind to it, and only
    # `git diff base..HEAD` is not. With an empty range every range check
    # has zero commits to look at, finds nothing to complain about, and
    # the gate prints "GATE OK" for a phase it never looked at. The
    # promise ("not one PNG byte changed inside the phase") would be
    # UNCHECKED and the gate would still be green.
    #
    # This is checked FIRST, before any other check, because a gate that
    # has to run everything before it can admit it looked at nothing is a
    # gate that wastes the CI budget to learn it is blind.
    count = _range_commit_count(base)
    if count == 0:
        return _print_verdict(
            args.phase,
            [
                f"the phase range ({base}..HEAD) is EMPTY: it holds 0 "
                "commits, so the range checks would measure NOTHING and the "
                "gate would report OK without having checked the phase's "
                "promise. Either the base constant is wrong, or the "
                "phase's work is already merged and the base has to point "
                "at the commit the phase started from"
            ],
        )

    if args.phase == 2:
        return _run_phase_2(base)
    return _run_phase_1(base)


def _run_phase_1(base: str) -> int:
    """The Phase 1 gate: the enemy sets are ready for Phase 2."""
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

    # The base commit must EXIST for the phase range to be measurable. This
    # check comes FIRST, before every range check, because a missing base is
    # not a phase failure but an ENVIRONMENT failure -- a wrong constant or
    # a shallow clone -- and the range checks below would otherwise fail
    # with a cryptic git error ("bad revision") instead of saying what is
    # wrong and how to fix it.
    #
    # A missing base FAILS the gate. The range checks are not silently
    # skipped: the failure says they did not run, and the gate goes red.
    base_check = _git(["rev-parse", "--verify", "--quiet", f"{base}^{{commit}}"])
    base_missing = base_check.returncode != 0
    if base_missing:
        failures.append(f"G11: {_missing_base_failure(base, 1, 'G5, G11')}")

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

    # The range half of G5 needs the base commit. When the base is missing,
    # G11 has already said why and the gate is already failing, so the
    # check is reported as "did not run" instead of as a cryptic git error.
    if not base_missing:
        bosses = _goliath_assets_diff(base)
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

    # verify_contract is imported HERE, on purpose: the module sets
    # SDL_VIDEODRIVER=dummy AT IMPORT TIME, so importing it at module level
    # would make the gate permanently headless -- ensure_display() (which
    # only falls back to the dummy driver when the machine has no real
    # display) would never get the chance to keep the real one.
    from sprite_pipeline.verify_contract import verify as verify_set_contract

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
    #
    # The base commit was already verified above: when it is missing, the
    # gate has already failed with the reason, and the range check is
    # reported as "did not run" instead of as a cryptic git error.
    #
    # BLOQUE 75 Fase 2: the RANGE check excludes ``tools/golden/``. The
    # golden frames are PROOF FIXTURES, not art: BLOQUE 75 Fase 2 Task 1
    # commits them (spec decision B3 -- the measurement is versioned), and
    # a `*.png` pathspec cannot tell a new fixture from a changed sprite.
    # The promise G11 protects -- "not one PNG byte of the ART changed" --
    # is untouched: `Assets/sprites/` is not excluded, and the WORKING TREE
    # check below keeps the strict `*.png` pathspec, so a golden frame
    # edited by hand on disk still turns the gate red.
    if not base_missing:
        png_range = _git(
            ["diff", "--stat", f"{base}..HEAD", "--", "*.png", ":!tools/golden/"]
        )
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
    #
    # The junit XML is READ, not the exit code: `pytest` exits 0 when
    # every case was SKIPPED, and a skipped test is not a pass. The XML
    # also carries the exact count, so a guard that stopped running is a
    # failure with a diagnosis instead of a green gate.
    for problem in _run_pytest_with_junit(
        list(GUARD_TESTS), GUARD_TEST_CASES, GUARDS_TIMEOUT_S
    ):
        failures.append(f"G13: the enemy guards are red: {problem}")

    return _print_verdict(1, failures)


def _run_phase_2(base: str) -> int:
    """The Phase 2 gate: the layered rendering engine is done.

    Six checks, and every one of them can fail:

      P2-G1  the golden frames are pixel-identical to the committed ones;
      P2-G2  the capture harness is reproducible;
      P2-G3  the type gate of src/render/ and src/anim/ is clean;
      P2-G4  the layer order is pinned;
      P2-G5  not one PNG byte of the art moved;
      P2-G6  GOLIATH's contract still holds.
    """
    pygame.init()
    ensure_display()

    failures: list[str] = []

    # The base commit must EXIST for the phase range to be measurable, and
    # a missing base FAILS the gate: the range check is reported as "did
    # not run" instead of as a cryptic git error.
    base_check = _git(["rev-parse", "--verify", "--quiet", f"{base}^{{commit}}"])
    base_missing = base_check.returncode != 0
    if base_missing:
        failures.append(f"P2-G5: {_missing_base_failure(base, 2, 'P2-G5')}")

    # P2-G1: the golden frames are pixel-identical to the committed ones.
    # The junit XML is read, not the exit code: the test SKIPS a case when
    # its golden is missing, and pytest exits 0 when everything was
    # skipped.
    for problem in _run_pytest_with_junit(
        [GOLDEN_TEST], GOLDEN_TEST_CASES, GUARDS_TIMEOUT_S
    ):
        failures.append(f"P2-G1: {problem}")

    # P2-G2: the harness is reproducible AND compared all six frames. The
    # OUTPUT is checked, not only the exit code: a harness that compared
    # one frame and exited 0 is not a proof of six.
    proc = _run(
        [sys.executable, str(ROOT / GOLDEN_HARNESS), "--check"],
        GOLDEN_TIMEOUT_S,
    )
    if proc.returncode != 0:
        failures.append(
            f"P2-G2: the harness is not reproducible:\n{_describe(proc)[-4000:]}"
        )
    else:
        missing = _missing_golden_names(proc.stdout)
        if missing:
            failures.append(
                "P2-G2: the harness did not report every golden frame: "
                f"missing {', '.join(missing)}"
            )

    # P2-G3: the type gate. `mypy src/` as a whole is NOT clean (the
    # pre-existing errors of src/ui/ and src/core/ are not this phase's
    # business), so the gate names the two directories it owns.
    mypy_cmd = _mypy_command()
    if mypy_cmd is None:
        failures.append(
            "P2-G3: mypy cannot be run -- install the dev requirements "
            "(`python -m pip install -r requirements-dev.txt`) or make `uvx` available"
        )
    else:
        proc = _run([*mypy_cmd, *MYPY_TARGETS], MYPY_TIMEOUT_S)
        if proc.returncode != 0:
            failures.append(
                f"P2-G3: mypy reported errors in {' and '.join(MYPY_TARGETS)}:\n"
                f"{_describe(proc)[-4000:]}"
            )

    # P2-G4: the layer order is pinned -- and the run must have really
    # happened: 3 cases, 0 failures, 0 skips.
    for problem in _run_pytest_with_junit(
        [LAYER_ORDER_TEST], LAYER_ORDER_TEST_CASES, GUARDS_TIMEOUT_S
    ):
        failures.append(f"P2-G4: {problem}")

    # P2-G5: not one PNG byte of the art moved. TWO halves, exactly as
    # G11 does:
    #
    #   * the RANGE check is the one that matters for the phase's promise
    #     (a PNG committed inside the phase is invisible to `git diff
    #     HEAD`), and it EXCLUDES `tools/golden/`: the golden frames are
    #     PROOF FIXTURES, not art;
    #   * the WORKING TREE check keeps the strict `*.png` pathspec, so a
    #     golden frame edited by hand on disk still turns the gate red.
    if not base_missing:
        png_range = _git(
            ["diff", "--stat", f"{base}..HEAD", "--", "*.png", ":!tools/golden/"]
        )
        if png_range.returncode != 0:
            failures.append(
                f"P2-G5: the git command failed (exit {png_range.returncode}): "
                f"{_describe(png_range)}"
            )
        elif png_range.stdout.strip():
            failures.append(
                f"P2-G5: PNG files changed inside the phase ({base}..HEAD):\n"
                f"{png_range.stdout.strip()}"
            )

    png_tree = _git(["diff", "--stat", "HEAD", "--", "*.png"])
    if png_tree.returncode != 0:
        failures.append(
            f"P2-G5: the git command failed (exit {png_tree.returncode}): "
            f"{_describe(png_tree)}"
        )
    elif png_tree.stdout.strip():
        failures.append(
            f"P2-G5: PNG files changed in the working tree:\n{png_tree.stdout.strip()}"
        )

    # P2-G6: GOLIATH's contract still holds. The contract is NOT
    # re-invented here: verify_contract.py already owns it.
    #
    # verify_contract is imported HERE, on purpose: the module sets
    # SDL_VIDEODRIVER=dummy AT IMPORT TIME, so importing it at module
    # level would make the gate permanently headless.
    from sprite_pipeline.verify_contract import verify as verify_set_contract

    goliath_failures, _report = verify_set_contract("goliath", None)
    for line in goliath_failures:
        failures.append(f"P2-G6: {line}")

    return _print_verdict(2, failures)


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
