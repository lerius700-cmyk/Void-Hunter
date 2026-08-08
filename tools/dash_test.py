"""Targeted dash-direction test.

Hypothesis: per GDD line 90, dash with no lateral input defaults to UP.
This test fires K presses at the player in various states and logs the
resulting position deltas to confirm/deny the behavior and surface any
related bugs.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pygame  # noqa: E402

from src.entities.player import Player, PlayerState  # noqa: E402
from src.core.settings import INTERNAL_W, INTERNAL_H  # noqa: E402


def press_dash(player: Player, with_left=False, with_right=False, label=""):
    """Simulate a K press (dash) and observe the direction taken."""
    # Snapshot pre-dash
    pre_x, pre_y = player.x, player.y
    pre_state = player.state
    # Inject input
    player.input_left = with_left
    player.input_right = with_right
    player.input_dash = True
    # Tick 0.18s of physics at 120 FPS
    for _ in range(int(0.18 * 120)):
        player.update(1.0 / 120)
    dx = player.x - pre_x
    dy = player.y - pre_y
    print(f"  {label:30s} pre=({pre_x:5.1f},{pre_y:5.1f}) state={pre_state.value:8s} "
          f"=> post=({player.x:5.1f},{player.y:5.1f}) dx={dx:+5.1f} dy={dy:+5.1f} "
          f"final_state={player.state.value}")
    return dx, dy


def main() -> int:
    print("=== Dash Direction Test ===")
    print("INTERNAL_W x INTERNAL_H =", INTERNAL_W, "x", INTERNAL_H)
    print()
    cases = [
        ("dash no input (default up)",     False, False),
        ("dash with left",                  True, False),
        ("dash with right",                False, True),
        ("dash with both (cancel)",         True,  True),
    ]
    for label, left, right in cases:
        p = Player()
        p.x = INTERNAL_W / 2  # center
        p.y = INTERNAL_H - 60  # spawn row
        # Make sure we're in IDLE so dash is taken
        p._enter_idle()
        press_dash(p, with_left=left, with_right=right, label=label)
    print()
    print("=== Dash-while-moving (no input held) ===")
    # Build up lateral velocity, then dash WITHOUT holding A/D
    for setup_label, setup_frames, post_dir in [
        ("moving left, then dash",   30, -1.0),
        ("moving right, then dash",  30,  1.0),
    ]:
        p = Player()
        p.x = INTERNAL_W / 2
        p.y = INTERNAL_H - 60
        p._enter_idle()
        # Move left or right for setup_frames ticks
        for _ in range(setup_frames):
            p.input_left = (post_dir < 0)
            p.input_right = (post_dir > 0)
            p.update(1.0 / 120)
        # Release input, then dash
        p.input_left = False
        p.input_right = False
        # Capture pre-dash velocity
        pre_vx = p.vx
        press_dash(p, with_left=False, with_right=False, label=f"{setup_label} (pre_vx={pre_vx:.1f})")
    print()
    print("=== Movement while firing test ===")
    print("Player should be able to move laterally while holding J (fire)")
    print()
    p = Player()
    p.x = INTERNAL_W / 2
    p.y = INTERNAL_H - 60
    p._enter_idle()
    initial_x = p.x
    # Simulate 2 seconds of holding A + J at 120 FPS
    for i in range(int(2.0 * 120)):
        p.input_left = True
        p.input_fire = True
        p.update(1.0 / 120)
    print(f"  Hold A+J for 2s: x moved {p.x - initial_x:+.1f} (target ~ -260px at 130 px/s)")
    print(f"  Final state: {p.state.value}")
    print(f"  Final vx: {p.vx:.1f} (target: -130)")
    print(f"  charge_time: {p.charge_time:.2f} (released fire would fire charge L1 at 0.5s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
