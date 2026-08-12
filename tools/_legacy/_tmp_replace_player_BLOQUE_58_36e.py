"""BLOQUE 58.36e: replace _draw_player with clean Star Fox 64-style design.

Old design: 5-step metallic shading, dorsal antenna, ventral fin, multiple
specular highlights, anti-phase red/green tip lights, center stripe,
wing-tip laser barrels, intake turbines. Over-designed — looks like a hi-res
ship, not 8-bit.

New design: clean white Arwing silhouette with:
  - White body with 4-step silver shading (matching enemy ships)
  - Cyan canopy with halo (the "eye" of the ship)
  - 2 small blue wing-tip dots (Arwing signature)
  - Twin yellow engines at the back
  - 1 thin center stripe (Arwing signature)
  - Wing leading-edge highlight (lit from top-left)
  - No dorsal antenna, no ventral fin, no engine intakes, no wing-tip lasers
"""
from __future__ import annotations
import sys
from pathlib import Path

PATH = Path("src/ui/gameplay_runtime.py")

NEW_PLAYER = '''    def _draw_player(self, target: pygame.Surface, ox: int, oy: int) -> None:
        """BLOQUE 58.36e: player ship redesign (Star Fox 64 Arwing, 8-bit).

        Design language (matches the redesigned enemies + sub-boss):
          - Clean white delta-wing silhouette (32x24 footprint)
          - 4-step silver shading (highlight, main, mid, dark)
          - Cyan canopy (1-px bright dot + alpha halo)
          - 2 small blue wing-tip dots (Arwing signature)
          - Twin yellow engines at the back (with halo)
          - 1 thin center stripe (Arwing signature)
          - Wing leading-edge highlight (lit from top-left)
          - State-based palette:
              IDLE: red+green Arwing tip lights
              PROPULSION: blue+white (matches Tron trail)
              CHARGE L1..L3: progressive white-out
        """
        # Engine flame behind the ship — length scales with |vx|
        self._draw_engine_flame(target, ox, oy)
        is_propulsion = (self._player.state == PlayerState.PROPULSION)
        # ---- Master palette (silver + per-state accent) ----
        # Body: 4-step silver (matches enemies)
        body_hi   = (250, 252, 255)  # white highlight
        body_main = (210, 220, 235)  # main silver
        body_mid  = (140, 155, 180)  # mid silver
        body_dark = (60,  75,  95)   # deep shadow / outline
        # State-specific colors
        if is_propulsion:
            stripe      = (65,  105, 225)  # royal blue
            canopy_dark = (40,  80,  140)
            canopy_glass= (140, 200, 255)
            canopy_h    = (220, 245, 255)
            tip_color   = (180, 220, 255)  # light blue-white
        else:
            # IDLE / CHARGE: red stripe, red canopy (classic Arwing)
            stripe      = (220, 50,  50)
            canopy_dark = (130, 20,  30)
            canopy_glass= (255, 100, 100)
            canopy_h    = (255, 220, 220)
            tip_color   = (220, 50,  50)
        # CHARGE level overrides (progressive lightening)
        if self._player.state == PlayerState.CHARGE:
            level = self._player.get_charge_level()
            if level >= 3:
                body_hi   = (255, 255, 255)
                body_main = (255, 255, 255)
                body_mid  = (240, 240, 255)
                stripe    = (255, 100, 200)
                canopy_glass = (255, 220, 255)
            elif level >= 2:
                body_main = (240, 240, 255)
                body_mid  = (180, 200, 230)
                canopy_glass = (255, 150, 200)
                stripe    = (255, 80, 120)
            elif level >= 1:
                body_main = (220, 235, 250)
                body_mid  = (150, 180, 215)
                canopy_glass = (255, 120, 150)
        # ---- Build the sprite on a 32x24 surface ----
        # Player faces UP (nose at top, engines at bottom)
        surf = pygame.Surface((32, 24), pygame.SRCALPHA)
        if self._player.dash_iframes_left > 0 and (self._t * 30) % 2 < 1:
            pass  # still draw so the trail is visible
        cx = 16  # sprite center
        # ---- 1) Wing outline (dark base) ----
        # Delta wing: wing tips at the BACK (bottom), nose at the FRONT (top)
        pygame.draw.polygon(surf, body_dark, [
            (cx, 0),         # nose tip (top)
            (cx + 1, 5),     # right shoulder
            (cx + 2, 8),     # right body
            (cx + 1, 12),    # right wing root
            (cx + 16, 21),   # right wing tip
            (cx + 14, 22),
            (cx + 10, 16),
            (cx + 2, 17),    # right back
            (cx + 1, 19),    # right engine
            (cx, 22),        # back center
            (cx - 1, 19),    # left engine
            (cx - 2, 17),    # left back
            (cx - 10, 16),
            (cx - 14, 22),
            (cx - 16, 21),   # left wing tip
            (cx - 1, 12),    # left wing root
            (cx - 2, 8),     # left body
            (cx - 1, 5),     # left shoulder
        ])
        # ---- 2) Main body (1-px inset) ----
        pygame.draw.polygon(surf, body_main, [
            (cx, 1),
            (cx + 1, 5),
            (cx + 1, 8),
            (cx + 1, 12),
            (cx + 14, 20),
            (cx + 9, 16),
            (cx + 1, 17),
            (cx + 1, 18),
            (cx, 21),
            (cx - 1, 18),
            (cx - 1, 17),
            (cx - 9, 16),
            (cx - 14, 20),
            (cx - 1, 12),
            (cx - 1, 8),
            (cx - 1, 5),
        ])
        # ---- 3) Top highlight (lit from top-left) ----
        pygame.draw.polygon(surf, body_hi, [
            (cx, 1), (cx - 1, 5), (cx, 6), (cx + 1, 5),
        ])
        pygame.draw.line(surf, body_hi, (cx - 1, 8), (cx - 1, 5), 1)
        # ---- 4) Wing leading-edge highlight (top of wings) ----
        pygame.draw.line(surf, body_hi,
                         (cx + 1, 12), (cx + 12, 19), 1)
        pygame.draw.line(surf, body_hi,
                         (cx - 1, 12), (cx - 12, 19), 1)
        # ---- 5) Wing panel line (subtle construction detail) ----
        pygame.draw.line(surf, body_dark,
                         (cx + 1, 12), (cx + 1, 17), 1)
        pygame.draw.line(surf, body_dark,
                         (cx - 1, 12), (cx - 1, 17), 1)
        # ---- 6) Center stripe (Arwing signature) ----
        pygame.draw.line(surf, stripe, (cx, 6), (cx, 16), 1)
        # ---- 7) Cockpit canopy (1-px bright dot + halo) ----
        # Halo: 8x8 alpha surface, centered on (cx, 9)
        canopy_halo = pygame.Surface((8, 8), pygame.SRCALPHA)
        pygame.draw.circle(canopy_halo, (*canopy_glass, 80),
                           (4, 4), 4)
        surf.blit(canopy_halo, (cx - 4, 5))
        # Inner dark socket
        pygame.draw.circle(surf, canopy_dark, (cx, 9), 1)
        # Bright glass
        pygame.draw.circle(surf, canopy_glass, (cx, 9), 1)
        # Specular highlight (top-left)
        pygame.draw.circle(surf, canopy_h, (cx, 8), 0)
        # ---- 8) Wing-tip dots (small bright accents at the wing tips) ----
        # Halo around each tip
        tip_halo_l = pygame.Surface((6, 6), pygame.SRCALPHA)
        pygame.draw.circle(tip_halo_l, (*tip_color, 90), (3, 3), 3)
        surf.blit(tip_halo_l, (cx - 14 - 1, 19))
        tip_halo_r = pygame.Surface((6, 6), pygame.SRCALPHA)
        pygame.draw.circle(tip_halo_r, (*tip_color, 90), (3, 3), 3)
        surf.blit(tip_halo_r, (cx + 12, 19))
        # Tip dot
        pygame.draw.circle(surf, tip_color, (cx - 12, 21), 1)
        pygame.draw.circle(surf, tip_color, (cx + 12, 21), 1)
        # ---- 9) Twin engines at the BACK (bottom) ----
        # Engine dark housing
        eng_w = 3
        eng_h = 2
        eng_y = 21
        pygame.draw.rect(surf, body_dark,
                         (cx - eng_w - 1, eng_y, eng_w, eng_h))
        pygame.draw.rect(surf, body_dark,
                         (cx + 1, eng_y, eng_w, eng_h))
        # Engine bright core (yellow with pulse)
        pulse_e = 200 + int(40 * math.sin(self._t * 12))
        if is_propulsion:
            ec = (255, 240, 200)  # white-yellow
        else:
            ec = (255, 200, 80)   # warm yellow
        pygame.draw.rect(surf, ec,
                         (cx - eng_w - 1, eng_y, eng_w, 1))
        pygame.draw.rect(surf, ec,
                         (cx + 1, eng_y, eng_w, 1))
        # ---- 10) Engine halos (1-px outer glow at the very back) ----
        eng_halo = pygame.Surface((20, 4), pygame.SRCALPHA)
        pygame.draw.ellipse(eng_halo, (*ec, 100), (0, 0, 20, 4))
        surf.blit(eng_halo, (cx - 10, eng_y - 1))
        # ---- BLOQUE 35: sprite scale 0.75 (player 32x24 -> 24x18) ----
        from src.core.settings import PLAYER_SPRITE_SCALE
        if PLAYER_SPRITE_SCALE != 1.0:
            scaled_w = max(1, int(surf.get_width() * PLAYER_SPRITE_SCALE))
            scaled_h = max(1, int(surf.get_height() * PLAYER_SPRITE_SCALE))
            surf = pygame.transform.scale(surf, (scaled_w, scaled_h))
        # ---- BLOQUE 29: combined tilt + nose angle ----
        rotated = pygame.transform.rotate(
            surf, -(self._player.current_tilt + self._player.current_nose_angle)
        )
        # Recenter after rotation
        rect = rotated.get_rect(center=(int(self._player.x + ox), int(self._player.y + oy)))
        target.blit(rotated, rect)
        # BLOQUE 25: Shield effect during respawn invulnerability
        if self._player.respawn_invuln > 0.0:
            self._draw_shield(target, ox, oy)
        # BLOQUE 22: muzzle flash overlay — bright oval at the player nose
        if self._muzzle_flash > 0.0:
            self._draw_muzzle_flash(target, ox, oy)
        # BLOQUE 49: charge aura + energy absorption particles
        if self._player.state == PlayerState.CHARGE:
            self._draw_charge_aura(target, ox, oy)
            est_dt = 1.0 / 60.0
            self._emit_energy_absorption(est_dt)
        # Afterimage trail — bigger ghost matching the new 32x24 sprite
        for tx, ty, age in self._player.afterimage:
            alpha = max(0, int(255 * (1 - age / self._player.AFTERIMAGE_LIFE)))
            ghost = pygame.Surface((32, 24), pygame.SRCALPHA)
            # Simple Arwing silhouette
            pygame.draw.polygon(ghost, (220, 240, 255, alpha), [
                (cx, 1), (cx + 1, 8), (cx + 1, 17),
                (cx, 21), (cx - 1, 17), (cx - 1, 8),
            ])
            pygame.draw.polygon(ghost, (180, 200, 230, alpha), [
                (cx + 1, 12), (cx + 14, 20), (cx + 9, 16), (cx + 1, 17),
            ])
            pygame.draw.polygon(ghost, (180, 200, 230, alpha), [
                (cx - 1, 12), (cx - 14, 20), (cx - 9, 16), (cx - 1, 17),
            ])
            target.blit(ghost, (int(tx - 16 + ox), int(ty - 12 + oy)))
        # Charge indicator: a ring around the player that fills as charge builds
        charge_level = self._player.get_charge_level()
        if self._player.state == PlayerState.CHARGE and charge_level > 0:
            self._draw_charge_indicator(target, charge_level, ox, oy)
        elif self._player.input_fire and self._player.charge_time > 0.1:
            progress = min(1.0, self._player.charge_time / 0.5)
            self._draw_charge_ring(target, progress, (180, 180, 200), ox, oy)
'''


