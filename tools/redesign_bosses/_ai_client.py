"""AI client for boss base generation (BLOQUE 60).

BLOQUE 60 deviation from plan: the plan's re-export
`from tools.redesign_ships._ai_client import generate_image, DEFAULT_MODEL`
could not be applied verbatim because the ship module exposes
`generate_ship_base` and `download_node` (the two-step mcode-tools flow
debated and locked-in during BLOQUE 59), not the `generate_image` /
`DEFAULT_MODEL` names the plan was written against.

To avoid touching the uncommitted `tools/redesign_ships/_ai_client.py`,
we define `generate_image` here as a thin wrapper that combines
`generate_ship_base` + `download_node` into the single-call interface
the boss pipeline expects. The underlying mcode-tools plumbing is
re-used unchanged.
"""
from __future__ import annotations

from tools.redesign_ships._ai_client import download_node, generate_ship_base

# Matrix image connector is the only model we use today; exposed so the
# plan-required `DEFAULT_MODEL` symbol is available for callers/tests.
DEFAULT_MODEL = "connector__matrix__generate_image"


def generate_image(
    prompt: str,
    out_path,
    width: int = 1024,
    height: int = 1024,
) -> str:
    """Generate one 1024x1024 base PNG and save it to `out_path`.

    Returns the mcode-tools `node_id` (also useful for manifest logging).
    `width` and `height` are accepted for signature compatibility with
    future model swaps; today's matrix connector is fixed to 1K square.
    """
    out_path = str(out_path)
    node_id = generate_ship_base(prompt=prompt, output_file=out_path)
    download_node(node_id, out_path)
    return node_id


__all__ = ["generate_image", "DEFAULT_MODEL"]
