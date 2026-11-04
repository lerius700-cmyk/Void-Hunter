"""BLOQUE 74: the pipeline command must be honest and side-effect free.

The CLI is the thing a developer types, so its contract is:

    run.py <set>           audit only -- it writes NOTHING
    run.py <set> --fix     audit, repair, re-audit, then write the anchors
    run.py <set> --json    the same report, machine-readable

The anchors are written AFTER the repair and the re-audit, never before,
and never by a dry run: a command that reads like "audit only" must not
be able to regress the generated anchors.

BLOQUE 74 (final review): EVERY run happens against a COPY of the set in
`tmp_path`, never against the repository. `--fix` rewrites anchors.toml and
can mirror the shipped frames, so a test that ran it in place could rewrite
the shipped art in the middle of the suite. The copy is made by a fixture.

There are TWO ways into the pipeline, and both have to be pointed at it:

- the SUBPROCESS CLI is pointed at the copy with `--root`;
- the IN-PROCESS entry point (`run.main`) has no `--root` to be given, so
  the fixture points it at the copy by patching the RESOLUTION: `run.py`
  resolves the set first and then loads it from the directory that holds
  the resolved one, so the resolution is what decides WHERE the set is.
  Patching the loader alone is not enough -- `run.py` hands it a root
  that points at the repository, and the copy is never reached.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from sprite_pipeline import run as pipeline  # noqa: E402

# The real entry points, captured before the fixture points the pipeline
# at the copy.
_REAL_LOAD_SET = pipeline.load_set
_REAL_RESOLVE_SET = pipeline.resolve_set

GOLIATH = ROOT / "Assets" / "sprites" / "bosses" / "goliath"
SHIPPED_ANCHORS = GOLIATH / "anchors.toml"
REPAIRED_FRAMES = (
    Path("javelin") / "frame_03.png",
    Path("purple_bullet") / "frame_06.png",
)


@pytest.fixture
def goliath_copy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A COPY of the GOLIATH set, in tmp_path.

    The pipeline's `--fix` REWRITES anchors.toml and can mirror the shipped
    frames. Running it against the repository tree would let a test rewrite
    the shipped files in the middle of the suite, so every run happens
    against this copy instead.

    The copy is byte-identical to the shipped set, so the counts the
    pipeline reports are the counts of the shipped art.
    """
    sets_root = tmp_path / "sets"
    sets_root.mkdir()
    copy = sets_root / "goliath"
    shutil.copytree(GOLIATH, copy)

    # The in-process entry point RESOLVES the set first and then loads it
    # from the directory that holds the resolved one (`run.py`:
    # `load_set(args.set, root=set_dir.parent)`). The resolution is what
    # decides WHERE the set is, so THAT is what has to be pointed at the
    # copy: patching only the loader is not enough, because `run.py`
    # hands it a root that points at the repository and the copy is
    # never reached.
    monkeypatch.setattr(
        pipeline,
        "resolve_set",
        lambda name, root=None: _REAL_RESOLVE_SET(
            name, root if root is not None else sets_root
        ),
    )
    # The loader is pointed at the copy too, so the two agree even if the
    # resolution is bypassed.
    monkeypatch.setattr(
        pipeline,
        "load_set",
        lambda name, root=None: _REAL_LOAD_SET(
            name, root if root is not None else sets_root
        ),
    )
    return copy


def _md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def _fingerprint(path: Path) -> tuple[str, int]:
    """The content AND the mtime of a file.

    The mtime is half of the fingerprint on purpose: `--fix` writes the
    anchors UNCONDITIONALLY, so a run that reaches the shipped set
    rewrites the file even when the content comes out identical -- and a
    guard that only compares md5 cannot see that.
    """
    return _md5(path), path.stat().st_mtime_ns


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "sprite_pipeline" / "run.py"),
            *args,
        ],
        cwd=ROOT,
        capture_output=True,
        timeout=300,
    )


def _run_cli_on(root: Path, *args: str) -> subprocess.CompletedProcess:
    """The CLI, pointed at a COPY of the sets."""
    return subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "sprite_pipeline" / "run.py"),
            *args,
            "--root",
            str(root),
        ],
        cwd=ROOT,
        capture_output=True,
        timeout=300,
    )


def test_the_cli_exits_zero_and_prints_pure_json(goliath_copy: Path):
    """The repaired set has no FAIL left, so the pipeline exits 0.

    The JSON must be parseable on its own: pygame's support banner goes to
    STDOUT, and the guard that suppresses it has to be in place before
    pygame is imported.
    """
    proc = _run_cli_on(goliath_copy.parent, "goliath", "--json")

    stdout = proc.stdout.decode("utf-8")
    stderr = proc.stderr.decode("utf-8")

    assert proc.returncode == 0, stdout + stderr
    assert stdout.lstrip().startswith("{"), stdout[:200]
    assert "Hello from the pygame community" not in stdout, stdout[:200]
    assert stderr == "", stderr

    report = json.loads(stdout)
    assert report["set"] == "GOLIATH"
    assert report["actions"] == []
    assert report["failures"] == []
    assert isinstance(report["warnings"], list)


def test_the_json_summary_counts_frames(goliath_copy: Path):
    """The summary counts FRAMES, like the auditor does.

    A frame can carry two findings, so a finding count and a frame count
    are different numbers. The summary says which one it is.
    """
    report = json.loads(
        _run_cli_on(goliath_copy.parent, "goliath", "--json").stdout.decode("utf-8")
    )
    summary = report["summary"]

    assert summary["frames_total"] == 60
    assert summary["frames_with_findings"] == 10
    assert summary["frames_failing"] == 0
    assert summary["frames_warning"] == 10
    # Every flagged frame carries exactly one finding in the repaired set.
    assert summary["findings_total"] == len(report["warnings"]) + len(
        report["failures"]
    )


