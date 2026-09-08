"""Capture GOLIATH phase 2 (cracked armor, eye trail, eye laser).

Headless capture that constructs GameplayRuntime in boss mode, forces
the spawned GOLIATH into phase 2, seeds the eye-trail ring buffer with
8 fading positions, arms the eye-laser cooldown, ticks once so the
laser spawns, and saves a 320x480 PNG to tools/playtest_out/.

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

# Construct with is_boss=True so the GameplayRuntime auto-spawns GOLIATH.
rt = GameplayRuntime(transition_to=lambda s: None, is_boss=True, act=1)
rt.on_enter()

# Skip the boss entry pose. The eye-laser tick is gated on
# _boss_entry_t >= 0.8, so we jump well past that.
rt._boss_entry_t = 2.0

b = rt._boss
assert b is not None, "expected GOLIATH to be auto-spawned in is_boss mode"
cfg = BOSS_CONFIGS[b.id]

# Pin the boss to its screen anchor.
b.x = cfg.anchor_x
b.y = cfg.anchor_y
b.move_t = 0.0

# Force phase 2 state directly. The boss starts in phase 1 on spawn;
# we drop HP below the 0.66 threshold AND set phase=2 in case the
# runtime's _check_phase isn't called between setup and draw.
b.hp = int(b.max_hp * 0.5)
b.phase = 2
b.animation_state = "phase2"
b.animation_frame = 0
b.animation_timer = 0.0

# Seed the eye-trail ring buffer (capacity 8). The trail draws the
# oldest position first with low alpha and the newest with high alpha;
# we sweep the boss across a small x/y range so the trail is visible
# against the black background.
for i in range(8):
    b.x = cfg.anchor_x - 16 + i * 4
    b.y = cfg.anchor_y + (i - 4)
    b.update_eye_trail()
# Reset the boss to the anchor (the latest trail entry is "where the
# boss is right now"; the rest fan out behind it).
b.x = cfg.anchor_x
b.y = cfg.anchor_y

# Arm the eye-laser cooldown so the next update fires the beam. The
# tick below will decrement the cd to 0 (it was 3.0 on spawn) and spawn
# BULLET_BOSS_LASER via _spawn_boss_attack(9).
b.eye_laser_cd = 1.0 / 60.0  # 1 tick of decrement will trigger it

# One update tick: advances the eye-laser cd, fires the beam, and adds
# the current anchor position to the trail (9th entry, full alpha).
rt.update(1.0 / 60.0)

# Save the screenshot.
out = ROOT / "tools" / "playtest_out" / "goliath_phase2_mid.png"
out.parent.mkdir(parents=True, exist_ok=True)
surf = pygame.Surface((320, 480))
surf.fill((8, 8, 20))
rt.draw(surf)
pygame.image.save(surf, str(out))
print(f"saved {out}")
