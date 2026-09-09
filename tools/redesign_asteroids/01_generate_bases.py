"""Stage 1: Generate 5 asteroid base images via mcode-tools (BLOQUE 61).

For each of the 5 asteroid variants, calls mcode-tools to generate a
1024x1024 base image using the MINE-ASTEROID reference image as a style
anchor, downloads it, saves to Assets/sprites/redesign/_base/, and logs
the node_id + prompt to asteroid_manifest.json.

Usage:
    python tools/redesign_asteroids/01_generate_bases.py
    python tools/redesign_asteroids/01_generate_bases.py --asteroid round  # one
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.redesign_asteroids._asteroid_specs import ASTEROIDS, AsteroidSpec
from tools.redesign_ships._ai_client import download_node, generate_ship_base


# Use the same "no 3/4 angle" wording from tools/redesign_ships/01_generate_bases.py
# (BLOQUE 62 prompt header), but applied to asteroids viewed from above.
PROMPT_TEMPLATE = (
    "16-bit pixel art, top-down view (strictly perpendicular, no 3/4 angle) "
    "viewed from directly above, isolated on pure black background. "
    "Sharp clean pixel edges, no anti-aliasing, no gradients, limited "
    "palette (max 12 colors), Metal Slug / Star Fox 64 aesthetic. "
    "Subject: a single rocky asteroid. Style: {FILL}. "
    "Mandatory elements: "
    "- irregular polygon outline with 12-16 craggy edges (asymmetric, not circle); "
    "- 2-3 horizontal Greek-key stripe bands (Star Fox 64 angular pattern: right-angle hooks at band ends); "
    "- 2-4 small craters scattered on the body; "
    "- 1-2 thin surface cracks; "
    "- 1-3 small mineral highlights (1-2px speckles). "
    "LOCKED 6-color palette (exact RGB values, no new colors): "
    "base_brown (140, 100, 60), highlight (180, 140, 90), mid_shadow (90, 60, 30), "
    "deep_shadow (50, 30, 15), black_crack (20, 10, 5), mineral_hi (210, 170, 110). "
    "The asteroid is a MINE-ASTEROID closed lookalike: the body could split horizontally "
    "to reveal a hidden gun, but stays closed in this view. "
)


BASE_DIR = PROJECT_ROOT / "Assets" / "sprites" / "redesign" / "_base"
MANIFEST_PATH = PROJECT_ROOT / "tools" / "redesign_asteroids" / "asteroid_manifest.json"


def build_prompt(spec: AsteroidSpec) -> str:
    return PROMPT_TEMPLATE.format(FILL=spec.prompt_fill)


def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {"bases": {}}


def save_manifest(m: dict) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(m, indent=2), encoding="utf-8")


def generate_one(spec: AsteroidSpec, manifest: dict) -> None:
    out_path = BASE_DIR / f"asteroid_{spec.key}_base.png"
    if out_path.exists():
        print(f"[skip] {spec.key}: {out_path} already exists")
        return
    print(f"[gen ] {spec.key} ({spec.display_name})")
    prompt = build_prompt(spec)
    print(f"        prompt length: {len(prompt)} chars")
    node_id = generate_ship_base(prompt=prompt, output_file=str(out_path))
    print(f"        node_id={node_id}, downloading...")
    download_node(node_id, str(out_path))
    manifest["bases"][spec.key] = {
        "node_id": node_id,
        "prompt": prompt,
        "display_name": spec.display_name,
        "out_path": str(out_path),
        "size_bytes": out_path.stat().st_size,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    save_manifest(manifest)
    print(f"        saved: {out_path} ({out_path.stat().st_size} bytes)")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--asteroid", help="Generate only this asteroid key")
    args = parser.parse_args()
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()
    targets = ASTEROIDS if not args.asteroid else [a for a in ASTEROIDS if a.key == args.asteroid]
    if args.asteroid and not targets:
        print(f"unknown asteroid: {args.asteroid}")
        return 1
    for spec in targets:
        generate_one(spec, manifest)
    print(f"\nDone. {len(targets)} base(s) processed. Manifest: {MANIFEST_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
