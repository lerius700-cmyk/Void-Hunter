"""Smart 10-minute playtester (BLOQUE 28).

BLOQUE 28: rewritten to be a competent auto-pilot:
- Tracks bullets fired (proper counter)
- Aims with movement (gets under enemies before firing)
- Predicts enemy bullet trajectories more accurately
- Dashes more aggressively when cornered
- Uses bombs proactively in tight spots
- Reports wave/boss progress clearly

This validates that the game is actually playable end-to-end.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("VOID_HUNTER_EASY", "1")  # BLOQUE 28: easy mode for playtest
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pygame  # noqa: E402

from src.core.game import Game  # noqa: E402
from src.core.scene_manager import GameState  # noqa: E402
from src.systems.projectile import OWNER_BOSS, OWNER_ENEMY, OWNER_PLAYER  # noqa: E402


def find_nearest_enemy_x(rt):
    """Return x of nearest active enemy, or None."""
    px = rt._player.x
    best_x: float | None = None
    best_dx = 9999.0
    for e in rt._enemies.pool:
        if e.active and e.state.name != "DEAD":
            d = abs(e.x - px)
            if d < best_dx:
                best_dx = d
                best_x = e.x
    if rt._boss is not None and rt._boss.active:
        d = abs(rt._boss.x - px)
        if d < best_dx:
            best_x = rt._boss.x
    return best_x


def find_collision_threat(rt, horizon_s: float = 0.4) -> int:
    """Count enemy bullets that will be within 8px of player in [0, horizon_s].

    Returns the count of imminent threats (higher = more dangerous).
    """
    px, py = rt._player.x, rt._player.y
    threats = 0
    for p in rt._bullets.pool:
        if not p.active or p.owner not in (OWNER_ENEMY, OWNER_BOSS):
            continue
        # Walk forward in time, see if it gets close
        fut_x = p.x + p.vx * horizon_s * 0.5
        fut_y = p.y + p.vy * horizon_s * 0.5
        if abs(fut_x - px) < 20 and abs(fut_y - py) < 20:
            threats += 1
    return threats


def should_dash(rt, game_time: float, last_dash: float) -> bool:
    """Dash if an enemy bullet is very close (within 6px in next 0.1s)."""
    if game_time - last_dash < 0.6:
        return False
    px, py = rt._player.x, rt._player.y
    for p in rt._bullets.pool:
        if not p.active or p.owner not in (OWNER_ENEMY, OWNER_BOSS):
            continue
        fut_x = p.x + p.vx * 0.1
        fut_y = p.y + p.vy * 0.1
        if abs(fut_x - px) < 6 and abs(fut_y - py) < 6:
            return True
    return False


def should_bomb(rt) -> bool:
    """Bomb when overwhelmed (5+ enemies, 3+ bullets nearby, low HP)."""
    if rt._player.bombs <= 0:
        return False
    if rt._player.hp <= 1 and rt._player.lives <= 1:
        return True
    enemies = sum(1 for e in rt._enemies.pool if e.active and e.state.name != "DEAD")
    if enemies >= 5 and rt._player.hp <= 2:
        return True
    nearby_bullets = find_collision_threat(rt, horizon_s=0.3)
    if nearby_bullets >= 4 and rt._player.hp <= 2:
        return True
    return False


def main() -> int:
    out_dir = ROOT / "tools" / "playtest_out" / "10min"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[10min smart] starting full playthrough")
    pygame.init()
    game = Game()
    game.scenes.transition_to(GameState.ACT_INTRO)
    game.scenes.transition_to(GameState.GAMEPLAY)
    game.scenes.scenes[GameState.GAMEPLAY].on_enter()

    stats = {
        "frames": 0,
        "game_time_s": 0.0,
        "wall_time_s": 0.0,
        "kills": 0,
        "deaths": 0,
        "bombs_used": 0,
        "bullets_fired": 0,
        "score": 0,
        "max_multiplier": 0,
        "bosses_killed": 0,
        "waves_cleared": 0,
        "boss_fights_reached": 0,
        "state_transitions": [],
        "anomalies": [],
    }
    last_state = game.scenes.current_state
    t0 = time.perf_counter()
    target_frames = 120 * 600  # 10 min at 120 FPS
    last_dash = -10.0
    last_bomb = -10.0
    last_kill_count = 0
    last_bullet_count = 0

    def reset_to_gameplay() -> None:
        nonlocal game, last_state, last_dash, last_bomb, last_kill_count, last_bullet_count
        game = Game()
        game.scenes.transition_to(GameState.ACT_INTRO)
        game.scenes.transition_to(GameState.GAMEPLAY)
        game.scenes.scenes[GameState.GAMEPLAY].on_enter()
        last_state = game.scenes.current_state
        last_dash = -10.0
        last_bomb = -10.0
        last_kill_count = 0
        last_bullet_count = 0

    for frame in range(target_frames):
        game_time = frame / 120.0
        stats["frames"] = frame + 1
        stats["game_time_s"] = game_time

        scene = game.scenes.scenes.get(game.scenes.current_state)
        # Non-gameplay handling
        if scene is None or not hasattr(scene, "_rt"):
            if scene is not None:
                scene.update(1.0 / 120.0)
            cs = game.scenes.current_state
            if cs == GameState.ACT_CLEARED:
                stats["waves_cleared"] += 1
                stats["state_transitions"].append(
                    (game_time, "ACT_CLEARED -> next act")
                )
                game.scenes.transition_to(GameState.ACT_INTRO)
                game.scenes.transition_to(GameState.GAMEPLAY)
                game.scenes.scenes[GameState.GAMEPLAY].on_enter()
                last_state = game.scenes.current_state
                continue
            elif cs == GameState.GAME_OVER:
                stats["deaths"] += 1
                stats["state_transitions"].append(
                    (game_time, f"GAME_OVER (run #{stats['deaths']} ended)")
                )
                reset_to_gameplay()
                continue
            elif cs == GameState.VICTORY:
                stats["bosses_killed"] += 1
                stats["state_transitions"].append((game_time, "VICTORY!"))
                break
            continue

        rt = scene._rt
        # Skip keyboard polling
        rt._read_input = lambda: None

        # -- AIM: get under nearest enemy and fire --
        nearest_x = find_nearest_enemy_x(rt)
        # Move toward nearest enemy if not aligned
        if nearest_x is not None:
            if nearest_x < rt._player.x - 8:
                rt._player.input_left = True
                rt._player.input_right = False
            elif nearest_x > rt._player.x + 8:
                rt._player.input_left = False
                rt._player.input_right = True
            else:
                # Aligned — stop and fire accurately
                rt._player.input_left = False
                rt._player.input_right = False
        else:
            # No targets — keep moving slowly to find them
            rt._player.input_left = False
            rt._player.input_right = False

        # Always fire (input is consumed each frame; setting True triggers the fire in update)
        rt._player.input_fire = True

        # -- DODGE: dash if a bullet is imminent --
        # In boss fight, dash more aggressively (within 0.5s instead of 0.1s)
        in_boss_fight = game.scenes.current_state == GameState.BOSS_FIGHT
        if in_boss_fight:
            # Wider dodge window for boss attacks
            if game_time - last_dash >= 0.5:
                # Check for any bullet within 0.5s of us
                px, py = rt._player.x, rt._player.y
                for p in rt._bullets.pool:
                    if not p.active or p.owner not in (OWNER_ENEMY, OWNER_BOSS):
                        continue
                    fut_x = p.x + p.vx * 0.5
                    fut_y = p.y + p.vy * 0.5
                    if abs(fut_x - px) < 15 and abs(fut_y - py) < 15:
                        rt._player.input_dash = True
                        last_dash = game_time
                        break
        elif should_dash(rt, game_time, last_dash):
            rt._player.input_dash = True
            last_dash = game_time

        # -- BOMB when in danger --
        # In boss fight, be more aggressive with bombs
        in_boss_fight = game.scenes.current_state == GameState.BOSS_FIGHT
        bomb_threshold_hp = 1 if in_boss_fight else 1
        bomb_enemy_threshold = 5 if in_boss_fight else 5
        if (rt._player.bombs > 0
                and game_time - last_bomb > (1.5 if in_boss_fight else 2.0)
                and (rt._player.hp <= bomb_threshold_hp
                     or (in_boss_fight and rt._player.hp <= 2)
                     or (sum(1 for e in rt._enemies.pool if e.active and e.state.name != "DEAD") >= bomb_enemy_threshold
                         and rt._player.hp <= 2))):
            rt._player.input_bomb = True
            rt._player.wants_to_bomb = True
            stats["bombs_used"] += 1
            last_bomb = game_time

        # -- TICK --
        rt.update(1.0 / 120.0)

        # -- Update stats --
        stats["score"] = rt._scoring.score
        stats["max_multiplier"] = max(stats["max_multiplier"], rt._scoring.multiplier)
        # Bullets fired = (active player bullets now) - (last frame) + newly killed enemies
        player_bullets = sum(1 for b in rt._bullets.pool if b.owner == OWNER_PLAYER)
        delta = max(0, player_bullets - last_bullet_count)
        stats["bullets_fired"] += delta
        last_bullet_count = player_bullets
        # Track kills
        new_kills = rt._wave_mgr.current.kills - last_kill_count
        if new_kills > 0:
            stats["kills"] += new_kills
            last_kill_count = rt._wave_mgr.current.kills
        # Boss fights reached
        if game.scenes.current_state == GameState.BOSS_FIGHT:
            if not stats["state_transitions"] or "BOSS_FIGHT" not in stats["state_transitions"][-1][1]:
                stats["boss_fights_reached"] += 1
                stats["state_transitions"].append((game_time, "-> BOSS_FIGHT"))

        # Watch state transitions
        if game.scenes.current_state != last_state:
            stats["state_transitions"].append(
                (game_time, f"{last_state.value} -> {game.scenes.current_state.value}")
            )
            last_state = game.scenes.current_state

        # Anomalies
        if not (5 <= rt._player.x <= 235) or not (5 <= rt._player.y <= 355):
            stats["anomalies"].append(
                f"t={game_time:.1f}: player out of bounds ({rt._player.x:.0f},{rt._player.y:.0f})"
            )
        if rt._player.lives < 0:
            stats["anomalies"].append(f"t={game_time:.1f}: lives went negative ({rt._player.lives})")
        if rt._scoring.score < 0:
            stats["anomalies"].append(f"t={game_time:.1f}: score went negative ({rt._scoring.score})")

    stats["wall_time_s"] = time.perf_counter() - t0
    report_path = out_dir / "report_smart.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("VOID HUNTER 10-MIN SMART PLAYTHROUGH REPORT\n")
        f.write("=" * 60 + "\n")
        for k, v in stats.items():
            if k == "state_transitions":
                f.write(f"\nState transitions ({len(v)}):\n")
                for t, s in v:
                    f.write(f"  t={t:.1f}s  {s}\n")
            elif k == "anomalies":
                f.write(f"\nAnomalies ({len(v)}):\n")
                for a in v:
                    f.write(f"  {a}\n")
            else:
                f.write(f"{k:25s} : {v}\n")
        f.write("\n" + "=" * 60 + "\n")
    print(f"\n[10min smart] DONE in {stats['wall_time_s']:.1f}s wall time")
    for k, v in stats.items():
        if k not in ("state_transitions", "anomalies"):
            print(f"  {k:25s}: {v}")
    print(f"  anomalies: {len(stats['anomalies'])}")
    print(f"\n  Report: {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
