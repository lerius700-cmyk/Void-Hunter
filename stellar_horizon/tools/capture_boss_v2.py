"""Capture screenshots of the new boss state machine + power-up rings.

Renders 4 frames to disk:
  1. Boss in TELEGRAPH (line + warning visible)
  2. Boss in CHARGE (thruster particles + movement)
  3. Player with 1 gold stack (6 max lives)
  4. Player with 2 gold stacks (9 max lives) + a silver ring on screen

This is a visual smoke test — if it crashes or the PNGs are blank
the integration is broken.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))

from stellar_horizon.audio.midi_player import MidiPlayer  # noqa: E402
from stellar_horizon.entities.boss import Boss, BossAction, BossPhase  # noqa: E402
from stellar_horizon.entities.player import Player  # noqa: E402
from stellar_horizon.entities.powerup import PowerUp, PowerUpKind  # noqa: E402
from stellar_horizon.scenes.gameplay import GameplayScene  # noqa: E402
from stellar_horizon.settings import INTERNAL_W, INTERNAL_H  # noqa: E402
from stellar_horizon.tools.make_placeholder_bgs import make_placeholder_backgrounds  # noqa: E402
from stellar_horizon.tools.make_placeholder_midi import make_placeholder_midi  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent / "playtest_out"
OUT_DIR.mkdir(exist_ok=True)


def _build_scene(assets_dir: Path) -> GameplayScene:
    midi = MidiPlayer()
    s = GameplayScene(
        midi_player=midi,
        wave_json=ROOT / "waves" / "waves_act1.json",
        assets_dir=assets_dir,
    )
    s.on_enter()
    return s


def _save(scene: GameplayScene, filename: str) -> None:
    surf = pygame.Surface((INTERNAL_W, INTERNAL_H))
    scene.draw(surf)
    out = OUT_DIR / filename
    pygame.image.save(surf, str(out))
    print(f"  -> {out.name}")


def main() -> int:
    pygame.init()
    pygame.display.set_mode((INTERNAL_W, INTERNAL_H))
    # Build a temp asset dir so the scene loads cleanly.
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        bg_dir = td / "backgrounds"
        make_placeholder_backgrounds(bg_dir)
        midi_dir = td / "midi"
        midi_dir.mkdir(parents=True, exist_ok=True)
        make_placeholder_midi(midi_dir / "act1.mid", seconds=2)
        # 1) Boss in TELEGRAPH.
        scene = _build_scene(td)
        scene._spawn_boss()
        scene.boss.phase = BossPhase.PHASE_1
        scene.boss.x, scene.boss.y = 350.0, 80.0
        scene.boss.action = BossAction.TELEGRAPH
        scene.boss._enter_action(BossAction.TELEGRAPH)
        scene.player.x, scene.player.y = 120.0, 140.0
        # Run a few frames so the bullet cooldown is set.
        for _ in range(5):
            scene.update(1 / 60, [])
        _save(scene, "boss_telegraph_v2.png")
        # 2) Boss in CHARGE.
        scene = _build_scene(td)
        scene._spawn_boss()
        scene.boss.phase = BossPhase.PHASE_1
        scene.boss.x, scene.boss.y = 350.0, 135.0
        scene.boss.action = BossAction.CHARGE
        scene.boss._enter_action(BossAction.CHARGE)
        # Charge target to the left of the boss so the trail flies
        # to the RIGHT and stays on screen.
        scene.boss.charge_target_x = 80.0
        scene.boss.charge_target_y = 130.0
        scene.player.x, scene.player.y = 80.0, 130.0
        for _ in range(3):
            scene.update(1 / 60, [])
        _save(scene, "boss_charge_v2.png")
        # 3) Player with 1 gold stack (max 6 lives).
        scene = _build_scene(td)
        scene.player.lives = 4
        scene.player.max_lives = 6
        scene.player.gold_stacks = 1
        _save(scene, "player_gold_1_stack.png")
        # 4) Player with 2 gold stacks (max 9 lives) + a silver ring.
        scene = _build_scene(td)
        scene.player.lives = 7
        scene.player.max_lives = 9
        scene.player.gold_stacks = 2
        scene._spawn_powerup(200.0, 150.0, PowerUpKind.SILVER)
        scene._spawn_powerup(280.0, 110.0, PowerUpKind.GOLD)
        _save(scene, "player_gold_2_stacks_with_rings.png")
        # 5) Boss in IDLE_PATROL — just to show movement is happening.
        scene = _build_scene(td)
        scene._spawn_boss()
        scene.boss.phase = BossPhase.PHASE_1
        scene.boss.x, scene.boss.y = 350.0, 135.0
        scene.boss.action = BossAction.IDLE_PATROL
        scene.boss._enter_action(BossAction.IDLE_PATROL)
        for _ in range(120):
            scene.update(1 / 60, [])
        _save(scene, "boss_patrol_v2.png")
    pygame.quit()
    print("OK: 5 frames captured to playtest_out/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
