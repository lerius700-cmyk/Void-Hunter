"""VOID HUNTER — automated playtester (BLOQUE 17.x).

Runs the game headless with SDL_VIDEODRIVER=dummy, simulates player inputs
over time, captures frames + state snapshots, and logs anomalies.

Use:
    python tools/playtest.py --duration 60 --out tools/playtest_out/
    python tools/playtest.py --scenario boss --duration 30

Scenarios:
  random    — random movement, occasional fire, dashing periodically
  dodge     — stationary, fires constantly, dashes when bullets near
  boss      — focused on a single boss fight scenario
  full      — runs all scenarios sequentially
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path

# Headless: must be set BEFORE importing pygame
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pygame  # noqa: E402

from src.core.game import Game  # noqa: E402
from src.core.scene_manager import GameState  # noqa: E402
from src.entities.player import PlayerState  # noqa: E402
from src.core.settings import INTERNAL_W, INTERNAL_H  # noqa: E402


class Playtester:
    """Drives the Game through simulated inputs + logs results."""

    def __init__(self, out_dir: Path) -> None:
        self.out_dir = out_dir
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.frames_dir = out_dir / "frames"
        self.frames_dir.mkdir(exist_ok=True)
        self.log: list[dict] = []
        self.anomalies: list[str] = []
        self.frame_count = 0
        self.last_player_pos: tuple[float, float] = (0.0, 0.0)
        self.last_state = None
        self.t_last_change = 0.0
        self.bullets_seen = 0
        self.enemies_seen = 0
        self.boss_seen = False

    # ------------------------------------------------------------------
    # Frame capture
    # ------------------------------------------------------------------
    def capture(self, game: Game, t: float) -> None:
        """Save current internal surface as a PNG (downscaled for log size)."""
        self.frame_count += 1
        # Save every 30th frame (~2 per sec at 60 FPS internal; we run uncapped)
        if self.frame_count % 30 == 0:
            try:
                path = self.frames_dir / f"t{t:08.2f}.png"
                pygame.image.save(game.internal, str(path))
            except Exception as exc:
                self.anomalies.append(f"capture error: {exc}")

    # ------------------------------------------------------------------
    # State extraction
    # ------------------------------------------------------------------
    def snapshot(self, game: Game, t: float) -> dict:
        scene = game.scenes.scenes.get(game.scenes.current_state)
        snap: dict = {
            "t": round(t, 3),
            "frame": self.frame_count,
            "state": game.scenes.current_state.value,
            "is_overlay": game.scenes.is_overlay_active(),
        }
        # Extract player info if GameplayScene
        if hasattr(scene, "_player"):
            p = scene._player
            snap["player"] = {
                "x": round(p.x, 1),
                "y": round(p.y, 1),
                "vx": round(p.vx, 1),
                "vy": round(p.vy, 1),
                "state": p.state.value,
                "hp": p.hp,
                "lives": p.lives,
                "bombs": p.bombs,
                "tilt": round(p.current_tilt, 1),
                "is_dead": p.is_dead,
                "is_game_over": p.is_game_over,
                "in_dash_iframes": p.dash_iframes_left > 0,
                "charge_time": round(p.charge_time, 2),
            }
            # Anomaly: player stuck in same state forever
            if p.state == self.last_state:
                pass
            else:
                self.last_state = p.state
                self.t_last_change = t
            # Anomaly: player stuck off-bounds
            if not (5 <= p.x <= INTERNAL_W - 5) or not (5 <= p.y <= INTERNAL_H - 5):
                self.anomalies.append(
                    f"t={t:.2f}: player out of bounds x={p.x:.1f} y={p.y:.1f}"
                )
        return snap

    # ------------------------------------------------------------------
    # Anomaly detection
    # ------------------------------------------------------------------
    def check_anomalies(self, snap: dict) -> None:
        # State stagnation
        if snap["t"] - self.t_last_change > 8.0 and snap["state"] == "gameplay":
            self.anomalies.append(
                f"t={snap['t']:.2f}: state stuck at gameplay for >8s (maybe enemy/wave broken?)"
            )
        # Player died
        p = snap.get("player")
        if p and p["is_dead"] and not getattr(self, "_logged_death", False):
            self._logged_death = True
            self.anomalies.append(
                f"t={snap['t']:.2f}: player died (state={p['state']})"
            )

    # ------------------------------------------------------------------
    # Input simulation
    # ------------------------------------------------------------------
    def sim_input(self, scene, t: float) -> None:
        """Inject fake key events into the scene's input handling.

        Two channels:
        1. Pygame key state (for GameplayScene which calls pygame.key.get_pressed
           and overwrites player.input_* each frame).
        2. Direct KEYDOWN events (for menu scenes that read event queue).
        """
        if not hasattr(scene, "_player"):
            return
        p = scene._player
        # Pseudo-random movement
        cycle = int(t * 2) % 6
        want_left = (cycle < 3)
        want_right = (cycle >= 3)
        # Pygame key state injection: use pygame.key.set_repeat + post events.
        # Easier: use a fake pressed-keys dict that the scene reads.
        fake_pressed: dict[int, bool] = {}
        if want_left:
            fake_pressed[pygame.K_a] = True
            fake_pressed[pygame.K_LEFT] = True
        if want_right:
            fake_pressed[pygame.K_d] = True
            fake_pressed[pygame.K_RIGHT] = True
        fake_pressed[pygame.K_j] = True  # always firing
        # Monkey-patch pygame.key.get_pressed to return our fake state
        if not hasattr(self, "_orig_get_pressed"):
            self._orig_get_pressed = pygame.key.get_pressed
        pygame.key.get_pressed = lambda: type("K", (), {"__getitem__": lambda s, k: fake_pressed.get(k, False)})()
        # Direct player input for non-keyboard-driven systems (bombs, dash)
        p.input_bomb = (int(t) % 15 == 7 and int(t * 60) % 60 == 0)
        p.input_dash = (abs(t - round(t / 3) * 3) < 0.05 and int(t * 60) % 60 == 0)

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def run(self, duration: float, scenario: str = "random") -> None:
        print(f"[playtest] starting scenario={scenario} duration={duration}s")
        pygame.init()
        game = Game()
        # Force the game into gameplay state for direct testing
        game.scenes.transition_to(GameState.ACT_INTRO)
        # Skip the act_intro timer by sending a transition key
        # ACT_INTRO transitions to GAMEPLAY after 4s; we'll fast-forward
        start = time.perf_counter()
        last_log = start
        log_every = 1.0  # seconds
        while time.perf_counter() - start < duration:
            t = time.perf_counter() - start
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    print("[playtest] QUIT event received")
                    return
            # Simulate input
            current_scene = game.scenes.scenes.get(game.scenes.current_state)
            if current_scene is not None:
                try:
                    self.sim_input(current_scene, t)
                except Exception as exc:
                    self.anomalies.append(f"input sim error: {exc}")
            # Fixed-timestep tick
            game.clock.tick(60)  # 60 FPS for speed
            frame_time = 1.0 / 60.0
            game._accumulator += frame_time
            while game._accumulator >= (1.0 / 120):
                game.scenes.update(1.0 / 120)
                game._accumulator -= 1.0 / 120
            # Draw
            game.internal.fill((0, 0, 0))
            game.scenes.draw(game.internal)
            # Capture
            self.capture(game, t)
            # Snapshot + log
            if t - (last_log - start) >= log_every:
                snap = self.snapshot(game, t)
                self.check_anomalies(snap)
                self.log.append(snap)
                last_log = time.perf_counter()
        # Save log
        log_path = self.out_dir / "playtest.jsonl"
        with open(log_path, "w", encoding="utf-8") as f:
            for entry in self.log:
                f.write(json.dumps(entry) + "\n")
        # Save anomalies
        anom_path = self.out_dir / "anomalies.txt"
        with open(anom_path, "w", encoding="utf-8") as f:
            f.write(f"Scenario: {scenario}\n")
            f.write(f"Duration: {duration}s\n")
            f.write(f"Frames: {self.frame_count}\n")
            f.write(f"Anomalies: {len(self.anomalies)}\n")
            f.write("=" * 60 + "\n")
            for a in self.anomalies:
                f.write(f"  {a}\n")
        # Save last frame for inspection
        try:
            pygame.image.save(game.internal, str(self.out_dir / "last_frame.png"))
        except Exception:
            pass
        # Summary
        print(f"\n[playtest] DONE")
        print(f"  scenario  : {scenario}")
        print(f"  duration  : {duration:.1f}s")
        print(f"  frames    : {self.frame_count}")
        print(f"  snapshots : {len(self.log)}")
        print(f"  anomalies : {len(self.anomalies)}")
        if self.anomalies:
            print(f"  See: {anom_path}")
        print(f"  Log: {log_path}")
        print(f"  Last frame: {self.out_dir / 'last_frame.png'}")
        print(f"  Frames dir: {self.frames_dir}")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--duration", type=float, default=30.0)
    p.add_argument("--scenario", default="random",
                   choices=("random", "dodge", "boss", "full"))
    p.add_argument("--out", default="tools/playtest_out")
    args = p.parse_args()
    pt = Playtester(Path(args.out))
    pt.run(args.duration, args.scenario)
    return 0


if __name__ == "__main__":
    sys.exit(main())
