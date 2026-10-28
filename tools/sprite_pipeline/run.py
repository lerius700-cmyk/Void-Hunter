"""BLOQUE 74: the sprite pipeline.

    python tools/sprite_pipeline/run.py goliath            # audit only
    python tools/sprite_pipeline/run.py goliath --fix      # audit, repair, re-audit
    python tools/sprite_pipeline/run.py goliath --json

Steps: validate -> audit -> repair -> re-audit -> anchors -> report.
Exits 1 when the final audit still has a FAIL.

Without --fix the command WRITES NOTHING: it validates the manifest,
audits the art and reports. The anchors are written only by --fix, after
the repair and the re-audit, so they always carry the repaired
measurements -- and a dry run can never regress the generated file.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# pygame prints its support banner to STDOUT when the module is imported,
# which would corrupt the --json report. This has to be set BEFORE the
# import below (same guard as tools/sprite_pipeline/audit.py).
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

ROOT = Path(__file__).resolve().parent.parent.parent
# The package lives in tools/sprite_pipeline/, so BOTH the repository root
# (for `src.anim.manifest`) and the tools directory (for
# `sprite_pipeline.audit`) have to be importable when this file is run as
# a script.
for _entry in (str(ROOT), str(ROOT / "tools")):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)

import pygame  # noqa: E402

from src.anim.manifest import load_set  # noqa: E402
from sprite_pipeline import ensure_display  # noqa: E402
from sprite_pipeline.audit import (  # noqa: E402
    FAIL_STATES,
    audit_set,
    write_anchors,
)
from sprite_pipeline.repair import repair_set  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the sprite pipeline.")
    parser.add_argument("set", help="set name under Assets/sprites/bosses/")
    parser.add_argument(
        "--fix", action="store_true", help="apply repairs (mirrors, re-pads)"
    )
    parser.add_argument("--json", action="store_true", help="machine-readable report")
    parser.add_argument(
        "--root",
        default=None,
        help=(
            "directory that HOLDS the sets (default: the repository's "
            "Assets/sprites/bosses). Point it at a copy to repair a set "
            "without touching the shipped art."
        ),
    )
    args = parser.parse_args(argv)

    pygame.init()
    ensure_display()

    try:
        anim_set = load_set(args.set, root=Path(args.root) if args.root else None)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    findings, measurements = audit_set(anim_set)
    actions: list[str] = []

    if args.fix:
        actions = repair_set(anim_set, findings, apply=True)
        findings, measurements = audit_set(anim_set)
        # The anchors are written AFTER the repair and the re-audit, so
        # they carry the repaired measurements, never the pre-repair ones.
        write_anchors(anim_set, measurements, anim_set.path / "anchors.toml")

    fails = [f for f in findings if f.state in FAIL_STATES]
    warns = [f for f in findings if f.state not in FAIL_STATES]

    # Count FRAMES, exactly like the auditor does: a frame can carry two
    # findings (javelin/frame_03 was FUERA_DE_RANGO *and*
    # LADO_EQUIVOCADO), so the number of findings and the number of
    # frames are different numbers. The summary says which one it reports.
    flagged = {(f.clip, f.frame) for f in findings}
    failing = {(f.clip, f.frame) for f in findings if f.state in FAIL_STATES}
    total = sum(c.frames for c in anim_set.clips.values())
    summary = {
        "frames_total": total,
        "frames_with_findings": len(flagged),
        "frames_failing": len(failing),
        "frames_warning": len(flagged) - len(failing),
        "findings_total": len(findings),
    }

    if args.json:
        print(
            json.dumps(
                {
                    "set": anim_set.name,
                    "actions": actions,
                    "failures": [
                        {"clip": f.clip, "frame": f.frame, "state": f.state, "detail": f.detail}
                        for f in fails
                    ],
                    "warnings": [
                        {"clip": f.clip, "frame": f.frame, "state": f.state, "detail": f.detail}
                        for f in warns
                    ],
                    "summary": summary,
                },
                indent=2,
            )
        )
    else:
        for action in actions:
            print(action)
        for f in fails:
            print(f"  FAIL {f.clip}/frame_{f.frame:02d}  {f.state}: {f.detail}")
        for f in warns:
            print(f"  WARN {f.clip}/frame_{f.frame:02d}  {f.state}: {f.detail}")
        print(
            f"{anim_set.name}: {summary['frames_with_findings']}/"
            f"{summary['frames_total']} frames with findings "
            f"({summary['frames_failing']} FAIL, {summary['frames_warning']} WARN), "
            f"{summary['findings_total']} findings"
        )

    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