def main() -> int:
    src = PATH.read_text(encoding="utf-8")
    orig_len = len(src)

    # Find _draw_player start (line 3216)
    start_marker = "    def _draw_player(self, target: pygame.Surface, ox: int, oy: int) -> None:\n"
    start_idx = src.find(start_marker)
    if start_idx == -1:
        print("ERROR: _draw_player not found")
        return 1
    print(f"_draw_player at offset {start_idx}")

    # Find end of _draw_player: next "    def " at 4-space indent
    next_def_idx = src.find("\n    def _draw_reticle(", start_idx)
    if next_def_idx == -1:
        print("ERROR: _draw_reticle not found")
        return 1

    # We want to replace from start_idx to next_def_idx (the blank line + newline
    # before _draw_reticle)
    # Actually keep the leading "\n    def _draw_reticle" so let's stop at the
    # last "\n" before that.
    end_idx = next_def_idx  # the \n before _draw_reticle
    # Walk back to find the start of the trailing blank line
    # The structure is: "...end of _draw_player\n\n    def _draw_reticle..."
    # So end_idx points to the \n before "    def _draw_reticle"
    # We want to keep the blank line + the next def, so end_idx is correct.

    src = src[:start_idx] + NEW_PLAYER.rstrip("\n") + src[end_idx:]

    if "BLOQUE 58.36e: player ship redesign" not in src:
        print("ERROR: new comment not inserted")
        return 1
    if "    def _draw_reticle(" not in src:
        print("ERROR: _draw_reticle disappeared")
        return 1
    print("Player replacement: OK")

    PATH.write_text(src, encoding="utf-8")
    new_len = len(src)
    print(f"OK: {orig_len} -> {new_len} bytes (delta {new_len - orig_len:+d})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
