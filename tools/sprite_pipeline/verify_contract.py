"""BLOQUE 74: verify the sprite pipeline's CONTRACT on a shipped set.

The auditor classifies; this asserts the result is what the set is
supposed to be. It runs against the SHIPPED code (src/anim/ and
tools/sprite_pipeline/), not against a plan, so it is a real guard: if the
art, the manifest or the measurement changes without the contract changing,
this fails.

Usage:
    python tools/sprite_pipeline/verify_contract.py goliath
    python tools/sprite_pipeline/verify_contract.py goliath --json
    python tools/sprite_pipeline/verify_contract.py goliath --root <dir>

Checks:
    1. every frame of every clip resolves (no missing ellipse, no missing eye)
    2. no FAIL state survives
    3. rendering the anchors twice is byte-identical (determinism)
    4. the committed anchors.toml equals the freshly rendered one (freshness)
    5. for a set with a known contract, the findings match it exactly
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from src.anim.manifest import load_set  # noqa: E402
from sprite_pipeline.audit import FAIL_STATES, audit_set, render_anchors_toml  # noqa: E402

# The contract of the shipped GOLIATH set, measured on the real pixels.
#
# Seven frames have no credible plate in the art (the AI generator drew the
# character turned around, or the baked beam IS the contour), so their
# ellipse is reconstructed by interpolation. Three more have the brass probe
# and the shape measurement disagreeing, which is what a crouching or
# collapsing boss looks like.
#
# The FAIL column is the important one: it is EMPTY. Two frames used to be
# FAIL (javelin/frame_03 and purple_bullet/frame_06, the ones drawn
# turned around); the repair mirrored them and now they are reconstructed
# like the rest.
GOLIATH_CONTRACT: dict[tuple[str, int], list[str]] = {
    ("javelin", 3): ["FUERA_DE_RANGO"],
    ("javelin", 4): ["FUERA_DE_RANGO"],
    ("javelin", 7): ["FUERA_DE_RANGO"],
    ("laser", 4): ["FUERA_DE_RANGO"],
    ("laser", 5): ["FIRMA_AMBIGUA"],
    ("laser", 7): ["FUERA_DE_RANGO"],
    ("purple_bullet", 6): ["FUERA_DE_RANGO"],
    ("purple_bullet", 8): ["FUERA_DE_RANGO"],
    ("death", 2): ["FIRMA_AMBIGUA"],
    ("death", 7): ["FIRMA_AMBIGUA"],
}

KNOWN_CONTRACTS = {"goliath": GOLIATH_CONTRACT}


def verify(set_name: str, root: Path | None) -> tuple[list[str], dict]:
    """Return (failures, report). Every entry in failures is a broken contract."""
    failures: list[str] = []
    report: dict = {"set": set_name}

    try:
        anim_set = load_set(set_name, root=root) if root else load_set(set_name)
    except Exception as exc:  # noqa: BLE001 - the message is the point
        return [f"the set could not be loaded: {exc}"], report

    try:
        findings, measurements = audit_set(anim_set)
    except Exception as exc:  # noqa: BLE001 - a missing frame is a finding
        # The audit loads the frames with pygame, and a frame that is
        # not there used to escape as a traceback: the guard died
        # instead of saying what was wrong. A guard has to REPORT.
        return [f"the set could not be audited: {exc}"], report

    by_frame: dict[tuple[str, int], list[str]] = {}
    for finding in findings:
        by_frame.setdefault((finding.clip, finding.frame), []).append(finding.state)

    report["frames_with_findings"] = len(by_frame)
    report["findings"] = {f"{c}/f{n:02d}": s for (c, n), s in sorted(by_frame.items())}

    # 1. every frame resolves
    unresolved = [
        f"{m.clip}/frame_{m.frame:02d}"
        for m in measurements
        if m.shield is None or m.eye is None
    ]
    if unresolved:
        failures.append(
            f"{len(unresolved)} frame(s) do not resolve: {', '.join(unresolved[:8])}"
        )

    # 2. no FAIL state survives
    fails = sorted({(f.clip, f.frame) for f in findings if f.state in FAIL_STATES})
    if fails:
        failures.append(
            "FAIL states survive (the pipeline would exit 1): "
            + ", ".join(f"{c}/frame_{n:02d}" for c, n in fails)
        )
    report["fail_states"] = [f"{c}/frame_{n:02d}" for c, n in fails]

    # 3. determinism: auditing twice gives the same anchors
    # The check re-runs the AUDIT, not the renderer. Rendering the same
    # measurements twice can only fail if the renderer itself is
    # nondeterministic; what could actually drift is the measurement.
    first = render_anchors_toml(anim_set, measurements)
    try:
        _, second_measurements = audit_set(anim_set)
    except Exception as exc:  # noqa: BLE001 - the message is the point
        failures.append(f"the set could not be audited a second time: {exc}")
        second = ""
    else:
        second = render_anchors_toml(anim_set, second_measurements)
    if first != second:
        failures.append("the audit is not deterministic: two audits differ")
    report["deterministic"] = first == second

    # 4. freshness: the committed anchors.toml equals the rendered one
    anchors_path = anim_set.path / "anchors.toml"
    if anchors_path.is_file():
        current = anchors_path.read_text(encoding="utf-8")
        if current != first:
            failures.append(
                "anchors.toml is stale -- regenerate it with "
                "`python tools/sprite_pipeline/run.py "
                f"{set_name} --fix`"
            )
        report["anchors_fresh"] = current == first
    else:
        failures.append(f"{anchors_path} does not exist")
        report["anchors_fresh"] = False

    # 5. the known contract, when we have one
    contract = KNOWN_CONTRACTS.get(set_name)
    if contract is not None and by_frame != contract:
        missing = sorted(set(contract) - set(by_frame))
        extra = sorted(set(by_frame) - set(contract))
        changed = sorted(
            k for k in set(contract) & set(by_frame) if contract[k] != by_frame[k]
        )
        parts = []
        if missing:
            parts.append("no longer reported: " + ", ".join(f"{c}/f{n:02d}" for c, n in missing))
        if extra:
            parts.append("newly reported: " + ", ".join(f"{c}/f{n:02d}" for c, n in extra))
        if changed:
            parts.append(
                "changed state: "
                + ", ".join(f"{c}/f{n:02d}" for c, n in changed)
            )
        failures.append("the findings do not match the contract -- " + "; ".join(parts))
    report["contract_known"] = contract is not None
    report["contract_matches"] = contract is None or by_frame == contract

    report["interpolated_shields"] = sum(
        1 for m in measurements if m.shield_source == "interpolated"
    )
    report["interpolated_eyes"] = sum(
        1 for m in measurements if m.eye_source == "interpolated"
    )

    return failures, report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify the sprite pipeline's contract on a shipped set."
    )
    parser.add_argument("set", help="set name under Assets/sprites/bosses/")
    parser.add_argument(
        "--root", help="verify a COPY of the set instead of the shipped one"
    )
    parser.add_argument("--json", action="store_true", help="machine-readable report")
    args = parser.parse_args(argv)

    pygame.init()
    pygame.display.set_mode((320, 480))

    root = Path(args.root) if args.root else None
    failures, report = verify(args.set, root)

    if args.json:
        print(json.dumps({"failures": failures, **report}, indent=2))
    else:
        for key in (
            "frames_with_findings",
            "fail_states",
            "deterministic",
            "anchors_fresh",
            "contract_known",
            "contract_matches",
            "interpolated_shields",
            "interpolated_eyes",
        ):
            print(f"  {key:<24} {report.get(key)}")
        for line in report.get("findings", {}).items():
            print(f"    {line[0]:<22} {' · '.join(line[1])}")
        if failures:
            print("\nCONTRACT BROKEN:")
            for line in failures:
                print(f"  - {line}")
        else:
            print("\nCONTRACT OK")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
