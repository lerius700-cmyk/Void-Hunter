"""BLOQUE 58.7ab: full-flow debug capture for the sub-boss.

Plays the game from O1 through O2, watches for the SUB_BOSS_INTRO
trigger, and captures a frame after the sub-boss spawns.
"""
from __future__ import annotations
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pygame
pygame.init()
pygame.display.set_mode((320, 480))

# Track scene transitions
transitions: list = []


def _track_transition(state):
    transitions.append(state)
    print(f"[transition] -> {state}")


def capture():
    from src.ui.gameplay_runtime import GameplayRuntime
    rt = GameplayRuntime(transition_to=_track_transition, is_boss=False, act=1)
    rt.on_enter()
    print(f"[init] chain.elapsed_s={rt._level1_chain.elapsed_s:.1f} wave_idx={rt._level1_chain.current_wave_idx}")
    print(f"[init] sub_boss_pending={rt._level1_chain.sub_boss_pending} sub_boss_alive={rt._sub_boss_alive}")

    # Kill all enemies every frame so O1 and O2 don't stack up
    def _kill_all_enemies():
        from src.entities.enemies.enemy import EnemyKind
        for e in rt._enemies.pool:
            if e.active and e.kind != EnemyKind.SUB_BOSS:
                rt._level1_chain.kill()
                e.active = False
                rt._enemies.release(e)

    # Run frames until we trigger SUB_BOSS_INTRO or 5400 frames (90s) elapse
    sub_boss_intro_frame = None
    spawn_frame = None
    frame = 0
    max_frames = 5400  # 90 seconds at 60 fps
    while frame < max_frames:
        rt.update(1.0 / 60.0)
        _kill_all_enemies()
        frame += 1
        # Check if we just transitioned
        if transitions and transitions[-1].name == "SUB_BOSS_INTRO" and sub_boss_intro_frame is None:
            sub_boss_intro_frame = frame
            print(f"\n=== SUB_BOSS_INTRO triggered at frame {frame}, chain.elapsed={rt._level1_chain.elapsed_s:.1f}s ===")
            break
        if frame % 120 == 0:
            print(f"  [frame {frame}] chain.elapsed={rt._level1_chain.elapsed_s:.1f}s wave={rt._level1_chain.current_wave_idx} "
                  f"sub_boss_pending={rt._level1_chain.sub_boss_pending} sub_boss_alive={rt._sub_boss_alive}")

    if sub_boss_intro_frame is None:
        print("[ERROR] SUB_BOSS_INTRO did not trigger within 10 seconds")
        return

    # Now we are in SUB_BOSS_INTRO. Simulate the 5s of the intro playing.
    # The runtime isn't in the SUB_BOSS_INTRO scene — we just have the trigger
    # logged. So instead, we manually run the intro by overriding the state.
    # For this test, we just call the scene manually.
    from src.core.scene_manager import GameState
    from src.ui.scenes import SubBossIntroScene
    intro = SubBossIntroScene(transition_to=_track_transition)
    intro.on_enter()
    print(f"\n[playing SUB_BOSS_INTRO for 5s]")
    for _ in range(int(5.0 * 60)):
        intro.update(1.0 / 60.0)
    print(f"[intro done] transitions so far: {[s.name for s in transitions]}")

    # The intro should have transitioned back to GAMEPLAY.
    # Now simulate the gameplay frame that spawns the sub-boss.
    # After the intro, _transition_to(GAMEPLAY) is called, which triggers
    # the GameplayScene.on_enter() to be called.
    # In the real game, the SceneManager handles this. For our test, we
    # manually trigger the resume by calling rt.on_enter() again with
    # sub_boss_pending=True (which the chain still has).
    print(f"\n[before resume] sub_boss_pending={rt._level1_chain.sub_boss_pending} sub_boss_alive={rt._sub_boss_alive}")
    # The transition from SubBossIntroScene to GAMEPLAY calls
    # _cmd_resume or similar in the Game. We need to make the runtime
    # resume. In the real game, this is automatic via SceneManager.
    # For this test, we manually clear the sub_boss_intro_done and re-enter.
    rt._sub_boss_intro_done = False
    rt.on_enter()
    print(f"[after resume] sub_boss_pending={rt._level1_chain.sub_boss_pending} sub_boss_alive={rt._sub_boss_alive}")
    # Tick 1 frame to spawn the sub-boss
    rt.update(1.0 / 60.0)
    print(f"[after 1 tick] sub_boss_alive={rt._sub_boss_alive}")
    # Tick 15 more frames (0.25s) so the sub-boss moves into the screen
    for _ in range(15):
        rt.update(1.0 / 60.0)

    from src.entities.enemies.enemy import EnemyKind
    sub = None
    for e in rt._enemies.pool:
        if e.active and e.kind == EnemyKind.SUB_BOSS:
            sub = e
            break

    if sub is None:
        print("[ERROR] sub-boss is NOT alive 15 frames after resume")
    else:
        print(f"\n[OK] sub-boss at ({sub.x:.1f}, {sub.y:.1f}) alive after 15 frames")

    # Render to surface
    surf = pygame.Surface((320, 480))
    surf.fill((0, 0, 0))
    rt.draw(surf)
    out = ROOT / "tools" / "playtest_out" / "sub_boss_full_flow.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(surf, str(out))
    print(f"Saved {out}")


if __name__ == "__main__":
    capture()
