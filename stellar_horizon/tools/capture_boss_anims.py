"""Capture screenshots of the 4 boss animations (IDLE, TELEGRAPH, CHARGE, DYING).

Renders 4 frames + a contact sheet showing all 4 animations side by side.
This is a visual smoke test — if it crashes or the PNGs look wrong the
integration is broken.
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
from stellar_horizon.scenes.gameplay import GameplayScene  # noqa: E402
from stellar_horizon.settings import INTERNAL_W, INTERNAL_H  # noqa: E402
from stellar_horizon.tools.make_placeholder_bgs import make_placeholder_backgrounds  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent / "playtest_out"
OUT_DIR.mkdir(exist_ok=True)


def _write_minimal_midi(path: Path) -> None:
    """Write a 27-byte minimal valid MIDI file (1 track, end-of-track).

    Used in place of make_placeholder_midi when mido isn't installed;
    pygame.mixer.music.load() accepts it.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(bytes([
        0x4D, 0x54, 0x68, 0x64,  # "MThd"
        0, 0, 0, 6,              # header length = 6
        0, 0,                    # format = 0
        0, 1,                    # tracks = 1
        0, 96,                   # division = 96
        0x4D, 0x54, 0x72, 0x6B,  # "MTrk"
        0, 0, 0, 4,              # track length = 4
        0, 0,                    # delta = 0
        0xFF, 0x2F, 0,           # end-of-track meta
    ]))


def _build_scene(assets_dir: Path) -> GameplayScene:
    midi = MidiPlayer()
    # Stub out midi_player.play so the dummy audio driver doesn't
    # choke on a placeholder MIDI file. We only need visual capture
    # here, not audio playback.
    midi.play = lambda *a, **kw: None  # type: ignore[assignment]
    midi.fadeout = lambda *a, **kw: None  # type: ignore[assignment]
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
    import shutil
    import tempfile
    # Real sprite source (where the 4 boss sheets actually live).
    real_sprites = ROOT / "assets" / "sprites"
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        bg_dir = td / "backgrounds"
        make_placeholder_backgrounds(bg_dir)
        midi_dir = td / "midi"
        midi_dir.mkdir(parents=True, exist_ok=True)
        _write_minimal_midi(midi_dir / "act1.mid")
        # Copy the 4 boss animation sheets so AnimatedSprite can load
        # them. The other sprites fall back to the magenta placeholder
        # in headless mode, but the boss ones need to be real so the
        # capture shows the actual new artwork.
        sprite_dir = td / "sprites"
        sprite_dir.mkdir(parents=True, exist_ok=True)
        for state in ("idle", "telegraph", "charge", "dying"):
            src = real_sprites / f"boss_{state}_sheet.png"
            if src.exists():
                shutil.copy2(src, sprite_dir / src.name)
        # Capture each boss state.
        for state_name, action, phase in [
            ("idle", BossAction.IDLE_PATROL, BossPhase.PHASE_1),
            ("telegraph", BossAction.TELEGRAPH, BossPhase.PHASE_1),
            ("charge", BossAction.CHARGE, BossPhase.PHASE_1),
            ("dying", BossAction.IDLE_PATROL, BossPhase.DYING),
        ]:
            scene = _build_scene(td)
            scene._spawn_boss()
            scene.boss.phase = phase
            scene.boss.x, scene.boss.y = 350.0, 135.0
            scene.boss.action = action
            scene.boss._enter_action(action)
            scene.player.x, scene.player.y = 120.0, 140.0
            # Tick a few frames so the animation cycles.
            for _ in range(30):
                scene.update(1 / 60, [])
            _save(scene, f"boss_v3_{state_name}.png")
    # Also build a contact sheet showing all 4 side by side.
    contact = pygame.Surface((INTERNAL_W * 2, INTERNAL_H * 2), pygame.SRCALPHA)
    contact.blit(pygame.image.load(str(OUT_DIR / "boss_v3_idle.png")), (0, 0))
    contact.blit(pygame.image.load(str(OUT_DIR / "boss_v3_telegraph.png")),
                 (INTERNAL_W, 0))
    contact.blit(pygame.image.load(str(OUT_DIR / "boss_v3_charge.png")),
                 (0, INTERNAL_H))
    contact.blit(pygame.image.load(str(OUT_DIR / "boss_v3_dying.png")),
                 (INTERNAL_W, INTERNAL_H))
    pygame.image.save(contact, str(OUT_DIR / "boss_v3_contact_sheet.png"))
    print("  -> boss_v3_contact_sheet.png")
    pygame.quit()
    print("OK: 4 animations captured + contact sheet.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
