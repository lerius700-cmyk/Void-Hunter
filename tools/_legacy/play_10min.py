"""10-minute full playthrough (BLOQUE 17.5).

Runs the game headless for 10 minutes of game time, simulating inputs that
actually try to win (smart aiming, periodic dashes, bomb on crowd).
Tracks everything: kills, deaths, bombs, scores, state transitions,
FPS, anomalies. Writes a report at the end.

This is the "did I really make a working game" check.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pygame  # noqa: E402
from src.core.game import Game  # noqa: E402
from src.core.scene_manager import GameState  # noqa: E402


def find_nearest_enemy(rt, include_boss=True):
    """Return nearest enemy or boss by x distance to player."""
    px, py = rt._player.x, rt._player.y
    candidates = []
    for e in rt._enemies.pool:
        if e.active and e.state.name != "DEAD":
            candidates.append((abs(e.x - px), e.x, e.y, "e"))
    if include_boss and rt._boss is not None and rt._boss.active:
        candidates.append((abs(rt._boss.x - px), rt._boss.x, rt._boss.y, "b"))
    if not candidates:
        return None
    return min(candidates, key=lambda c: c[0])


def find_dodge_direction(rt):
    """If an enemy bullet is heading toward the player, return 'left'/'right' to dodge.

    Looks ahead in time: predicts where the bullet will be in 0.2-0.4s and
    checks if the player is in the danger zone. Wider window than naive
    approach.
    """
    px, py = rt._player.x, rt._player.y
    for p in rt._bullets.pool:
        if not p.active or p.owner not in (1, 2):  # OWNER_ENEMY=1, OWNER_BOSS=2
            continue
        # Predict position in 0.2s and 0.4s
        for predict_t in (0.15, 0.30, 0.45):
            fut_x = p.x + p.vx * predict_t
            fut_y = p.y + p.vy * predict_t
            if abs(fut_x - px) < 12 and abs(fut_y - py) < 12:
                # Bullet will be near us; dodge perpendicular to its direction
                if p.vx != 0 or p.vy != 0:
                    if abs(p.vx) > abs(p.vy):
                        return "up" if p.vy < 0 else "down"
                    return "left" if p.vx > 0 else "right"
    return None


def should_use_bomb(rt):
    """Bomb if: low HP, many enemies on screen, or many bullets near."""
    if rt._player.bombs <= 0:
        return False
    # Low HP
    if rt._player.hp <= 1 and rt._player.lives <= 1:
        return True
    # 3+ enemies on screen and player took damage recently
    live = sum(1 for e in rt._enemies.pool if e.active and e.state.name != "DEAD")
    if live >= 4 and rt._player.hp <= 2:
        return True
    # 3+ bullets in danger zone
    danger_bullets = 0
    for p in rt._bullets.pool:
        if p.active and p.owner in (1, 2):
            if abs(p.x - rt._player.x) < 50 and abs(p.y - rt._player.y) < 50:
                danger_bullets += 1
    if danger_bullets >= 3:
        return True
    return False


def main() -> int:
    out_dir = ROOT / "tools" / "playtest_out" / "10min"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[10min] starting full playthrough")
    pygame.init()
    game = Game()
    # Force into ACT_INTRO then GAMEPLAY to start
    game.scenes.transition_to(GameState.ACT_INTRO)
    game.scenes.transition_to(GameState.GAMEPLAY)
    game.scenes.scenes[GameState.GAMEPLAY].on_enter()

    # Stats
    stats = {
        "frames": 0,
        "game_time_s": 0.0,
        "wall_time_s": 0.0,
        "kills": 0,
        "deaths": 0,
        "bombs_used": 0,
        "score": 0,
        "max_multiplier": 0,
        "bullets_fired": 0,
        "bosses_killed": 0,
        "waves_cleared": 0,
        "state_transitions": [],
        "anomalies": [],
    }
    last_state = game.scenes.current_state
    t0 = time.perf_counter()
    target_frames = 120 * 600  # 10 min at 120 FPS = 72000 frames
    last_dash = -10.0
    last_bomb = -10.0
    last_kill_count = 0

    for frame in range(target_frames):
        game_time = frame / 120.0
        stats["frames"] = frame + 1
        stats["game_time_s"] = game_time

        scene = game.scenes.scenes.get(game.scenes.current_state)
        # Handle non-gameplay scenes: skip if we ever leave gameplay
        if scene is None or not hasattr(scene, "_rt"):
            # Tick any menu timer
            if scene is not None:
                scene.update(1.0 / 120.0)
            # Auto-advance through menu scenes
            cs = game.scenes.current_state
            if cs in (GameState.ACT_INTRO, GameState.BOSS_INTRO, GameState.ACT_CLEARED):
                # Wait briefly then auto-transition
                if not hasattr(scene, "_t"):
                    continue
                if scene._t < 0.5:  # Let any animations play
                    continue
            if cs == GameState.ACT_CLEARED:
                game.scenes.transition_to(GameState.ACT_INTRO)
                game.scenes.transition_to(GameState.GAMEPLAY)
                game.scenes.scenes[GameState.GAMEPLAY].on_enter()
                stats["state_transitions"].append((game_time, "ACT_CLEARED -> ACT_INTRO -> GAMEPLAY"))
                continue
            elif cs == GameState.GAME_OVER:
                stats["state_transitions"].append((game_time, "GAME_OVER (died!)"))
                # Restart
                game = Game()
                game.scenes.transition_to(GameState.ACT_INTRO)
                game.scenes.transition_to(GameState.GAMEPLAY)
                game.scenes.scenes[GameState.GAMEPLAY].on_enter()
                last_state = game.scenes.current_state
                stats["deaths"] += 1
                continue
            elif cs == GameState.VICTORY:
                stats["state_transitions"].append((game_time, "VICTORY!"))
                stats["bosses_killed"] += 1
                break
            continue

        rt = scene._rt
        # Skip _read_input
        rt._read_input = lambda: None
        # Dodge check first (overrides aiming)
        dodge = find_dodge_direction(rt)
        if dodge == "left":
            rt._player.input_left = True
            rt._player.input_right = False
        elif dodge == "right":
            rt._player.input_left = False
            rt._player.input_right = True
        else:
            # Smart aim: move toward nearest enemy/boss
            nearest = find_nearest_enemy(rt)
            if nearest is not None:
                _, ex, ey, kind = nearest
                # Only move if misaligned; stop when aligned (for accurate shots)
                if ex < rt._player.x - 6:
                    rt._player.input_left = True
                    rt._player.input_right = False
                elif ex > rt._player.x + 6:
                    rt._player.input_left = False
                    rt._player.input_right = True
                else:
                    # Aligned — don't move so bullets land
                    rt._player.input_left = False
                    rt._player.input_right = False
            else:
                # No targets — stay still
                rt._player.input_left = False
                rt._player.input_right = False
        # Always fire
        rt._player.input_fire = True
        # Dash only when bullet is IMMINENT (very close, very soon)
        imminent = False
        for p in rt._bullets.pool:
            if p.active and p.owner in (1, 2):
                fut_x = p.x + p.vx * 0.1
                fut_y = p.y + p.vy * 0.1
                if abs(fut_x - rt._player.x) < 8 and abs(fut_y - rt._player.y) < 8:
                    imminent = True
                    break
        if imminent and game_time - last_dash > 1.0:
            rt._player.input_dash = True
            last_dash = game_time
        # Bomb when in danger
        if should_use_bomb(rt) and game_time - last_bomb > 2.0:
            rt._player.input_bomb = True
            rt._player.wants_to_bomb = True
            stats["bombs_used"] += 1
            last_bomb = game_time

        # Tick
        rt.update(1.0 / 120.0)
        # Update stats
        stats["score"] = rt._scoring.score
        stats["max_multiplier"] = max(stats["max_multiplier"], rt._scoring.multiplier)
        if rt._player.is_dead:
            stats["deaths"] += 1
        if rt._wave_mgr.current.kills != last_kill_count:
            new_kills = rt._wave_mgr.current.kills - last_kill_count
            stats["kills"] += new_kills
            last_kill_count = rt._wave_mgr.current.kills

        # Watch state transitions
        if game.scenes.current_state != last_state:
            stats["state_transitions"].append(
                (game_time, f"{last_state.value} -> {game.scenes.current_state.value}")
            )
            last_state = game.scenes.current_state
        # Anomalies
        if not (5 <= rt._player.x <= 235) or not (5 <= rt._player.y <= 355):
            stats["anomalies"].append(f"t={game_time:.1f}: player out of bounds ({rt._player.x:.0f},{rt._player.y:.0f})")
        if rt._player.lives < 0:
            stats["anomalies"].append(f"t={game_time:.1f}: lives went negative ({rt._player.lives})")
        if rt._scoring.score < 0:
            stats["anomalies"].append(f"t={game_time:.1f}: score went negative ({rt._scoring.score})")

    stats["wall_time_s"] = time.perf_counter() - t0
    # Write report
    report_path = out_dir / "report.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("VOID HUNTER 10-MIN PLAYTHROUGH REPORT\n")
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
    # Console summary
    print(f"\n[10min] DONE in {stats['wall_time_s']:.1f}s wall time")
    print(f"  frames          : {stats['frames']}")
    print(f"  game time       : {stats['game_time_s']:.1f}s")
    print(f"  kills           : {stats['kills']}")
    print(f"  deaths          : {stats['deaths']}")
    print(f"  bombs used      : {stats['bombs_used']}")
    print(f"  score           : {stats['score']}")
    print(f"  max multiplier  : x{stats['max_multiplier']}")
    print(f"  bosses killed   : {stats['bosses_killed']}")
    print(f"  state changes   : {len(stats['state_transitions'])}")
    print(f"  anomalies       : {len(stats['anomalies'])}")
    print(f"\n  Report: {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
