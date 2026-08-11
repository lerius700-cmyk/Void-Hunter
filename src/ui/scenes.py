"""Concrete scenes for the 9 game states (BLOQUE 14).

All fonts are sized for the 240x360 internal surface (the screen is
scaled 4x to 960x1440 by Game._present). 240px width is the hard cap.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Optional
import math

import pygame

from src.core.scene_manager import GameState, Scene
from src.utils.palette import PALETTE


# Type alias for scene constructor
TransitionFn = Callable[[GameState], None]

if TYPE_CHECKING:
    from src.audio.synth import AudioEngine


def _center_blit(
    target: pygame.Surface,
    text_surface: pygame.Surface,
    y: int,
) -> None:
    """Blit a surface centered horizontally at the given y on target."""
    x = target.get_width() // 2 - text_surface.get_width() // 2
    target.blit(text_surface, (x, y))


def _wrap_text(text: str, font: pygame.font.Font, max_width: int) -> list[str]:
    """Wrap text to fit max_width, breaking on spaces or at hard char limits."""
    if font.size(text)[0] <= max_width:
        return [text]
    words = text.split(" ")
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = (current + " " + word).strip()
        if font.size(candidate)[0] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            # Hard-break words longer than max_width
            while font.size(word)[0] > max_width and len(word) > 1:
                # Binary search largest prefix that fits
                lo, hi = 1, len(word)
                while lo < hi:
                    mid = (lo + hi + 1) // 2
                    if font.size(word[:mid])[0] <= max_width:
                        lo = mid
                    else:
                        hi = mid - 1
                lines.append(word[:lo])
                word = word[lo:]
            current = word
    if current:
        lines.append(current)
    return lines


class TitleScene(Scene):
    """TITLE — main menu, void logo, 'PRESS ANY KEY TO START'.

    Waits for ANY keypress or mouse click to start. Removed the
    BLOQUE 46 auto-start so the player has control over when the
    game begins (fix for "game opens and immediately starts").
    """

    def __init__(self, transition_to: TransitionFn) -> None:
        self._transition_to = transition_to
        self._t: float = 0.0

    def on_enter(self) -> None:
        self._t = 0.0

    def update(self, dt: float) -> None:
        self._t += dt
        for event in pygame.event.get(pygame.KEYDOWN):
            # Any key starts the game (except a few modifiers)
            if event.key in (
                pygame.K_LSHIFT, pygame.K_RSHIFT,
                pygame.K_LCTRL, pygame.K_RCTRL,
                pygame.K_LALT, pygame.K_RALT,
            ):
                continue
            self._transition_to(GameState.ACT_INTRO)
            return
        # Mouse click also starts
        for event in pygame.event.get(pygame.MOUSEBUTTONDOWN):
            self._transition_to(GameState.ACT_INTRO)
            return

    def draw(self, target: pygame.Surface) -> None:
        target.fill((0, 0, 0))
        # Title — 32px sized to fit "VOID HUNTER" in 240px
        font = pygame.font.Font(None, 32)
        title = font.render("VOID HUNTER", True, (220, 220, 255))
        _center_blit(target, title, 100)
        # Subtitle
        font2 = pygame.font.Font(None, 14)
        sub = font2.render("PRESS ANY KEY TO START", True, (255, 240, 140))
        # Blink
        if int(self._t * 2) % 2 == 0:
            _center_blit(target, sub, 200)
        # Hint about controls
        ctrl1 = font2.render("WASD MOVE  |  MOUSE AIM  |  LMB CHARGE  |  RMB RAPID", True, (140, 140, 160))
        _center_blit(target, ctrl1, 220)
        ctrl2 = font2.render("B MISSILE  |  SHIFT DASH  |  ESC PAUSE", True, (140, 140, 160))
        _center_blit(target, ctrl2, 235)
        # Credits hint
        sub2 = font2.render("C: CREDITS", True, (120, 120, 140))
        _center_blit(target, sub2, 230)


class ActIntroScene(Scene):
    """ACT_INTRO — 'ACT N' title + boss portrait placeholder."""

    def __init__(self, transition_to: TransitionFn, act: int = 1) -> None:
        self._transition_to = transition_to
        self._act = act
        self._t: float = 0.0
        self._duration: float = 4.0

    def on_enter(self) -> None:
        self._t = 0.0

    def update(self, dt: float) -> None:
        self._t += dt
        for event in pygame.event.get(pygame.KEYDOWN):
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._transition_to(GameState.GAMEPLAY)
        if self._t >= self._duration:
            self._transition_to(GameState.GAMEPLAY)

    def draw(self, target: pygame.Surface) -> None:
        target.fill((0, 0, 0))
        font = pygame.font.Font(None, 40)
        text = font.render(f"ACT {self._act}", True, (255, 220, 100))
        _center_blit(target, text, 120)
        # Boss name — 18px fits "GOLIATH AWAITS" comfortably
        font2 = pygame.font.Font(None, 18)
        boss_names = {1: "GOLIATH AWAITS", 2: "HYDRA EMERGES", 3: "PHANTOM & NEMESIS"}
        sub = font2.render(boss_names.get(self._act, ""), True, (220, 80, 80))
        _center_blit(target, sub, 200)


class GameplayScene(Scene):
    """GAMEPLAY — main action scene. Delegates to GameplayRuntime.

    Runtime handles: bullets, enemies, waves, score, particles, HUD,
    boss transitions, collisions, hitstop, shake, slowmo.
    """

    def __init__(self, transition_to: "TransitionFn", act: int = 1,
                 audio: Optional["AudioEngine"] = None) -> None:
        self._transition_to = transition_to
        self._act = act
        from src.ui.gameplay_runtime import GameplayRuntime
        self._rt = GameplayRuntime(transition_to, is_boss=False, act=act, audio=audio)

    def on_enter(self) -> None:
        self._rt.on_enter()

    def on_exit(self) -> None:
        self._rt.on_exit()

    def update(self, dt: float) -> None:
        self._rt.update(dt)

    def draw(self, target: pygame.Surface) -> None:
        self._rt.draw(target)


class BossIntroScene(Scene):
    """BOSS_INTRO — RED ALARM warning, 4-6s animated intro (BLOQUE 50).

    The whole scene pulses bright red like a fire alarm. The "WARNING"
    text is rendered in big red letters, flashes at alarm frequency, and
    a scanline / diagonal-stripe pattern overlays the screen to make it
    feel like an emergency klaxon.

    Phases (4.5s total):
      0.0 - 0.3s : White flash burst, then red flash
      0.3 - 1.5s : "!! WARNING !!" text grows + flashes red
      1.5 - 3.5s : Boss portrait slides down from top with red glow
      3.5 - 4.5s : Pulsing red, boss locked in
    """

    def __init__(self, transition_to: TransitionFn, boss_name: str = "BOSS",
                 audio: Optional["AudioEngine"] = None) -> None:
        self._transition_to = transition_to
        self._boss_name = boss_name
        self._audio = audio
        self._t: float = 0.0
        self._duration: float = 4.5

    def on_enter(self) -> None:
        self._t = 0.0
        # BLOQUE 58.23: reuse the game's existing audio engine.
        # The previous code did `AudioEngine()` here, which calls
        # `_prebake_all()` and re-renders EVERY SFX + BGM from scratch.
        # That took ~1.2s, blocking the game loop right at the
        # moment the wave cleared and the boss intro was supposed
        # to start. Using the shared engine is O(1) instead.
        audio = self._audio
        if audio is None:
            # Fallback: construct one if no shared engine was passed
            # (keeps backward-compat for any callers that don't pass audio).
            try:
                from src.audio.synth import AudioEngine
                audio = AudioEngine()
            except Exception:
                return
        try:
            audio.play_sfx("boss_warning", volume=0.9)
        except Exception:
            pass

    def update(self, dt: float) -> None:
        self._t += dt
        for event in pygame.event.get(pygame.KEYDOWN):
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._transition_to(GameState.BOSS_FIGHT)
        if self._t >= self._duration:
            self._transition_to(GameState.BOSS_FIGHT)

    def draw(self, target: pygame.Surface) -> None:
        w, h = target.get_size()
        # Phase 1: white flash burst (first 0.2s)
        if self._t < 0.2:
            target.fill((255, 255, 255))
            return
        # BLOQUE 50: fast alarm pulse (8 Hz — twice the old 6 Hz feel)
        pulse = 0.5 + 0.5 * math.sin(self._t * 8.0)
        # BLOQUE 50: deep red background that intensifies with the pulse
        bg_r = int(60 + pulse * 80)   # 60-140 (was 40-70)
        bg_g = int(0)
        bg_b = int(0)
        target.fill((bg_r, bg_g, bg_b))
        # BLOQUE 50: alarm diagonal stripes overlay (subtle, alarm-style)
        stripe_alpha = int(30 + pulse * 30)
        stripe = pygame.Surface((w, h), pygame.SRCALPHA)
        stripe_spacing = 12
        for y in range(-h, h * 2, stripe_spacing * 2):
            pygame.draw.line(stripe, (255, 60, 60, stripe_alpha),
                             (0, y), (w, y + 40), 2)
        target.blit(stripe, (0, 0))
        # Phase 2: BIG RED WARNING text (slides + flashes)
        font = pygame.font.Font(None, 32)
        # Slide: text appears 0.2-1.0s
        text_alpha = min(1.0, max(0.0, (self._t - 0.2) / 0.4))
        # BLOQUE 50: red WARNING with boss name on second line
        warning_text = "!! WARNING !!"
        # BLOQUE 50: alarm flash — text toggles between bright red and dim red
        if int(self._t * 6) % 2 == 0:
            text_color = (255, 60, 60)
            glow_color = (200, 30, 30)
        else:
            text_color = (200, 30, 30)
            glow_color = (120, 20, 20)
        warn_surf = font.render(warning_text, True, text_color)
        warn_surf.set_alpha(int(255 * text_alpha))
        # Outer red glow (multi-layer)
        for i, alpha_mul in enumerate([0.7, 0.4, 0.2]):
            glow_surf = font.render(warning_text, True, glow_color)
            glow_surf.set_alpha(int(120 * alpha_mul * text_alpha))
            off = i + 1
            for ox, oy in [(-off, 0), (off, 0), (0, -off), (0, off)]:
                target.blit(glow_surf,
                            (w // 2 - warn_surf.get_width() // 2 + ox,
                             60 - warn_surf.get_height() // 2 + oy))
        target.blit(warn_surf,
                    (w // 2 - warn_surf.get_width() // 2,
                     60 - warn_surf.get_height() // 2))
        # Boss name (under the WARNING, in white with red glow)
        font_name = pygame.font.Font(None, 16)
        name_surf = font_name.render(self._boss_name, True, (255, 240, 220))
        name_surf.set_alpha(int(255 * text_alpha))
        # Red name glow
        for ox, oy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            g = font_name.render(self._boss_name, True, (255, 60, 60))
            g.set_alpha(int(100 * text_alpha))
            target.blit(g, (w // 2 - name_surf.get_width() // 2 + ox,
                            90 + oy))
        target.blit(name_surf, (w // 2 - name_surf.get_width() // 2, 90))
        # Phase 3: Boss portrait slides down from top (1.0s+)
        if self._t > 0.8:
            # Boss rectangle (dark red, with eye detail)
            boss_size = 36
            # Slide in: y starts at -boss_size, settles at 180
            target_y = 180
            start_y = -boss_size
            t_slide = min(1.0, (self._t - 0.8) / 0.8)
            t_eased = 1.0 - (1.0 - t_slide) ** 3  # ease-out
            boss_y = int(start_y + (target_y - start_y) * t_eased)
            boss_x = w // 2
            # BLOQUE 50: bigger red glow under boss (pulsing)
            glow_size = boss_size + 20
            glow = pygame.Surface((glow_size, glow_size), pygame.SRCALPHA)
            pygame.draw.rect(glow, (255, 40, 40, 80 + int(60 * pulse)),
                             (0, 0, glow_size, glow_size), border_radius=4)
            target.blit(glow, (boss_x - glow_size // 2, boss_y - glow_size // 2))
            # Boss body (darker red — almost black-red)
            boss_rect = pygame.Rect(boss_x - boss_size // 2, boss_y - boss_size // 4,
                                    boss_size, boss_size // 2)
            pygame.draw.rect(target, (140, 30, 30), boss_rect)
            # Inner darker rectangle
            inner = boss_rect.inflate(-max(2, boss_size // 3), -max(1, boss_size // 6))
            pygame.draw.rect(target, (80, 20, 20), inner)
            # Boss eye (white, glowing red border)
            eye_w = 14
            eye_h = 3
            pygame.draw.rect(target, (255, 80, 80),
                             (boss_x - eye_w // 2 - 1, boss_y - eye_h // 2 - 1,
                              eye_w + 2, eye_h + 2))
            pygame.draw.rect(target, (255, 255, 255),
                             (boss_x - eye_w // 2, boss_y - eye_h // 2, eye_w, eye_h))
            # Phase border (bright red, flashing)
            border_color = (255, 40, 40) if pulse > 0.5 else (180, 20, 20)
            pygame.draw.rect(target, border_color, boss_rect, 1)
        # Bottom: "INCOMING HOSTILE" subtitle (red, blinking)
        font2 = pygame.font.Font(None, 12)
        sub = font2.render("!! INCOMING HOSTILE !!", True, (255, 80, 80))
        if int(self._t * 4) % 2 == 0 and self._t > 0.5:
            _center_blit(target, sub, 250)
        # Progress bar (fills over duration, red)
        bar_w = 200
        bar_h = 4
        bar_x = (w - bar_w) // 2
        bar_y = 320
        pygame.draw.rect(target, (80, 20, 20), (bar_x, bar_y, bar_w, bar_h), 1)
        progress = min(1.0, self._t / self._duration)
        pygame.draw.rect(target, (255, 60, 60),
                         (bar_x + 1, bar_y + 1, int(bar_w * progress) - 2, bar_h - 2))
        # "PRESS ENTER TO SKIP" hint
        if self._t > 1.0:
            font3 = pygame.font.Font(None, 10)
            hint = font3.render("PRESS ENTER TO SKIP", True, (200, 160, 160))
            _center_blit(target, hint, 340)
            _center_blit(target, sub, 200)


class SubBossIntroScene(Scene):
    """SUB_BOSS_INTRO — BLOQUE 50: YELLOW WARNING intro for the mid-wave
    sub-boss. Same structure as BossIntroScene but with a yellow/amber
    palette and shorter duration (2.5s). The sub-boss is fast, hard to
    hit, and shoots a lot — the warning tells the player "incoming
    threat, but not as bad as a real boss".
    """

    def __init__(self, transition_to: TransitionFn,
                 audio: Optional["AudioEngine"] = None) -> None:
        self._transition_to = transition_to
        self._audio = audio
        self._t: float = 0.0
        self._duration: float = 2.5  # shorter than boss (4.5s)

    def on_enter(self) -> None:
        self._t = 0.0
        # BLOQUE 58.23: reuse the shared audio engine (see BossIntroScene).
        # Creating a new AudioEngine() here would re-bake all SFX + BGM
        # (~1.2s freeze) right when the sub-boss warning is supposed
        # to start playing.
        audio = self._audio
        if audio is None:
            try:
                from src.audio.synth import AudioEngine
                audio = AudioEngine()
            except Exception:
                return
        try:
            audio.play_sfx("boss_warning", volume=0.7)
        except Exception:
            pass

    def update(self, dt: float) -> None:
        self._t += dt
        for event in pygame.event.get(pygame.KEYDOWN):
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._transition_to(GameState.GAMEPLAY)
        if self._t >= self._duration:
            self._transition_to(GameState.GAMEPLAY)

    def draw(self, target: pygame.Surface) -> None:
        w, h = target.get_size()
        # White flash for the first 0.15s
        if self._t < 0.15:
            target.fill((255, 255, 255))
            return
        # Yellow background, gentler pulse than boss (5 Hz)
        pulse = 0.5 + 0.5 * math.sin(self._t * 5.0)
        bg_r = int(60 + pulse * 50)
        bg_g = int(50 + pulse * 30)
        bg_b = int(0)
        target.fill((bg_r, bg_g, bg_b))
        # Yellow diagonal stripes (subtler than boss red)
        stripe_alpha = int(20 + pulse * 20)
        stripe = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(-h, h * 2, 14):
            pygame.draw.line(stripe, (255, 200, 60, stripe_alpha),
                             (0, y), (w, y + 40), 2)
        target.blit(stripe, (0, 0))
        # WARNING text — yellow, flashing
        font = pygame.font.Font(None, 28)
        text_alpha = min(1.0, max(0.0, (self._t - 0.15) / 0.4))
        if int(self._t * 5) % 2 == 0:
            text_color = (255, 220, 80)
            glow_color = (200, 160, 40)
        else:
            text_color = (200, 160, 40)
            glow_color = (140, 110, 20)
        warn_surf = font.render("! WARNING !", True, text_color)
        warn_surf.set_alpha(int(255 * text_alpha))
        # Yellow glow
        for off in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            g = font.render("! WARNING !", True, glow_color)
            g.set_alpha(int(120 * text_alpha))
            target.blit(g, (w // 2 - warn_surf.get_width() // 2 + off[0],
                            80 - warn_surf.get_height() // 2 + off[1]))
        target.blit(warn_surf,
                    (w // 2 - warn_surf.get_width() // 2,
                     80 - warn_surf.get_height() // 2))
        # Sub-boss label below WARNING
        font_sub = pygame.font.Font(None, 14)
        sub = font_sub.render("HOSTILE FRENETIC", True, (255, 230, 140))
        sub.set_alpha(int(255 * text_alpha))
        _center_blit(target, sub, 110)
        # Mini ship preview (yellow dart, slides down from top)
        if self._t > 0.4:
            ship_y_target = 200
            t_slide = min(1.0, (self._t - 0.4) / 0.5)
            t_eased = 1.0 - (1.0 - t_slide) ** 3
            ship_y = int(-30 + (ship_y_target - -30) * t_eased)
            ship_x = w // 2
            # Yellow halo
            halo = pygame.Surface((50, 50), pygame.SRCALPHA)
            halo_alpha = 60 + int(40 * pulse)
            pygame.draw.ellipse(halo, (255, 200, 80, halo_alpha),
                                (0, 0, 50, 50), 1)
            target.blit(halo, (ship_x - 25, ship_y - 25))
            # Dart body (yellow)
            pygame.draw.polygon(target, (255, 200, 80), [
                (ship_x, ship_y - 12),
                (ship_x + 10, ship_y + 2),
                (ship_x + 4, ship_y + 8),
                (ship_x, ship_y + 4),
                (ship_x - 4, ship_y + 8),
                (ship_x - 10, ship_y + 2),
            ])
            # Red core (glowing)
            pygame.draw.circle(target, (255, 80, 80), (ship_x, ship_y), 2)
        # Progress bar (yellow, fills faster)
        bar_w = 200
        bar_h = 3
        bar_x = (w - bar_w) // 2
        bar_y = 320
        pygame.draw.rect(target, (100, 80, 30), (bar_x, bar_y, bar_w, bar_h), 1)
        progress = min(1.0, self._t / self._duration)
        pygame.draw.rect(target, (255, 220, 80),
                         (bar_x + 1, bar_y + 1, int(bar_w * progress) - 2, bar_h - 2))
        # "PRESS ENTER TO SKIP" hint
        if self._t > 0.5:
            font3 = pygame.font.Font(None, 10)
            hint = font3.render("PRESS ENTER TO SKIP", True, (220, 200, 140))
            _center_blit(target, hint, 340)


class BossFightScene(Scene):
    """BOSS_FIGHT — boss arena. Delegates to GameplayRuntime in boss mode."""

    def __init__(self, transition_to: "TransitionFn", act: int = 1,
                 audio: Optional["AudioEngine"] = None) -> None:
        self._transition_to = transition_to
        self._act = act
        from src.ui.gameplay_runtime import GameplayRuntime
        self._rt = GameplayRuntime(transition_to, is_boss=True, act=act, audio=audio)

    def on_enter(self) -> None:
        self._rt.on_enter()

    def on_exit(self) -> None:
        self._rt.on_exit()

    def update(self, dt: float) -> None:
        # ESC to pause; otherwise full runtime
        for event in pygame.event.get(pygame.KEYDOWN):
            if event.key == pygame.K_ESCAPE:
                self._transition_to(GameState.PAUSE)
        self._rt.update(dt)

    def draw(self, target: pygame.Surface) -> None:
        self._rt.draw(target)


class ActClearedScene(Scene):
    """ACT_CLEARED — act boss defeated, +25000 pts, act transition."""

    def __init__(self, transition_to: TransitionFn) -> None:
        self._transition_to = transition_to
        self._t: float = 0.0
        self._duration: float = 4.0

    def on_enter(self) -> None:
        self._t = 0.0

    def update(self, dt: float) -> None:
        self._t += dt
        if self._t >= self._duration:
            self._transition_to(GameState.ACT_INTRO)
        for event in pygame.event.get(pygame.KEYDOWN):
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._transition_to(GameState.ACT_INTRO)

    def draw(self, target: pygame.Surface) -> None:
        target.fill((0, 0, 0))
        # 28px fits "ACT CLEARED!" (12 chars) in 240px
        font = pygame.font.Font(None, 28)
        text = font.render("ACT CLEARED!", True, (255, 220, 100))
        _center_blit(target, text, 100)
        font2 = pygame.font.Font(None, 18)
        sub = font2.render("+25000 PTS", True, (255, 180, 40))
        _center_blit(target, sub, 200)


class GameOverScene(Scene):
    """GAME_OVER — 0 lives, end of run."""

    def __init__(self, transition_to: TransitionFn) -> None:
        self._transition_to = transition_to
        self._t: float = 0.0
        self._duration: float = 5.0

    def on_enter(self) -> None:
        self._t = 0.0

    def update(self, dt: float) -> None:
        self._t += dt
        if self._t >= self._duration:
            self._transition_to(GameState.TITLE)
        for event in pygame.event.get(pygame.KEYDOWN):
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._transition_to(GameState.TITLE)

    def draw(self, target: pygame.Surface) -> None:
        target.fill((40, 0, 0))
        # 32px fits "GAME OVER" (9 chars) in 240px
        font = pygame.font.Font(None, 32)
        text = font.render("GAME OVER", True, (255, 60, 40))
        _center_blit(target, text, 140)


class VictoryScene(Scene):
    """VICTORY — final boss defeated, runs after NEMESIS dies."""

    def __init__(self, transition_to: TransitionFn) -> None:
        self._transition_to = transition_to
        self._t: float = 0.0
        self._duration: float = 6.0

    def on_enter(self) -> None:
        self._t = 0.0

    def update(self, dt: float) -> None:
        self._t += dt
        if self._t >= self._duration:
            self._transition_to(GameState.CREDITS)

    def draw(self, target: pygame.Surface) -> None:
        target.fill((40, 30, 0))
        # 40px fits "VICTORY!" (8 chars) in 240px
        font = pygame.font.Font(None, 40)
        text = font.render("VICTORY!", True, (255, 220, 100))
        _center_blit(target, text, 140)


class CreditsScene(Scene):
    """CREDITS — final roll, "PRESS ENTER FOR TITLE"."""

    def __init__(self, transition_to: TransitionFn) -> None:
        self._transition_to = transition_to
        self._t: float = 0.0

    def update(self, dt: float) -> None:
        self._t += dt
        for event in pygame.event.get(pygame.KEYDOWN):
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._transition_to(GameState.TITLE)

    def draw(self, target: pygame.Surface) -> None:
        target.fill((0, 0, 0))
        # Title (small)
        title_font = pygame.font.Font(None, 20)
        title = title_font.render("VOID HUNTER", True, (255, 220, 100))
        _center_blit(target, title, 30)
        # Body — wrap to fit 240px
        body_font = pygame.font.Font(None, 12)
        body_lines = [
            "A shmup by Lerius",
            "",
            "Built on Pygame 2.6 + Python 3.11",
            "120 FPS lock",
            "Zero external deps",
            "(numpy/scipy prohibited)",
            "",
            "Thanks to: Cave, Touhou, Ikaruga,",
            "DoDonPachi, Gradius, R-Type,",
            "Metal Slug, Devil May Cry",
            "",
            f"Run time: {int(self._t)}s",
            "",
            "PRESS ENTER FOR TITLE",
        ]
        y = 70
        for line in body_lines:
            text = body_font.render(line, True, (200, 200, 220))
            _center_blit(target, text, y)
            y += 16


class PauseScene(Scene):
    """PAUSE overlay — dim screen, 'PAUSED' text, ESC to resume."""

    def __init__(self, transition_to: TransitionFn) -> None:
        self._transition_to = transition_to

    def update(self, dt: float) -> None:
        for event in pygame.event.get(pygame.KEYDOWN):
            if event.key == pygame.K_ESCAPE:
                self._transition_to(GameState.GAMEPLAY)  # will pop overlay

    def draw(self, target: pygame.Surface) -> None:
        # Dim overlay
        dim = pygame.Surface(target.get_size(), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 128))
        target.blit(dim, (0, 0))
        # 48px fits "PAUSED" (6 chars) in 240px
        font = pygame.font.Font(None, 48)
        text = font.render("PAUSED", True, (255, 255, 255))
        _center_blit(target, text, 140)
        font2 = pygame.font.Font(None, 14)
        sub = font2.render("ESC to resume", True, (200, 200, 200))
        _center_blit(target, sub, 220)
