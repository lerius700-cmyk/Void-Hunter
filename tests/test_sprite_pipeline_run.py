"""BLOQUE 74: the pipeline command must be honest and side-effect free.

The CLI is the thing a developer types, so its contract is:

    run.py <set>           audit only -- it writes NOTHING
    run.py <set> --fix     audit, repair, re-audit, then write the anchors
    run.py <set> --json    the same report, machine-readable

The anchors are written AFTER the repair and the re-audit, never before,
and never by a dry run: a command that reads like "audit only" must not
be able to regress the generated anchors.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from sprite_pipeline import run as pipeline  # noqa: E402

GOLIATH = ROOT / "Assets" / "sprites" / "bosses" / "goliath"
ANCHORS = GOLIATH / "anchors.toml"
REPAIRED_FRAMES = (
    GOLIATH / "javelin" / "frame_03.png",
    GOLIATH / "purple_bullet" / "frame_06.png",
)


def _md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


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


def test_the_cli_exits_zero_and_prints_pure_json():
    """The repaired set has no FAIL left, so the pipeline exits 0.

    The JSON must be parseable on its own: pygame's support banner goes to
    STDOUT, and the guard that suppresses it has to be in place before
    pygame is imported.
    """
    proc = _run_cli("goliath", "--json")

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


def test_the_json_summary_counts_frames():
    """The summary counts FRAMES, like the auditor does.

    A frame can carry two findings, so a finding count and a frame count
    are different numbers. The summary says which one it is.
    """
    report = json.loads(_run_cli("goliath", "--json").stdout.decode("utf-8"))
    summary = report["summary"]

    assert summary["frames_total"] == 60
    assert summary["frames_with_findings"] == 10
    assert summary["frames_failing"] == 0
    assert summary["frames_warning"] == 10
    # Every flagged frame carries exactly one finding in the repaired set.
    assert summary["findings_total"] == len(report["warnings"]) + len(
        report["failures"]
    )


def test_the_fix_run_changes_no_file():
    """The art is already repaired, so --fix has nothing to do.

    It must still re-audit and write the anchors, and it must not touch
    the shipped frames.
    """
    before = {path: _md5(path) for path in REPAIRED_FRAMES}
    anchors_before = _md5(ANCHORS)

    proc = _run_cli("goliath", "--fix")

    assert proc.returncode == 0, proc.stdout.decode("utf-8")
    assert {path: _md5(path) for path in REPAIRED_FRAMES} == before
    assert _md5(ANCHORS) == anchors_before


def test_the_dry_run_does_not_write_the_anchors(monkeypatch):
    """`run.py <set>` is audit-only: it writes nothing at all."""
    written = []
    monkeypatch.setattr(pipeline, "write_anchors", lambda *a, **k: written.append(a))

    assert pipeline.main(["goliath"]) == 0
    assert written == []


def test_the_fix_run_writes_the_anchors_after_the_re_audit(monkeypatch):
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
