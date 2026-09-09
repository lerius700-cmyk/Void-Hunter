"""Stage 1: Generate 8 base images via mcode-tools (BLOQUE 59).

For each of the 8 ships, calls mcode-tools to generate a 1024x1024 base
image, downloads it, saves to Assets/sprites/redesign/_base/, and logs
the node_id + prompt to manifest.json.

Usage:
    python tools/redesign_ships/01_generate_bases.py
    python tools/redesign_ships/01_generate_bases.py --ship enemy_scout  # regenerate one
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.redesign_ships._ai_client import download_node, generate_ship_base
from tools.redesign_ships._ship_specs import SHIPS, ShipSpec


PROMPT_TEMPLATE = (
    "16-bit pixel art, STRICT TOP-DOWN VIEW (perpendicular, no 3/4 angle) "
    "viewed from directly above the ship. The ship's NOSE points DOWN "
    "toward the bottom of the image. WINGS spread OUT to the left and "
    "right sides of the image. ENGINES at the TOP of the image (rear of "
    "ship). COCKPIT/CANOPY visible on the upper body. Single isolated "
    "ship on pure black background. "
    "Sharp clean pixel edges, no anti-aliasing, no gradients, limited "
    "palette (max 8 colors), Metal Slug aesthetic. "
    "Character: {FILL}. "
)


BASE_DIR = PROJECT_ROOT / "Assets" / "sprites" / "redesign" / "_base"
MANIFEST_PATH = PROJECT_ROOT / "tools" / "redesign_ships" / "manifest.json"


def build_prompt(spec: ShipSpec) -> str:
    return PROMPT_TEMPLATE.format(FILL=spec.prompt_fill)


def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {"bases": {}}


def save_manifest(m: dict) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(m, indent=2), encoding="utf-8")


def generate_one(spec: ShipSpec, manifest: dict) -> None:
    out_path = BASE_DIR / f"{spec.key}_base.png"
    if out_path.exists():
        print(f"[skip] {spec.key}: {out_path} already exists")
        return
    print(f"[gen ] {spec.key} ({spec.display_name})")
    prompt = build_prompt(spec)
    node_id = generate_ship_base(prompt=prompt, output_file=str(out_path))
    print(f"        node_id={node_id}, downloading...")
    download_node(node_id, str(out_path))
    manifest["bases"][spec.key] = {
        "node_id": node_id,
        "prompt": prompt,
        "template": spec.template,
        "display_name": spec.display_name,
        "out_path": str(out_path),
        "size_bytes": out_path.stat().st_size,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    save_manifest(manifest)
    print(f"        saved: {out_path} ({out_path.stat().st_size} bytes)")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ship", help="Regenerate only this ship key")
    args = parser.parse_args()
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()
    targets = SHIPS if not args.ship else [s for s in SHIPS if s.key == args.ship]
    if args.ship and not targets:
        print(f"unknown ship: {args.ship}")
        return 1
    for spec in targets:
        generate_one(spec, manifest)
    print(f"\nDone. {len(targets)} base(s) processed. Manifest: {MANIFEST_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
