"""Capture the OSCILLATING_BUTTERFLY pattern in v1.1."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import sys
from pathlib import Path
ROOT = Path(".").resolve()
sys.path.insert(0, str(ROOT))
import pygame
pygame.init()
pygame.display.set_mode((320, 480))
from src.ui.gameplay_runtime import GameplayRuntime
rt = GameplayRuntime(transition_to=lambda s: None, is_boss=False, act=1)
rt.on_enter()
rt.enable_procedural_patterns(seed=1, floor=1, spawn_interval=0.5)
out_dir = ROOT / "tools" / "playtest_out"
captured_for = set()
last = ""
for tick in range(7200):  # 120s
    rt.update(1.0/60.0)
    if rt._active_pattern_kind_label and rt._active_pattern_kind_label != last:
        last = rt._active_pattern_kind_label
        if last not in captured_for:
            surf = pygame.Surface((320, 480))
            surf.fill((8, 8, 20))
            rt.draw(surf)
            safe = last.replace(" ", "_")
            out = out_dir / f"v1.28_{safe}_v1.1_mid.png"
            pygame.image.save(surf, str(out))
            print(f"Saved {out.name}")
            captured_for.add(last)
    if len(captured_for) >= 6:
        break
print(f"Captured: {captured_for}")
