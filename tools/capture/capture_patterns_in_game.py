"""Capture the patterns in actual gameplay runtime.

Creates a GameplayRuntime directly, enables patterns, and captures
frames showing the procedural patterns in action. Doesn't go through
the title scene.

BLOQUE 58.10: uses floor=1 (the REAL default) instead of floor=5.
Before this fix, the capture script used floor=5 which masked the
real-world bug: floor 1 only had V_FORMATION + DICE_FIVE_GRID in
the pool. The user reported seeing only 2 patterns in v1.1 because
the .exe uses floor=1.

Captures each pattern at MID-life (when ships are mid-screen and
the leader glow is clearly visible), not at start (ships off-screen).
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

# BLOQUE 58.10: floor=1 is what the .exe uses in production.
rt.enable_procedural_patterns(seed=1, floor=1, spawn_interval=1.0)

# Capture frames
out_dir = ROOT / "tools" / "playtest_out"
out_dir.mkdir(parents=True, exist_ok=True)

# Track: when each pattern starts, schedule a mid-life capture
patterns_seen: list[str] = []
captured_for: set[str] = set()
last_label = ""
max_ticks = 3600  # 60 seconds at 60fps
mid_capture_ticks: dict[str, int] = {}  # pattern_label -> tick to capture mid

for tick in range(max_ticks):
    rt.update(1.0 / 60.0)
    # New pattern started
    if rt._active_pattern_kind_label and rt._active_pattern_kind_label != last_label:
        label = rt._active_pattern_kind_label
        last_label = label
        patterns_seen.append(label)
        print(f"  [t={tick/60:.1f}s] NEW PATTERN: {label}")
        # Schedule a mid-life capture in 1.2s (ships will be mid-screen)
        mid_capture_ticks[label] = tick + 72  # 72 ticks = 1.2s @ 60fps

    # Mid-life capture
    for label, capture_tick in list(mid_capture_ticks.items()):
        if tick >= capture_tick and label not in captured_for:
            surf = pygame.Surface((320, 480))
            surf.fill((8, 8, 20))
            rt.draw(surf)
            safe_label = label.replace(' ', '_')
            out = out_dir / f"in_game_pattern_v1.28_{safe_label}_mid.png"
            pygame.image.save(surf, str(out))
            print(f"  Saved {out.name} (mid-life, t={tick/60:.1f}s)")
            captured_for.add(label)
            del mid_capture_ticks[label]

    # Stop after seeing all 5 patterns
    if len(set(patterns_seen)) >= 5 and len(captured_for) >= 5:
        break

print(f"\nPatterns seen: {patterns_seen}")
print(f"Total unique patterns: {len(set(patterns_seen))}")
print(f"Frames captured (mid): {len(captured_for)}")
if len(set(patterns_seen)) < 5:
    print(f"WARNING: only saw {len(set(patterns_seen))} unique patterns in {max_ticks} ticks")
    sys.exit(1)
