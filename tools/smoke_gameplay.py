"""Render gameplay state for 5 seconds with auto-fire to test wiring."""
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, ".")
import pygame
from src.core.game import Game
from src.core.scene_manager import GameState

pygame.init()
g = Game()
# Force transition to gameplay (must go through ACT_INTRO first)
g.scenes.transition_to(GameState.ACT_INTRO)
g.scenes.transition_to(GameState.GAMEPLAY)
# Force the runtime to do its thing
g.scenes.scenes[GameState.GAMEPLAY].on_enter()

# Simulate 5 seconds at 60 FPS with constant fire input + lateral sway
for frame in range(600):  # 10 sec — give enough time for kills
    # Inject fake input
    scene = g.scenes.scenes[GameState.GAMEPLAY]
    if hasattr(scene, "_rt"):
        rt = scene._rt
        # Monkey-patch _read_input to use our test inputs
        rt._read_input = lambda: None
        # Smart aiming: track nearest enemy x
        enemies = [e for e in rt._enemies.pool if e.active]
        if enemies:
            # Pick nearest enemy by x distance
            target = min(enemies, key=lambda e: abs(e.x - rt._player.x))
            if target.x < rt._player.x - 4:
                rt._player.input_left = True
                rt._player.input_right = False
            elif target.x > rt._player.x + 4:
                rt._player.input_left = False
                rt._player.input_right = True
            else:
                rt._player.input_left = False
                rt._player.input_right = False
        else:
            rt._player.input_left = False
            rt._player.input_right = False
        rt._player.input_fire = True
        # Update at fixed 120 FPS
        rt.update(1.0 / 120.0)
    # Snapshot every 30 frames
    if frame % 30 == 0:
        g.internal.fill((0, 0, 0))
        if hasattr(scene, "_rt"):
            scene._rt.draw(g.internal)
        pygame.image.save(g.internal, f"tools/playtest_out/gameplay_t{frame:04d}.png")
        # Print stats
        rt = scene._rt
        enemies = sum(1 for e in rt._enemies.pool if e.active)
        bullets = sum(1 for b in rt._bullets.pool if b.active)
        score = rt._scoring.score
        print(f"t={frame/60:.1f}s  player=({rt._player.x:.0f},{rt._player.y:.0f})  "
              f"enemies={enemies}  bullets={bullets}  score={score}  "
              f"kills={rt._wave_mgr.current.kills}")

# Now test boss fight
print("\n=== BOSS FIGHT ===")
# Use boss scene directly
g.scenes.transition_to(GameState.BOSS_INTRO)
g.scenes.transition_to(GameState.BOSS_FIGHT)
g.scenes.scenes[GameState.BOSS_FIGHT].on_enter()
for frame in range(180):  # 3 sec
    scene = g.scenes.scenes[GameState.BOSS_FIGHT]
    if hasattr(scene, "_rt"):
        rt = scene._rt
        rt._read_input = lambda: None
        rt._player.input_fire = True
        rt.update(1.0 / 120.0)
    if frame % 30 == 0:
        g.internal.fill((0, 0, 0))
        if hasattr(scene, "_rt"):
            scene._rt.draw(g.internal)
        pygame.image.save(g.internal, f"tools/playtest_out/boss_t{frame:04d}.png")
        rt = scene._rt
        boss = rt._boss
        boss_hp = boss.hp if boss else 0
        boss_max = boss.max_hp if boss else 0
        bullets = sum(1 for b in rt._bullets.pool if b.active)
        print(f"boss_t={frame/60:.1f}s  boss_hp={boss_hp}/{boss_max}  bullets={bullets}")

print("Done.")
