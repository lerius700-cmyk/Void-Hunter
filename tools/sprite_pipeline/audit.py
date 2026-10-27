"""BLOQUE 74: the sprite auditor.

Measures every frame of an animated set, classifies it into one of seven
states, and bakes the measurement into anchors.toml.

Read-only by default. Deterministic: the same assets in, the same verdict
out. No AI, no network, no writes unless --write-anchors is passed.

Usage:
    python tools/sprite_pipeline/audit.py goliath
    python tools/sprite_pipeline/audit.py goliath --json
    python tools/sprite_pipeline/audit.py goliath --write-anchors
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

import pygame

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.anim.manifest import AnimSet, Clip, load_set  # noqa: E402
from src.anim.measure import (  # noqa: E402
    ALPHA_MIN,
    alpha_centroid,
    color_centroid,
    credible_ellipse,
    interpolate,
    plate_ellipse,
    silhouette_bbox,
    silhouette_height,
)

STATES = (
    "COLAPSADO",
    "CORTADO",
    "LADO_EQUIVOCADO",
    "FIRMA_AMBIGUA",
    "AUSENTE",
    "FUERA_DE_RANGO",
    "ESCALADO",
)

# A FAIL blocks the pipeline. A WARN is informational and is resolved (or
# accepted) without touching the art.
#
# AUSENTE is a WARN, not a FAIL: a frame whose plate cannot be measured is
# resolved by interpolating it from the frames around it, which is a
# legitimate reconstruction rather than a default. The real gate is that no
# frame ends up with an unresolved feature -- that is what
# tests/test_features_detected_everywhere.py asserts.
#
# FIRMA_AMBIGUA is also a WARN. Two candidate definitions were measured
# against the 60 shipped frames and both were useless:
#
#   * "the measured region contains a baked-effect colour" fires on 59/60
#     frames, because (240,200,120) is the plate's OWN highlight, not only
#     the beam's;
#   * "excluding the colliding colours changes the measurement" fires on
#     0/60 frames, because the colliding pixels are isolated highlights
#     and never change a run boundary.
#
# The definition that survives is the one that asks whether the two
# INDEPENDENT detectors agree: the probe (a colour signature) and the
# shape measurement. When they disagree by more than the tolerance, one of
# them is measuring the wrong thing.
FAIL_STATES = frozenset(
    {"COLAPSADO", "CORTADO", "LADO_EQUIVOCADO"}
)


@dataclass(frozen=True)
class Finding:
    """One problem, in one frame."""

    clip: str
    frame: int
    state: str
    detail: str


@dataclass(frozen=True)
class FrameMeasurement:
    """The measurement of one frame, ready to be baked."""

    clip: str
    frame: int
    body_dx: int
    body_dy: int
    eye: tuple[int, int] | None
    eye_source: str
    shield: tuple[float, float, float, float] | None
    shield_source: str


def _load_surface(path: Path) -> pygame.Surface:
    return pygame.image.load(str(path)).convert_alpha()


def _frame_path(anim_set: AnimSet, clip: Clip, index: int) -> Path:
    return anim_set.path / clip.dir / f"frame_{index:02d}.png"


def _md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def _clip_probe_columns(
    anim_set: AnimSet, clip: Clip, surfaces: list
) -> list[float | None]:
    """Probe column per frame: where the brass signature sits in each frame.

    The probe inherits the parent's warm rule: the brass signature also
    matches two of the beam's colours, so without the warm filter the
    probe latches onto the beam.
    """
    rule = anim_set.part("shield_plate").detect
    if rule is None or rule.probe is None:
        return [None] * len(surfaces)
    out: list[float | None] = []
    for surf in surfaces:
        found = color_centroid(surf, rule.probe, warm=rule.warm_fallback)
        out.append(found[0] if found else None)
    return out


def audit_set(anim_set: AnimSet) -> tuple[list[Finding], list[FrameMeasurement]]:
    """Measure every frame of every clip.

    The findings describe the ART. The measurements are the REPAIRED
    result: a frame whose plate could not be measured gets its ellipse
    interpolated from the frames around it, so the oval keeps tracking the
    arm instead of falling back to a constant.
    """
    findings: list[Finding] = []
    measurements: list[FrameMeasurement] = []

    shield_part = anim_set.part("shield_plate")
    eye_part = anim_set.part("eye")

    for clip in anim_set.clips.values():
        surfaces = [
            _load_surface(_frame_path(anim_set, clip, i)) for i in range(clip.frames)
        ]

        # --- COLAPSADO: duplicate frames inside a clip -----------------
        digests: dict[str, list[int]] = {}
        for i in range(clip.frames):
            path = _frame_path(anim_set, clip, i)
            digests.setdefault(_md5(path), []).append(i)
        for digest, indices in digests.items():
            if len(indices) > 1:
                findings.append(
                    Finding(
                        clip.id,
                        indices[0],
                        "COLAPSADO",
                        f"frames {indices} share md5 {digest[:8]} -- the animation is a still",
                    )
                )

        probe_cols = _clip_probe_columns(anim_set, clip, surfaces)
        good_cols = sorted(c for c in probe_cols if c is not None)
        # The TRUE median -- the average of the two middle values. The
        # upper-middle element would shift the threshold by up to 0.2 px and
        # make the auditor decide against a different median than the one
        # the baseline table was measured with.
        probe_median = statistics.median(good_cols) if good_cols else 0.0

        rule = shield_part.detect
        heights = [
            silhouette_height(surf, rule, drop_warm=True) for surf in surfaces
        ]
        good_heights = sorted(h for h in heights if h is not None)
        height_median = statistics.median(good_heights) if good_heights else 0

        for i, surf in enumerate(surfaces):
            frame_no = i

            # --- CORTADO: silhouette touching the canvas edge -----------
            bbox = silhouette_bbox(surf)
            if bbox is not None:
                left, top, right, bottom = bbox
                w, h = surf.get_size()
                if left < 2 or top < 2 or (w - right) < 2 or (h - bottom) < 2:
                    findings.append(
                        Finding(
                            clip.id,
                            frame_no,
                            "CORTADO",
                            f"silhouette margins L{left} T{top} R{w - right} B{h - bottom}",
                        )
                    )

            # --- ESCALADO: silhouette height vs the clip median ---------
            height = heights[i]
            if height is not None and height_median:
                deviation = abs(height - height_median) / height_median
                if deviation > clip.scale_tolerance:
                    findings.append(
                        Finding(
                            clip.id,
                            frame_no,
                            "ESCALADO",
                            f"height {height} vs clip median {height_median} "
                            f"({deviation * 100:.0f}% > {clip.scale_tolerance * 100:.0f}%)",
                        )
                    )

            # --- body centroid: the registration correction -------------
            centre = alpha_centroid(surf)
            if centre is None:
                body_dx = body_dy = 0
            else:
                body_dx = int(round(anim_set.anchor[0] - centre[0]))
                body_dy = int(round(anim_set.anchor[1] - centre[1]))

            # --- eye ------------------------------------------------------
            eye = None
            eye_source = "measured"
            if eye_part.detect is not None:
                found = color_centroid(surf, eye_part.detect)
                if found is not None:
                    eye = (int(round(found[0])), int(round(found[1])))
                else:
                    # The boss is a wreck by the end of the death clip: the
                    # last frame has no eye left to find. The part's
                    # on_missing policy (interpolate) resolves it.
                    eye_source = "missing"

            # --- shield plate ---------------------------------------------
            shield = None
            shield_source = "measured"
            if rule is not None:
                ellipse = credible_ellipse(surf, rule)
                if ellipse is None:
                    # Neither pass gave a credible ellipse. The plain
                    # measurement tells us whether the plate is absent
                    # entirely or merely implausible.
                    plain = plate_ellipse(surf, rule, drop_warm=False)
                    if plain is None:
                        shield_source = "missing"
                        findings.append(
                            Finding(clip.id, frame_no, "AUSENTE", "shield plate not found")
                        )
                    else:
                        shield_source = "out_of_range"
                        findings.append(
                            Finding(
                                clip.id,
                                frame_no,
                                "FUERA_DE_RANGO",
                                f"rx {plain[2]:.1f} ry {plain[3]:.1f} outside "
                                f"rx {rule.rx_range} ry {rule.ry_range}",
                            )
                        )
                else:
                    shield = ellipse

                probe_col = probe_cols[i]
                if probe_col is not None:
                    # --- LADO_EQUIVOCADO: turned-around character ----------
                    # This check must NOT depend on the shape measurement.
                    # The turned-around frames are exactly the ones whose
                    # shape measurement is NOT credible -- the shape rule
                    # finds the arm, not the plate -- so gating this on a
                    # credible ellipse would skip the very frames it exists
                    # to catch. The probe is independent of the shape rule,
                    # so it can answer the side question on its own.
                    centre_col = anim_set.anchor[0]
                    wrong_side = (
                        probe_col <= centre_col
                        if rule.side == "right"
                        else probe_col >= centre_col
                    )
                    stray = abs(probe_col - probe_median) > clip.side_tolerance
                    if wrong_side and stray:
                        findings.append(
                            Finding(
                                clip.id,
                                frame_no,
                                "LADO_EQUIVOCADO",
                                f"probe col {probe_col:.1f} (clip median "
                                f"{probe_median:.1f}), expected > {centre_col}",
                            )
                        )

                    # --- FIRMA_AMBIGUA: the two detectors disagree -------
                    # This one DOES need both: it is the disagreement
                    # between the two detectors that defines it.
                    if shield is not None and abs(probe_col - shield[0]) > clip.side_tolerance:
                        findings.append(
                            Finding(
                                clip.id,
                                frame_no,
                                "FIRMA_AMBIGUA",
                                f"probe col {probe_col:.1f} vs shape cx {shield[0]:.1f} "
                                f"disagree by more than {clip.side_tolerance:.0f}px",
                            )
                        )

            measurements.append(
                FrameMeasurement(
                    clip=clip.id,
                    frame=frame_no,
                    body_dx=body_dx,
                    body_dy=body_dy,
                    eye=eye,
                    eye_source=eye_source,
                    shield=shield,
                    shield_source=shield_source,
                )
            )

    measurements = _interpolate_missing(measurements)
    return findings, measurements


def _interpolate_missing(
    measurements: list[FrameMeasurement],
) -> list[FrameMeasurement]:
    """Fill the frames whose measurement was implausible.

    A frame whose plate could not be measured (or measured implausibly)
    gets its ellipse reconstructed from the frames around it, so the oval
    keeps tracking the arm instead of falling back to a constant.

    The findings still report the art problem -- the interpolation fixes
    the measurement, it does not fix the art.
    """
    by_clip: dict[str, list[FrameMeasurement]] = {}
    for m in measurements:
        by_clip.setdefault(m.clip, []).append(m)

    out: list[FrameMeasurement] = []
    for items in by_clip.values():
        items.sort(key=lambda m: m.frame)
        cxs = [m.shield[0] if m.shield else None for m in items]
        cys = [m.shield[1] if m.shield else None for m in items]
        rxs = [m.shield[2] if m.shield else None for m in items]
        rys = [m.shield[3] if m.shield else None for m in items]
        eye_cols = [float(m.eye[0]) if m.eye else None for m in items]
        eye_rows = [float(m.eye[1]) if m.eye else None for m in items]
        for i, m in enumerate(items):
            eye = m.eye
            eye_source = m.eye_source
            if eye is None:
                ex = interpolate(eye_cols, i)
                ey = interpolate(eye_rows, i)
                if ex is not None and ey is not None:
                    eye = (int(round(ex)), int(round(ey)))
                    eye_source = "interpolated"
            if m.shield is not None and eye is not None:
                out.append(
                    FrameMeasurement(
                        clip=m.clip,
                        frame=m.frame,
                        body_dx=m.body_dx,
                        body_dy=m.body_dy,
                        eye=eye,
                        eye_source=eye_source,
                        shield=m.shield,
                        shield_source=m.shield_source,
                    )
                )
                continue
            cx = interpolate(cxs, i)
            cy = interpolate(cys, i)
            rx = interpolate(rxs, i)
            ry = interpolate(rys, i)
            if None in (cx, cy, rx, ry):
                out.append(
                    FrameMeasurement(
                        clip=m.clip,
                        frame=m.frame,
                        body_dx=m.body_dx,
                        body_dy=m.body_dy,
                        eye=eye,
                        eye_source=eye_source,
                        shield=None,
                        shield_source=m.shield_source,
                    )
                )
                continue
            out.append(
                FrameMeasurement(
                    clip=m.clip,
                    frame=m.frame,
                    body_dx=m.body_dx,
                    body_dy=m.body_dy,
                    eye=eye,
                    eye_source=eye_source,
                    shield=(cx, cy, rx, ry),
                    shield_source="interpolated",
                )
            )
    out.sort(key=lambda m: (m.clip, m.frame))
    return out


def _fmt_number(value: float) -> str:
    text = f"{value:.1f}"
    return text[:-2] if text.endswith(".0") else text


def render_anchors_toml(anim_set: AnimSet, measurements: list[FrameMeasurement]) -> str:
    """Render anchors.toml from the measurements.

    Deterministic: the same measurements always produce the same text, so
    the freshness test can compare it byte for byte.
    """
    manifest_bytes = (anim_set.path / "manifest.toml").read_bytes()
    lines = [
        "# BLOQUE 74: baked measurement of every frame.",
        "# GENERATED by tools/sprite_pipeline/audit.py --write-anchors",
        "# DO NOT HAND-EDIT: tests/test_anchors_are_fresh.py fails if this is stale.",
        "",
        "[meta]",
        'generated_by = "tools/sprite_pipeline/audit.py"',
        f'manifest_sha256 = "{hashlib.sha256(manifest_bytes).hexdigest()}"',
        "",
    ]
    for m in measurements:
        lines.append("[[anchors]]")
        lines.append(f'clip = "{m.clip}"')
        lines.append(f"frame = {m.frame}")
        lines.append(f"body_dx = {m.body_dx}")
        lines.append(f"body_dy = {m.body_dy}")
        if m.eye is None:
            lines.append("eye = [0, 0]")
        else:
            lines.append(f"eye = [{m.eye[0]}, {m.eye[1]}]")
        lines.append(f'eye_source = "{m.eye_source}"')
        if m.shield is None:
            lines.append("shield = [0.0, 0.0, 0.0, 0.0]")
        else:
            cx, cy, rx, ry = m.shield
            lines.append(
                f"shield = [{_fmt_number(cx)}, {_fmt_number(cy)}, "
                f"{_fmt_number(rx)}, {_fmt_number(ry)}]"
            )
        lines.append(f'shield_source = "{m.shield_source}"')
        lines.append("")
    return "\n".join(lines)


def write_anchors(
    anim_set: AnimSet, measurements: list[FrameMeasurement], path: Path
) -> None:
    path.write_text(render_anchors_toml(anim_set, measurements), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit an animated sprite set.")
    parser.add_argument("set", help="set name under Assets/sprites/bosses/")
    parser.add_argument("--json", action="store_true", help="machine-readable report")
    parser.add_argument(
        "--write-anchors", action="store_true", help="write anchors.toml"
    )
    args = parser.parse_args(argv)

    pygame.init()
    pygame.display.set_mode((320, 480))

    try:
        anim_set = load_set(args.set)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    findings, measurements = audit_set(anim_set)

    if args.json:
        print(
            json.dumps(
                {
                    "set": anim_set.name,
                    "findings": [
                        {
                            "clip": f.clip,
                            "frame": f.frame,
                            "state": f.state,
                            "detail": f.detail,
                        }
                        for f in findings
                    ],
                },
                indent=2,
            )
        )
    else:
        by_clip: dict[str, list[Finding]] = {}
        for f in findings:
            by_clip.setdefault(f.clip, []).append(f)
        for clip_id, items in by_clip.items():
            print(f"[clip] {clip_id}")
            for f in items:
                print(f"  frame_{f.frame:02d}  {f.state:<16} {f.detail}")
        # Count FRAMES, not findings: a frame can carry two findings
        # (javelin/frame_03 is FUERA_DE_RANGO *and* LADO_EQUIVOCADO).
        flagged = {(f.clip, f.frame) for f in findings}
        failing = {
            (f.clip, f.frame) for f in findings if f.state in FAIL_STATES
        }
        total = sum(c.frames for c in anim_set.clips.values())
        print(
            f"summary: {len(flagged)}/{total} frames with findings "
            f"({len(failing)} FAIL, {len(flagged) - len(failing)} WARN)"
        )

    if args.write_anchors:
        write_anchors(anim_set, measurements, anim_set.path / "anchors.toml")
        print(f"wrote {anim_set.path / 'anchors.toml'}")

    return 1 if any(f.state in FAIL_STATES for f in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