def test_the_fix_run_changes_no_file(goliath_copy: Path):
    """The art is already repaired, so --fix has nothing to do.

    It must still re-audit and write the anchors, and it must not touch
    the frames. The run happens on the COPY, so the shipped art is out of
    reach.
    """
    frames = [goliath_copy / rel for rel in REPAIRED_FRAMES]
    before = {path: _md5(path) for path in frames}
    anchors_before = _md5(goliath_copy / "anchors.toml")

    proc = _run_cli_on(goliath_copy.parent, "goliath", "--fix")

    assert proc.returncode == 0, proc.stdout.decode("utf-8")
    assert {path: _md5(path) for path in frames} == before
    assert _md5(goliath_copy / "anchors.toml") == anchors_before


def test_the_shipped_anchors_are_not_touched_by_the_suite(goliath_copy: Path):
    """The guard on the guard: the SHIPPED anchors survive the run.

    The copy is a byte-identical copy, so writing the copy's anchors must
    leave the shipped file untouched. If this fails, some other test is
    still running the pipeline against the repository tree.
    """
    shipped_before = _md5(SHIPPED_ANCHORS)

    proc = _run_cli_on(goliath_copy.parent, "goliath", "--fix")

    assert proc.returncode == 0, proc.stdout.decode("utf-8")
    assert _md5(SHIPPED_ANCHORS) == shipped_before


def test_the_in_process_run_does_not_touch_the_shipped_set(goliath_copy: Path):
    """The guard on the guard: the IN-PROCESS run must not reach the shipped set.

    The other guard (`test_the_shipped_anchors_are_not_touched_by_the_suite`)
    runs the CLI as a SUBPROCESS with `--root`, so it never exercised the
    in-process path -- the one that had lost its isolation.

    The fingerprint carries the mtime as well as the content: a rewrite
    with identical content leaves the md5 unchanged, so the md5 alone
    cannot see that the shipped file was written.
    """
    shipped_before = _fingerprint(SHIPPED_ANCHORS)
    frames_before = {
        path: _fingerprint(path) for path in sorted(GOLIATH.rglob("*.png"))
    }

    assert pipeline.main(["goliath", "--fix"]) == 0

    assert _fingerprint(SHIPPED_ANCHORS) == shipped_before, (
        "the in-process run rewrote the SHIPPED anchors: the fixture no "
        "longer isolates the set it resolves"
    )
    after = {path: _fingerprint(path) for path in frames_before}
    assert after == frames_before, (
        "the in-process run touched the SHIPPED frames: the fixture no "
        "longer isolates the set it resolves"
    )


def test_the_dry_run_does_not_write_the_anchors(
    goliath_copy: Path, monkeypatch: pytest.MonkeyPatch
):
    """`run.py <set>` is audit-only: it writes nothing at all."""
    written = []
    monkeypatch.setattr(pipeline, "write_anchors", lambda *a, **k: written.append(a))

    assert pipeline.main(["goliath"]) == 0
    assert written == []


def test_the_fix_run_writes_the_anchors_after_the_re_audit(
    goliath_copy: Path, monkeypatch: pytest.MonkeyPatch
):
    """The anchors come from the POST-repair measurements.

    The order is audit -> repair -> re-audit -> anchors. If the anchors
    were written before the re-audit they would carry the pre-repair
    numbers, and the freshness test would fail on the very next run.
    """
    events: list[str] = []
    real_audit = pipeline.audit_set

    def counting_audit(anim_set):
        events.append("audit")
        return real_audit(anim_set)

    monkeypatch.setattr(pipeline, "audit_set", counting_audit)
    monkeypatch.setattr(
        pipeline, "write_anchors", lambda *a, **k: events.append("anchors")
    )

    assert pipeline.main(["goliath", "--fix"]) == 0
    assert events == ["audit", "audit", "anchors"]


def test_the_cli_reports_an_unknown_set_without_a_traceback():
    proc = _run_cli("no-such-set")

    assert proc.returncode == 2
    stderr = proc.stderr.decode("utf-8")
    assert stderr.startswith("error:"), stderr
    assert "Traceback" not in stderr, stderr


def test_the_generated_anchors_use_lf_line_endings(goliath_copy: Path):
    """The generator writes LF, because the repository declares LF.

    `.gitattributes` declares `*.toml text eol=lf`, so a fresh checkout
    has the anchors in LF. `Path.write_text` in TEXT mode translates
    every "\\n" into "\\r\\n" on Windows, so the generator used to write
    CRLF: `--fix` changed the file on every run and left the working
    tree dirty.

    It passed on the worktree where the file happened to still be CRLF
    from before the attribute existed, and failed on every clean
    checkout -- the branch that had one measured 2 failures where the
    base had 1.
    """
    proc = _run_cli_on(goliath_copy.parent, "goliath", "--fix")
    assert proc.returncode == 0, proc.stdout.decode("utf-8")

    raw = (goliath_copy / "anchors.toml").read_bytes()
    assert b"\r\n" not in raw, (
        "the generator wrote CRLF: on a clean checkout --fix changes the "
        "file and dirties the tree"
    )
    assert raw.count(b"\n") > 0, "the generator wrote nothing"


def test_the_repository_declares_lf_for_the_toml():
    """The rule the generator has to honour is in the repository."""
    attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "*.toml text eol=lf" in attributes, (
        "the repository no longer declares the .toml as LF: the generator "
        "and the attribute have to agree"
    )
