"""BLOQUE 58.36d: replace _draw_enemy dispatch with arwing template.

Replaces:
  - Entire if/elif/else block (SCOUT through default) inside _draw_enemy
  - Adds _draw_arwing method right before the cfg.is_mini check
  - Replaces _draw_sub_boss_sprite (the body that draws to scratch)
"""
from __future__ import annotations
import sys
from pathlib import Path

PATH = Path("src/ui/gameplay_runtime.py")

# 1) New dispatch body (per-kind call to _draw_arwing)
NEW_DISPATCH = '''        if e.kind == EnemyKind.SCOUT:
            # 12x8 Mono-Raptor dart — minimal, fast, cyan accent
            self._draw_arwing(
                target, cx, cy, w, h,
                accent=(80, 220, 240), accent_dark=(30, 110, 130),
                accent_h=(200, 245, 255), weapon="none", special="dart",
            )
        elif e.kind == EnemyKind.CRUISER:
            # 14x10 Cornerian Fighter — balanced delta, green accent, side guns
            self._draw_arwing(
                target, cx, cy, w, h,
                accent=(100, 220, 100), accent_dark=(40, 130, 50),
                accent_h=(200, 255, 200), weapon="side_guns",
                special="std", engine_color=(255, 200, 80),
            )
        elif e.kind == EnemyKind.HEAVY:
            # 18x12 armored bomber — wide body, 4 corner turrets, red core
            self._draw_arwing(
                target, cx, cy, w, h,
                accent=(220, 60, 70), accent_dark=(130, 30, 35),
                accent_h=(255, 200, 200), weapon="corner_turrets",
                special="armored", engine_color=(255, 200, 80),
            )
        elif e.kind == EnemyKind.KAMIKAZE:
            # 10x10 diving spike — narrow delta, hot pulsing core, flame
            self._draw_arwing(
                target, cx, cy, w, h,
                accent=(255, 140, 50), accent_dark=(160, 70, 20),
                accent_h=(255, 220, 130), weapon="none", special="aggressive",
                engine_color=(255, 180, 60), flame=True,
            )
        elif e.kind == EnemyKind.SNIPER:
            # 16x8 long-range — elongated body, blue laser cannon underneath
            self._draw_arwing(
                target, cx, cy, w, h,
                accent=(100, 160, 255), accent_dark=(50, 90, 180),
                accent_h=(180, 220, 255), weapon="long_cannon",
                special="elongated", engine_color=(255, 200, 80),
            )
        elif e.kind == EnemyKind.DRONE:
            # 8x8 small circular ship — tight delta, cyan core, ring of dots
            self._draw_arwing(
                target, cx, cy, w, h,
                accent=(80, 200, 255), accent_dark=(30, 90, 130),
                accent_h=(200, 240, 255), weapon="none", special="round",
                engine_color=(255, 200, 80),
            )
        elif e.kind == EnemyKind.TURRET:
            # 12x12 defensive — symmetric delta, pink rotating cannons
            self._draw_arwing(
                target, cx, cy, w, h,
                accent=(255, 100, 180), accent_dark=(160, 50, 110),
                accent_h=(255, 200, 230), weapon="rotating_ring",
                special="defensive", engine_color=(255, 200, 80),
            )
        elif e.kind == EnemyKind.SUB_BOSS:
            # BLOQUE 58.6.5: sub-boss rotates to face velocity.
            # Draw nose-DOWN sprite to scratch, then rotate 0/90/180/270.
            self._sub_boss_scratch.fill((0, 0, 0, 0))
            scratch_cx = self._sub_boss_scratch.get_width() // 2
            scratch_cy = self._sub_boss_scratch.get_height() // 2
            self._draw_sub_boss_sprite(
                self._sub_boss_scratch, scratch_cx, scratch_cy, w, h,
            )
            from src.entities.enemies.enemy import sub_boss_facing_angle
            facing = sub_boss_facing_angle(e.vx, e.vy)
            rotated = pygame.transform.rotate(self._sub_boss_scratch, facing)
            target.blit(
                rotated,
                (cx - rotated.get_width() // 2,
                 cy - rotated.get_height() // 2),
            )
        else:
            # Default fallback: simple arwing with the kind's color
            r, g, b = color
            accent = (min(255, r + 40), min(255, g + 40), min(255, b + 40))
            accent_dark = (max(0, r - 80), max(0, g - 80), max(0, b - 80))
            accent_h = (min(255, r + 80), min(255, g + 80), min(255, b + 80))
            self._draw_arwing(
                target, cx, cy, w, h,
                accent=accent, accent_dark=accent_dark, accent_h=accent_h,
                weapon="none", special="std", engine_color=(255, 200, 80),
            )
'''

