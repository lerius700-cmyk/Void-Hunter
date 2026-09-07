"""mcode-tools wrapper for ship base image generation (BLOQUE 59).

Wraps `mcode-tools connector call connector__matrix__generate_image` so the
pipeline can generate 1024x1024 base art for each ship and get back a
`node_id` for downloading.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path


def generate_ship_base(prompt: str, output_file: str) -> str:
    """Call mcode-tools to generate one ship base image.

    Args:
        prompt: Text description of the ship (e.g. "16-bit pixel art,
            small fast scout, cyan and electric blue, single thruster...").
        output_file: Local path where the generated PNG should be saved.
            Used as the `output_file` field in the mcode-tools request.

    Returns:
        The `node_id` from mcode-tools. Pass to `download_node` to fetch bytes.
    """
    args = {
        "requests": [
            {
                "prompt": prompt,
                "aspect_ratio": "1:1",
                "resolution": "1K",
                "output_file": Path(output_file).name,  # mcode-tools ignores dir components
            }
        ]
    }
    cmd = [
        "mcode-tools",
        "connector",
        "call",
        "connector__matrix__generate_image",
        "--args",
        json.dumps(args),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f"mcode-tools failed (exit {result.returncode}): {result.stderr}")
    response = json.loads(result.stdout)
    success_items = response.get("success_items", [])
    if not success_items:
        raise RuntimeError(f"mcode-tools returned no success_items: {result.stdout[:500]}")
    return success_items[0]["node_id"]


def download_node(node_id: str, dest_path: str) -> None:
    """Download a generated asset by node_id to dest_path."""
    # First get the short-lived URL
    cmd = ["mcode-tools", "get_asset_url", node_id]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(f"get_asset_url failed: {result.stderr}")
    data = json.loads(result.stdout)
    url = data["download_url"]
    # Then fetch the URL
    import urllib.request
    urllib.request.urlretrieve(url, dest_path)
