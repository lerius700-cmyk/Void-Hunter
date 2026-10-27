"""BLOQUE 74: the sprite pipeline.

    python tools/sprite_pipeline/run.py goliath            # audit only
    python tools/sprite_pipeline/run.py goliath --fix      # audit, repair, re-audit
    python tools/sprite_pipeline/run.py goliath --json

Steps: validate -> audit -> repair -> re-audit -> anchors -> report.
Exits 1 when the final audit still has a FAIL.
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
    args = parser.parse_args(argv)

    pygame.init()
    pygame.display.set_mode((320, 480))

    try:
        anim_set = load_set(args.set)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    findings, measurements = audit_set(anim_set)
    actions: list[str] = []

    if args.fix:
        actions = repair_set(anim_set, findings, apply=True)
        findings, measurements = audit_set(anim_set)

    write_anchors(anim_set, measurements, anim_set.path / "anchors.toml")

    fails = [f for f in findings if f.state in FAIL_STATES]
    warns = [f for f in findings if f.state not in FAIL_STATES]

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
                },
                indent=2,
            )
        )
    else:
        for action in actions:
            print(f"repaired: {action}")
        for f in fails:
            print(f"  FAIL {f.clip}/frame_{f.frame:02d}  {f.state}: {f.detail}")
        for f in warns:
            print(f"  WARN {f.clip}/frame_{f.frame:02d}  {f.state}: {f.detail}")
        print(
            f"{anim_set.name}: {len(fails)} FAIL, {len(warns)} WARN, "
            f"{len(measurements)} frames measured"
        )

    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