# 2) New _draw_arwing method — unified Star Fox 64-style template
NEW_ARWING = '''
    def _draw_arwing(
        self, target: pygame.Surface, cx: int, cy: int, w: int, h: int,
        *,
        accent: tuple, accent_dark: tuple, accent_h: tuple,
        weapon: str, special: str,
        engine_color: tuple = (255, 200, 80),
        flame: bool = False,
    ) -> None:
        """BLOQUE 58.36d: unified Star Fox 64-style arwing template.

        All enemy ships share this base silhouette: delta wing (nose
        pointing DOWN, engines at the TOP), silver 4-step shading, glowing
        cockpit eye with halo, twin engine rects.

        Per-type variation:
          - weapon: "none" | "side_guns" | "long_cannon" | "corner_turrets"
            | "rotating_ring" | "central_beam"
          - special: "std" | "dart" | "armored" | "aggressive"
            | "elongated" | "round" | "defensive"
          - engine_color: tuple of 3 ints (default yellow)
          - flame: bool — adds hot orange exhaust above engines

        Design language: top-down view of a Star Fox 64 Arwing/Star Wolf
        fighter. Light source: top-left. Outline: 1-px dark inset.
        """
        # Master silver palette (4-step shading)
        silver_hi   = (210, 220, 235)
        silver      = (170, 180, 195)
        silver_mid  = (115, 130, 150)
        silver_dark = (60, 75, 95)
        # Geometry (scaled to actual size)
        top_y    = cy - h // 2
        bot_y    = cy + h // 2
        wing_tip_y = top_y + max(1, h // 4)  # wing tips are at the back (top)
        shoulder_y = top_y + max(1, h // 3)
        half_w   = w // 2
        # ---- 1) Outline (dark base) ----
        # Delta wing: wing tips at top-side, nose at bottom.
        if special == "aggressive":
            # Pointier, narrower wings (kamikaze)
            pygame.draw.polygon(target, silver_dark, [
                (cx + half_w, wing_tip_y),
                (cx + 1, shoulder_y),
                (cx, bot_y),
                (cx - 1, shoulder_y),
                (cx - half_w, wing_tip_y),
                (cx, top_y),
            ])
        elif special == "elongated":
            # Sniper — wider wing tips, longer body
            pygame.draw.polygon(target, silver_dark, [
                (cx + half_w, wing_tip_y),
                (cx + 1, shoulder_y),
                (cx + 1, cy + 1),
                (cx, bot_y),
                (cx - 1, cy + 1),
                (cx - 1, shoulder_y),
                (cx - half_w, wing_tip_y),
                (cx, top_y),
            ])
        elif special == "armored":
            # Heavy — boxy hull with extended wing roots
            pygame.draw.polygon(target, silver_dark, [
                (cx + half_w, wing_tip_y),
                (cx + 1, shoulder_y - 1),
                (cx + 1, cy + 1),
                (cx, bot_y),
                (cx - 1, cy + 1),
                (cx - 1, shoulder_y - 1),
                (cx - half_w, wing_tip_y),
                (cx, top_y),
            ])
        else:
            # Standard delta (Scout/Cruiser/Drone/Turret)
            pygame.draw.polygon(target, silver_dark, [
                (cx + half_w, wing_tip_y),
                (cx + 1, shoulder_y),
                (cx, bot_y),
                (cx - 1, shoulder_y),
                (cx - half_w, wing_tip_y),
                (cx, top_y),
            ])
        # ---- 2) Main body (1-px inset) ----
        if special == "elongated":
            pygame.draw.polygon(target, silver, [
                (cx + half_w - 1, wing_tip_y + 1),
                (cx + 1, shoulder_y + 1),
                (cx + 1, cy + 2),
                (cx, bot_y - 1),
                (cx - 1, cy + 2),
                (cx - 1, shoulder_y + 1),
                (cx - half_w + 1, wing_tip_y + 1),
                (cx, top_y + 1),
            ])
        elif special == "armored":
            pygame.draw.polygon(target, silver, [
                (cx + half_w - 1, wing_tip_y + 1),
                (cx + 1, shoulder_y),
                (cx + 1, cy + 2),
                (cx, bot_y - 1),
                (cx - 1, cy + 2),
                (cx - 1, shoulder_y),
                (cx - half_w + 1, wing_tip_y + 1),
                (cx, top_y + 1),
            ])
        else:
            pygame.draw.polygon(target, silver, [
                (cx + half_w - 1, wing_tip_y + 1),
                (cx + 1, shoulder_y + 1),
                (cx, bot_y - 1),
                (cx - 1, shoulder_y + 1),
                (cx - half_w + 1, wing_tip_y + 1),
                (cx, top_y + 1),
            ])
        # ---- 3) Top highlight (lit from top-left) ----
        pygame.draw.polygon(target, silver_hi, [
            (cx, top_y + 1),
            (cx + 1, shoulder_y + 1),
            (cx, shoulder_y + 2),
        ])
        pygame.draw.line(target, silver_hi,
                         (cx - 1, shoulder_y + 1), (cx, top_y + 1), 1)
        # ---- 4) Inner panel detail (silver_mid) — gives the ship depth ----
        if h >= 8:
            spine_top = top_y + 2
            spine_bot = bot_y - 2
            pygame.draw.line(target, silver_dark,
                             (cx, spine_top), (cx, spine_bot), 1)
            if w >= 12 and h >= 10:
                pygame.draw.line(target, silver_mid,
                                 (cx - half_w + 1, wing_tip_y + 1),
                                 (cx - 1, shoulder_y + 1), 1)
                pygame.draw.line(target, silver_mid,
                                 (cx + half_w - 1, wing_tip_y + 1),
                                 (cx + 1, shoulder_y + 1), 1)
        # ---- 5) Cockpit eye (glowing accent) with halo ----
        eye_x, eye_y = cx, cy - (1 if h >= 10 else 0)
        halo_size = 8 if w >= 12 else 6
        eye_halo = pygame.Surface((halo_size, halo_size), pygame.SRCALPHA)
        pygame.draw.circle(eye_halo, (*accent, 80),
                           (halo_size // 2, halo_size // 2), halo_size // 2)
        target.blit(eye_halo, (eye_x - halo_size // 2, eye_y - halo_size // 2))
        if special == "aggressive":
            pulse = 200 + int(55 * math.sin(self._t * 8))
            pygame.draw.circle(target, (pulse, 60, 30), (eye_x, eye_y), 2)
            pygame.draw.circle(target, accent_h, (eye_x, eye_y), 1)
        elif special == "armored":
            pygame.draw.circle(target, accent_dark, (eye_x, eye_y), 2)
            pygame.draw.circle(target, accent, (eye_x, eye_y), 2)
            pygame.draw.circle(target, accent_h, (eye_x, eye_y), 1)
        else:
            pygame.draw.circle(target, accent, (eye_x, eye_y), 1)
            pygame.draw.circle(target, accent_h, (eye_x, eye_y), 1)
        # ---- 6) Twin engines at the TOP (back of ship) ----
        eng_w = max(1, w // 6)
        eng_h = max(1, h // 8)
        eng_y = top_y - eng_h
        pygame.draw.rect(target, silver_dark,
                         (cx - eng_w * 2, eng_y, eng_w, eng_h))
        pygame.draw.rect(target, silver_dark,
                         (cx + eng_w, eng_y, eng_w, eng_h))
        pulse_e = 200 + int(40 * math.sin(self._t * 12))
        ec = (min(255, engine_color[0] * pulse_e // 200),
              min(255, engine_color[1] * pulse_e // 200),
              min(255, engine_color[2] * pulse_e // 200))
        pygame.draw.rect(target, ec,
                         (cx - eng_w * 2, eng_y, eng_w, eng_h - 1))
        pygame.draw.rect(target, ec,
                         (cx + eng_w, eng_y, eng_w, eng_h - 1))
        if flame:
            for dx in (-eng_w * 2 + eng_w // 2, eng_w + eng_w // 2):
                fx = cx + dx
                pygame.draw.circle(target, (255, 100, 30),
                                   (fx, eng_y - 1), 1)
                pygame.draw.circle(target, (255, 200, 80),
                                   (fx, eng_y - 2), 1)
                pygame.draw.circle(target, (255, 255, 200),
                                   (fx, eng_y - 3), 1)
        # ---- 7) Per-weapon detail ----
        if weapon == "side_guns":
            gun_y = cy - 1
            for gx in (cx - half_w + 2, cx + half_w - 3):
                pygame.draw.rect(target, silver_dark,
                                 (gx, gun_y, 1, max(2, h // 4)))
                pygame.draw.rect(target, accent_dark,
                                 (gx, gun_y, 1, 1))
                pygame.draw.circle(target, accent, (gx, gun_y + max(2, h // 4)), 1)
        elif weapon == "long_cannon":
            barrel_len = max(4, h // 2 + 2)
            pygame.draw.rect(target, accent_dark,
                             (cx - 1, cy, 2, barrel_len))
            pygame.draw.rect(target, accent,
                             (cx - 1, cy, 1, barrel_len))
            pygame.draw.circle(target, accent_h, (cx, cy + barrel_len), 1)
        elif weapon == "corner_turrets":
            for ddx, ddy in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
                tcx = cx + ddx * (half_w - 2)
                tcy = cy + ddy * (h // 2 - 2)
                th = pygame.Surface((6, 6), pygame.SRCALPHA)
                pygame.draw.circle(th, (*accent, 70), (3, 3), 3)
                target.blit(th, (tcx - 3, tcy - 3))
                pygame.draw.circle(target, silver_dark, (tcx, tcy), 1)
                pygame.draw.circle(target, accent, (tcx, tcy), 1)
        elif weapon == "rotating_ring":
            import math as _m
            angle = self._t * 3
            for spoke in range(3):
                a = angle + spoke * (2 * _m.pi / 3)
                ex = cx + int(_m.cos(a) * half_w * 0.6)
                ey = cy + int(_m.sin(a) * h * 0.35)
                pygame.draw.line(target, accent_dark, (cx, cy), (ex, ey), 1)
                pygame.draw.line(target, accent, (cx, cy), (ex, ey), 1)
                tip_h = pygame.Surface((4, 4), pygame.SRCALPHA)
                pygame.draw.circle(tip_h, (*accent, 80), (2, 2), 2)
                target.blit(tip_h, (ex - 2, ey - 2))
                pygame.draw.circle(target, accent_h, (ex, ey), 1)
        # ---- 8) Per-special decorative details ----
        if special == "dart":
            pygame.draw.circle(target, accent_h, (cx, bot_y - 1), 1)
        elif special == "round":
            import math as _m
            for k in range(4):
                a = k * _m.pi / 2 + _m.pi / 4
                dx = int(_m.cos(a) * (half_w - 1))
                dy = int(_m.sin(a) * (h // 2 - 1))
                pygame.draw.circle(target, accent, (cx + dx, cy + dy), 1)
        elif special == "defensive":
            for ddx, ddy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                dx = ddx * (half_w - 1)
                dy = ddy * (h // 2 - 1)
                pygame.draw.circle(target, accent, (cx + dx, cy + dy), 1)
'''

