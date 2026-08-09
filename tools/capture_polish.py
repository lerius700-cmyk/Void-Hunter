"""Capture polished-state frames for BLOQUE 22 visual verification.

Renders a single frame with each polish effect forced active so we can confirm:
  1. Muzzle flash on player
  2. Charge release flash (yellow full-screen overlay)
  3. Boss death multi-stage explosion
  4. Bomb screen flash
  5. Shockwave ring
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Headless before pygame import
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pygame  # noqa: E402

from src.core.settings import INTERNAL_H, INTERNAL_W  # noqa: E402
from src.core.scene_manager import GameState  # noqa: E402
from src.entities.enemies import EnemyKind  # noqa: E402
from src.ui.gameplay_runtime import GameplayRuntime  # noqa: E402


def _noop(_state: GameState) -> None:
    pass


def main() -> None:
    pygame.init()
    out_dir = ROOT / "tools" / "playtest_out"
    out_dir.mkdir(parents=True, exist_ok=True)
    surf = pygame.Surface((INTERNAL_W, INTERNAL_H))

    # 1. Idle frame (no polish)
    rt = GameplayRuntime(transition_to=_noop, is_boss=False, act=1)
    rt.on_enter()
    rt._player.x, rt._player.y = INTERNAL_W / 2, INTERNAL_H - 60
    rt.draw(surf)
    pygame.image.save(surf, str(out_dir / "polish_01_idle.png"))
    print("saved polish_01_idle.png")

    # 2. Muzzle flash (player just fired)
    rt._muzzle_flash = 1.0
    # Spawn a player bullet for visual context
    rt._bullets.spawn(
        0,  # BULLET_PLAYER
        rt._player.x, rt._player.y - 12, 0.0, -480.0,
        damage=1, owner=1,  # OWNER_PLAYER
    )
    rt.draw(surf)
    pygame.image.save(surf, str(out_dir / "polish_02_muzzle_flash.png"))
    print("saved polish_02_muzzle_flash.png")

    # 3. Charge release flash (yellow full-screen)
    rt2 = GameplayRuntime(transition_to=_noop, is_boss=False, act=1)
    rt2.on_enter()
    rt2._charge_release_flash = 0.6
    rt2._add_shockwave(rt2._player.x, rt2._player.y, 30.0)
    rt2.draw(surf)
    pygame.image.save(surf, str(out_dir / "polish_03_charge_release.png"))
    print("saved polish_03_charge_release.png")

    # 4. Bomb screen flash
    rt3 = GameplayRuntime(transition_to=_noop, is_boss=False, act=1)
    rt3.on_enter()
    rt3._screen_flash = 0.9
    rt3._add_shockwave(rt3._player.x, rt3._player.y, 60.0)
    rt3.draw(surf)
    pygame.image.save(surf, str(out_dir / "polish_04_bomb_flash.png"))
    print("saved polish_04_bomb_flash.png")

    # 5. Boss death multi-stage explosion (mid-stage 1)
    rt4 = GameplayRuntime(transition_to=_noop, is_boss=True, act=1)
    rt4.on_enter()
    rt4._on_boss_killed()
    # Step a few frames so stage 1 is established and shockwave expanded
    for _ in range(6):
        rt4.update(1.0 / 60)
    rt4.draw(surf)
    pygame.image.save(surf, str(out_dir / "polish_05_boss_death.png"))
    print("saved polish_05_boss_death.png")

    # 5b. Boss entry warning border (pulsing red)
    rt4b = GameplayRuntime(transition_to=_noop, is_boss=True, act=1)
    rt4b.on_enter()
    rt4b._boss_entry_t = 0.4  # mid-entry
    rt4b.draw(surf)
    pygame.image.save(surf, str(out_dir / "polish_05b_boss_entry_warning.png"))
    print("saved polish_05b_boss_entry_warning.png")

    # 5c. Power-up pulse halo
    rt4c = GameplayRuntime(transition_to=_noop, is_boss=False, act=1)
    rt4c.on_enter()
    rt4c._spawn_powerup("bomb", INTERNAL_W / 2, INTERNAL_H / 2)
    rt4c._spawn_powerup("1up", INTERNAL_W / 2 + 30, INTERNAL_H / 2)
    rt4c._spawn_powerup("score", INTERNAL_W / 2 - 30, INTERNAL_H / 2)
    rt4c.draw(surf)
    pygame.image.save(surf, str(out_dir / "polish_05c_powerup_pulse.png"))
    print("saved polish_05c_powerup_pulse.png")

    # 6. Bullets with bigger glow
    rt5 = GameplayRuntime(transition_to=_noop, is_boss=False, act=1)
    rt5.on_enter()
    # Spawn a vertical fan of player bullets
    for dx in (-6, 0, 6):
        rt5._bullets.spawn(
            0, INTERNAL_W / 2 + dx, INTERNAL_H - 100, 0.0, -480.0,
            damage=1, owner=1,
        )
    # And a couple of enemy bullets going up
    for dx in (-20, 20):
        rt5._bullets.spawn(
            1, INTERNAL_W / 2 + dx, 80, dx * 0.5, 200.0,
            damage=1, owner=2,  # OWNER_ENEMY
        )
    rt5.draw(surf)
    pygame.image.save(surf, str(out_dir / "polish_06_bullets_glow.png"))
    print("saved polish_06_bullets_glow.png")

    # 7. BLOQUE 24: pickup flash (green overlay)
    rt7 = GameplayRuntime(transition_to=_noop, is_boss=False, act=1)
    rt7.on_enter()
    rt7._pickup_flash = 0.5
    rt7.draw(surf)
    pygame.image.save(surf, str(out_dir / "polish_07_pickup_flash.png"))
    print("saved polish_07_pickup_flash.png")

    # 8. BLOQUE 24: level-up flash (cyan overlay)
    rt8 = GameplayRuntime(transition_to=_noop, is_boss=False, act=1)
    rt8.on_enter()
    rt8._level_up_flash = 0.6
    rt8.draw(surf)
    pygame.image.save(surf, str(out_dir / "polish_08_levelup_flash.png"))
    print("saved polish_08_levelup_flash.png")

    # 9. BLOQUE 24: speed lines (player moving fast)
    rt9 = GameplayRuntime(transition_to=_noop, is_boss=False, act=1)
    rt9.on_enter()
    rt9._player.x = INTERNAL_W / 2
    rt9._player.y = INTERNAL_H - 60
    rt9._player.vx = 200.0
    rt9._speed_line_t = 1.5
    rt9.draw(surf)
    pygame.image.save(surf, str(out_dir / "polish_09_speed_lines.png"))
    print("saved polish_09_speed_lines.png")

    # 10. BLOQUE 25: shield effect (respawn invuln)
    rt10 = GameplayRuntime(transition_to=_noop, is_boss=False, act=1)
    rt10.on_enter()
    rt10._player.x = INTERNAL_W / 2
    rt10._player.y = INTERNAL_H - 60
    rt10._player.respawn_invuln = 1.0
    rt10._t = 0.5
    rt10.draw(surf)
    pygame.image.save(surf, str(out_dir / "polish_10_shield.png"))
    print("saved polish_10_shield.png")

    # 11. BLOQUE 25: low HP (animated red pulse)
    rt11 = GameplayRuntime(transition_to=_noop, is_boss=False, act=1)
    rt11.on_enter()
    rt11._player.hp = 1
    rt11._t = 0.5
    rt11.draw(surf)
    pygame.image.save(surf, str(out_dir / "polish_11_low_hp.png"))
    print("saved polish_11_low_hp.png")

    # 12. BLOQUE 25: HUD with high weapon level
    rt12 = GameplayRuntime(transition_to=_noop, is_boss=False, act=1)
    rt12.on_enter()
    rt12._weapon.level = rt12._weapon.level.__class__.L3  # type: ignore[attr-defined]
    rt12._weapon.xp = 50
    rt12._t = 0.5
    rt12.draw(surf)
    pygame.image.save(surf, str(out_dir / "polish_12_hud_high_level.png"))
    print("saved polish_12_hud_high_level.png")

    # 13. BLOQUE 26: engine smoke + bomb flash
    rt13 = GameplayRuntime(transition_to=_noop, is_boss=False, act=1)
    rt13.on_enter()
    rt13._player.x = INTERNAL_W / 2
    rt13._player.y = INTERNAL_H - 60
    rt13._player.vx = 80.0
    # Advance a few frames to spawn smoke
    for _ in range(20):
        rt13.update(1.0 / 60)
    rt13.draw(surf)
    pygame.image.save(surf, str(out_dir / "polish_13_engine_smoke.png"))
    print("saved polish_13_engine_smoke.png")

    # 14. BLOQUE 26: dash stars + dash smoke
    rt14 = GameplayRuntime(transition_to=_noop, is_boss=False, act=1)
    rt14.on_enter()
    rt14._player.x = INTERNAL_W / 2
    rt14._player.y = INTERNAL_H / 2
    rt14._player.state = rt14._player.state.__class__.DASH  # type: ignore[attr-defined]
    rt14._player.dash_dir_x = 1.0
    rt14._player.dash_dir_y = 0.0
    rt14._player.dash_iframes_left = 10
    # Advance a few frames
    for _ in range(5):
        rt14.update(1.0 / 60)
    rt14.draw(surf)
    pygame.image.save(surf, str(out_dir / "polish_14_dash_stars.png"))
    print("saved polish_14_dash_stars.png")

    # 15. BLOQUE 26: bomb flash overlay
    rt15 = GameplayRuntime(transition_to=_noop, is_boss=False, act=1)
    rt15.on_enter()
    rt15._bomb_flash = 0.8
    rt15._screen_flash = 0.5
    rt15.draw(surf)
    pygame.image.save(surf, str(out_dir / "polish_15_bomb_flash.png"))
    print("saved polish_15_bomb_flash.png")

    # 16. BLOQUE 26: kill counter + low HP smoke
    rt16 = GameplayRuntime(transition_to=_noop, is_boss=False, act=1)
    rt16.on_enter()
    rt16._scoring.kills = 42
    rt16._player.hp = 1
    rt16._t = 1.0
    # Advance frames for damage smoke
    for _ in range(15):
        rt16.update(1.0 / 60)
    rt16.draw(surf)
    pygame.image.save(surf, str(out_dir / "polish_16_kill_counter.png"))
    print("saved polish_16_kill_counter.png")

    # 17. BLOQUE 30: Star Fox-style player ship (rotated 30° right)
    rt17 = GameplayRuntime(transition_to=_noop, is_boss=False, act=1)
    rt17.on_enter()
    rt17._player.x = INTERNAL_W / 2
    rt17._player.y = INTERNAL_H - 60
    rt17._player.nose_angle = 30.0  # pointing right-up
    rt17._t = 0.5
    rt17._update_nose_angle()
    # Advance smoothing
    for _ in range(20):
        rt17.update(1.0 / 60)
    rt17.draw(surf)
    pygame.image.save(surf, str(out_dir / "polish_17_starfox_player.png"))
    print("saved polish_17_starfox_player.png")

    # 17b. BLOQUE 38: RMB rapid-fire muzzle flash (orange tint)
    rt17b = GameplayRuntime(transition_to=_noop, is_boss=False, act=1)
    rt17b.on_enter()
    rt17b._player.x, rt17b._player.y = INTERNAL_W / 2, INTERNAL_H - 60
    rt17b._player.nose_angle = 0.0
    rt17b._muzzle_flash_source = "rmb"
    rt17b._muzzle_flash = 1.0
    rt17b.draw(surf)
    pygame.image.save(surf, str(out_dir / "polish_17b_rmb_muzzle.png"))
    print("saved polish_17b_rmb_muzzle.png (BLOQUE 38: orange RMB tint)")

    # 18. BLOQUE 37: continuous L3 plasma laser (multi-layer beam from muzzle to edge)
    from src.entities.player.player import PlayerState
    rt18 = GameplayRuntime(transition_to=_noop, is_boss=False, act=1)
    rt18.on_enter()
    rt18._player.x = INTERNAL_W / 2
    rt18._player.y = INTERNAL_H - 80
    rt18._player.nose_angle = 0.0
    rt18._player.state = PlayerState.CHARGE
    rt18._player.charge_time = 1.6
    rt18._mouse_held = True
    # Tick the laser update so endpoint is computed.
    rt18._update_continuous_laser(0.10, current_charge=3)
    # Now draw (laser draws after the player in draw()).
    rt18.draw(surf)
    pygame.image.save(surf, str(out_dir / "polish_18_charged_beam.png"))
    print("saved polish_18_charged_beam.png (BLOQUE 37: continuous laser)")

    # 19. BLOQUE 30: Star Fox-style enemy ships
    rt19 = GameplayRuntime(transition_to=_noop, is_boss=False, act=1)
    rt19.on_enter()
    from src.entities.enemies import EnemyKind
    # Spawn 3 different enemy types
    e1 = rt19._enemies.spawn(EnemyKind.SCOUT, 60, 100)
    e2 = rt19._enemies.spawn(EnemyKind.CRUISER, INTERNAL_W / 2, 100)
    e3 = rt19._enemies.spawn(EnemyKind.HEAVY, INTERNAL_W - 60, 100)
    rt19.draw(surf)
    pygame.image.save(surf, str(out_dir / "polish_19_starfox_enemies.png"))
    print("saved polish_19_starfox_enemies.png")

    print("Done. Saved 19 frames in tools/playtest_out/")
    pygame.quit()


if __name__ == "__main__":
    main()
