"""Capture the patterns in actual gameplay runtime.

Creates a GameplayRuntime directly, enables patterns, and captures
frames showing the procedural patterns in action. Doesn't go through
the title scene.
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
from src.entities.enemies.enemy import EnemyKind

# Create runtime
rt = GameplayRuntime(transition_to=lambda s: None, is_boss=False, act=1)
rt.on_enter()

# Enable procedural patterns
rt.enable_procedural_patterns(seed=2, floor=5, spawn_interval=1.5)

# Capture frames
out_dir = ROOT / "tools" / "playtest_out"
out_dir.mkdir(parents=True, exist_ok=True)

patterns_seen = []
last_label = ""
frame_count = 0

for tick in range(3000):  # 50 seconds at 60fps
    rt.update(1.0 / 60.0)
    # Check for new pattern
    if rt._active_pattern_kind_label and rt._active_pattern_kind_label != last_label:
        label = rt._active_pattern_kind_label
        patterns_seen.append(label)
        last_label = label
        print(f"  [t={tick/60:.1f}s] NEW PATTERN: {label}")
    # Capture frames: first frame of each new pattern + 1 mid-frame
    if rt._active_pattern_kind_label:
        # Capture the first time we see this label
        if not hasattr(rt, '_captured_for_label') or rt._captured_for_label != last_label:
            surf = pygame.Surface((320, 480))
            surf.fill((8, 8, 20))
            rt.draw(surf)
            out = out_dir / f"in_game_pattern_v1.28_{label.replace(' ', '_')}_start.png"
            pygame.image.save(surf, str(out))
            print(f"  Saved {out.name}")
            rt._captured_for_label = last_label
            frame_count += 1
    # Stop after seeing all 5 patterns
    if len(set(patterns_seen)) >= 5:
        break

print(f"\nPatterns seen: {patterns_seen}")
print(f"Total unique patterns: {len(set(patterns_seen))}")
print(f"Frames captured: {frame_count}")