# 3) New sub-boss sprite — Star Wolf-style fighter (not an alien creature)
NEW_SUB_BOSS = '''
    def _draw_sub_boss_sprite(
        self, target: pygame.Surface, cx: int, cy: int, w: int, h: int,
    ) -> None:
        """BLOQUE 58.36d: sub-boss redesign (Star Wolf Wolfen fighter).

        Visual identity (proper Star Fox 64-style 8-bit spaceship, not an
        alien creature):
          - Wide delta-wing silhouette with sharp wing tips at the back
          - 4-step silver shading (highlight, main, mid, dark)
          - Twin menacing red eyes at the body center (Star Wolf style)
          - Cyan glow halos around the eyes
          - Twin large engines at the TOP (purple pulsing)
          - Red Star Wolf accent stripes along the wing leading edges
          - Pink trim at the nose tip
          - 4 panel dots on the body (alien predator DNA)
          - All visuals scale with the hitbox (24x14 = reference)
        """
        import math as _m
        wolf_hi     = (210, 220, 235)
        wolf_main   = (160, 175, 200)
        wolf_mid    = (110, 125, 150)
        wolf_dark   = (50,  60,  85)
        wolf_red    = (220, 50,  60)
        wolf_red_d  = (130, 20,  30)
        cyan_eye    = (80,  220, 240)
        cyan_eye_h  = (200, 245, 255)
        pink_nose   = (255, 100, 180)
        sx = w / 24.0
        sy = h / 14.0
        bob = int(round(_m.sin(self._t * 2.0 * _m.pi) * 1.0))
        cy_b = cy + bob
        engine_pulse = 0.7 + 0.3 * (0.5 + 0.5 * _m.sin(self._t * 6.0))
        eye_pulse = 0.85 + 0.15 * _m.sin(self._t * 3.0)
        body_top_y = cy_b - h // 2
        body_bot_y = cy_b + h // 2
        half_w = max(8, int(round(11 * sx)))
        wing_tip_y = body_top_y + max(1, int(round(2 * sy)))
        shoulder_y = body_top_y + max(2, int(round(3 * sy)))
        pygame.draw.polygon(target, wolf_dark, [
            (cx + half_w, wing_tip_y),
            (cx + 1, shoulder_y),
            (cx + 1, cy_b + 1),
            (cx, body_bot_y),
            (cx - 1, cy_b + 1),
            (cx - 1, shoulder_y),
            (cx - half_w, wing_tip_y),
            (cx, body_top_y),
        ])
        pygame.draw.polygon(target, wolf_main, [
            (cx + half_w - 1, wing_tip_y + 1),
            (cx + 1, shoulder_y + 1),
            (cx + 1, cy_b + 2),
            (cx, body_bot_y - 1),
            (cx - 1, cy_b + 2),
            (cx - 1, shoulder_y + 1),
            (cx - half_w + 1, wing_tip_y + 1),
            (cx, body_top_y + 1),
        ])
        pygame.draw.polygon(target, wolf_hi, [
            (cx, body_top_y + 1),
            (cx + 1, shoulder_y + 1),
            (cx, shoulder_y + 2),
        ])
        pygame.draw.line(target, wolf_hi,
                         (cx - 1, shoulder_y + 1), (cx, body_top_y + 1), 1)
        pygame.draw.line(target, wolf_mid,
                         (cx - half_w + 1, wing_tip_y + 1),
                         (cx - 1, shoulder_y + 1), 1)
        pygame.draw.line(target, wolf_mid,
                         (cx + half_w - 1, wing_tip_y + 1),
                         (cx + 1, shoulder_y + 1), 1)
        pygame.draw.line(target, wolf_dark,
                         (cx, body_top_y + 2), (cx, body_bot_y - 2), 1)
        pygame.draw.line(target, wolf_red,
                         (cx - half_w + 1, wing_tip_y + 1),
                         (cx - 1, shoulder_y + 2), 1)
        pygame.draw.line(target, wolf_red,
                         (cx + half_w - 1, wing_tip_y + 1),
                         (cx + 1, shoulder_y + 2), 1)
        eye_y = cy_b - 1
        eye_x_off = max(1, int(round(2 * sx)))
        for sign in (-1, 1):
            ex = cx + sign * eye_x_off
            halo_size = 8
            eye_halo = pygame.Surface((halo_size, halo_size), pygame.SRCALPHA)
            pygame.draw.circle(eye_halo, (*cyan_eye, 70),
                               (halo_size // 2, halo_size // 2), 3)
            target.blit(eye_halo, (ex - halo_size // 2, eye_y - halo_size // 2))
            r1 = max(1, int(round(2 * eye_pulse)))
            pygame.draw.circle(target, wolf_dark, (ex, eye_y), r1 + 1)
            pygame.draw.circle(target, wolf_red, (ex, eye_y), r1)
            pygame.draw.circle(target, wolf_red_d, (ex, eye_y), max(0, r1 - 1))
            pygame.draw.circle(target, cyan_eye_h, (ex, eye_y - 1), 1)
        panel_y_off = max(1, int(round(2 * sy)))
        for px_off in (-max(2, int(round(3 * sx))), max(2, int(round(3 * sx)))):
            pygame.draw.circle(target, wolf_dark,
                               (cx + px_off, body_top_y + panel_y_off), 1)
        pygame.draw.circle(target, pink_nose, (cx, body_bot_y), 1)
        eng_w = max(2, int(round(3 * sx)))
        eng_h = max(2, int(round(2 * sy)))
        eng_y = body_top_y - eng_h
        pygame.draw.rect(target, wolf_dark,
                         (cx - eng_w * 2, eng_y, eng_w, eng_h))
        pygame.draw.rect(target, wolf_dark,
                         (cx + eng_w, eng_y, eng_w, eng_h))
        eng_c = (
            int(255 * engine_pulse),
            int(120 * engine_pulse),
            int(240 * engine_pulse),
        )
        pygame.draw.rect(target, eng_c,
                         (cx - eng_w * 2, eng_y, eng_w, eng_h - 1))
        pygame.draw.rect(target, eng_c,
                         (cx + eng_w, eng_y, eng_w, eng_h - 1))
        halo_a = int(80 * engine_pulse)
        if halo_a > 0:
            for eng_x in (cx - eng_w * 2 + eng_w // 2,
                          cx + eng_w + eng_w // 2):
                eh = pygame.Surface((eng_w * 4, eng_h * 4), pygame.SRCALPHA)
                pygame.draw.circle(eh, (255, 120, 240, halo_a),
                                   (eng_w * 2, eng_h * 2), eng_w * 2)
                target.blit(eh,
                            (eng_x - eng_w * 2, eng_y - eng_h))
        halo_w = w + 12
        halo_h = h + 12
        halo_alpha = 35 + int(15 * _m.sin(self._t * 6))
        pygame.draw.ellipse(
            target, (*wolf_red, halo_alpha),
            (cx - halo_w // 2, cy_b - halo_h // 2, halo_w, halo_h), 1,
        )
'''


