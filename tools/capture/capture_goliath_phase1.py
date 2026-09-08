"""Capture GOLIATH phase 1 in the new sprite (BLOQUE 60 verification).

Headless capture that constructs GameplayRuntime in boss mode, switches
the spawned GOLIATH boss to its idle frame, pins it at the screen
anchor, and saves a 320x480 PNG to tools/playtest_out/.

Follows the same dummy-driver + 320x480 set_mode pattern used by
tools/capture/capture_patterns_in_game.py.
"""
from __future__ import annotations
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import pygame
pygame.init()
pygame.display.set_mode((320, 480))

from src.ui.gameplay_runtime import GameplayRuntime
from src.entities.enemies.boss import BOSS_CONFIGS

# Construct with is_boss=True so the GameplayRuntime auto-spawns GOLIATH
# in on_enter() via _spawn_boss_for_act() (act=1 -> BossId.GOLIATH).
rt = GameplayRuntime(transition_to=lambda s: None, is_boss=True, act=1)
rt.on_enter()

# Skip the boss entry pose (slides from y=-50 to anchor over 1.5s). Set
# entry_t past the 1.5s mark so _draw_boss/_update_boss path uses the
# normal sine oscillation + attack selection.
rt._boss_entry_t = 2.0

b = rt._boss
assert b is not None, "expected GOLIATH to be auto-spawned in is_boss mode"
cfg = BOSS_CONFIGS[b.id]

# Pin the boss to its screen anchor so the screenshot is deterministic.
b.x = cfg.anchor_x
b.y = cfg.anchor_y
b.move_t = 0.0

# BLOQUE 60: switch to the idle sprite. The boss spawns in "intro"
# (set by Boss.on_spawn); we want a clean mid-screen shot of "idle".
b.hp = b.max_hp
b.phase = 1
b.animation_state = "idle"
b.animation_frame = 0
b.animation_timer = 0.0

# Save the screenshot.
out = ROOT / "tools" / "playtest_out" / "goliath_phase1_mid.png"
out.parent.mkdir(parents=True, exist_ok=True)
surf = pygame.Surface((320, 480))
surf.fill((8, 8, 20))
rt.draw(surf)
pygame.image.save(surf, str(out))
print(f"saved {out}")