def main() -> int:
    src = PATH.read_text(encoding="utf-8")
    orig_len = len(src)

    # ---- 1) Find the SCOUT dispatch line ----
    scout_marker = "        if e.kind == EnemyKind.SCOUT:\n"
    scout_idx = src.find(scout_marker)
    if scout_idx == -1:
        print("ERROR: SCOUT dispatch line not found")
        return 1
    print(f"SCOUT dispatch at offset {scout_idx}")

    # ---- 2) Find the cfg.is_mini line (end of dispatch) ----
    cfg_mini_marker = "        if cfg.is_mini:\n"
    cfg_mini_idx = src.find(cfg_mini_marker, scout_idx)
    if cfg_mini_idx == -1:
        print("ERROR: cfg.is_mini line not found")
        return 1
    print(f"cfg.is_mini at offset {cfg_mini_idx}")

    # ---- 3) Find start of the cfg.is_mini line ----
    line_start = src.rfind("\n", 0, cfg_mini_idx) + 1

    # ---- 4) Replace SCOUT..cfg.is_mini with NEW_DISPATCH + NEW_ARWING + blank ----
    new_block = NEW_DISPATCH + NEW_ARWING + "\n"
    src = src[:scout_idx] + new_block + src[line_start:]

    # ---- 5) Verify ----
    if "def _draw_arwing" not in src:
        print("ERROR: _draw_arwing method not added")
        return 1
    if "        if cfg.is_mini:" not in src:
        print("ERROR: cfg.is_mini disappeared")
        return 1
    if "        if e.kind == EnemyKind.SCOUT:" not in src:
        print("ERROR: SCOUT dispatch missing")
        return 1
    print("Dispatch + arwing: OK")

    # ---- 6) Replace _draw_sub_boss_sprite ----
    sub_start = "    def _draw_sub_boss_sprite(\n"
    sub_start_idx = src.find(sub_start)
    if sub_start_idx == -1:
        print("ERROR: _draw_sub_boss_sprite not found")
        return 1
    print(f"_draw_sub_boss_sprite at offset {sub_start_idx}")

    # Find the END of the current sub-boss method. It ends with a blank line
    # followed by a new method def or class.
    # The current method ends at the last `        )` line of the last
    # function call (the ellipse halo). We look for the end of the
    # _draw_sub_boss_sprite function — the next "    def " at 4-space indent.
    next_def_idx = src.find("\n    def _draw_boss(self,", sub_start_idx)
    if next_def_idx == -1:
        print("ERROR: end of _draw_sub_boss_sprite not found")
        return 1

    # Walk back to find the end of the last statement. The body ends with
    # `        )` for the ellipse call. Add 2 newlines after.
    sub_body_end = next_def_idx + 1  # keep the leading \n

    src = src[:sub_start_idx] + NEW_SUB_BOSS + src[sub_body_end:]

    if "        cx + 1, shoulder_y + 2), 1)\n" not in src:
        # sanity check the new sub-boss was inserted
        pass

    PATH.write_text(src, encoding="utf-8")
    new_len = len(src)
    print(f"OK: {orig_len} -> {new_len} bytes (delta {new_len - orig_len:+d})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
