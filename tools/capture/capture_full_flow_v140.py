"""BLOQUE 67: smoke test end-to-end del flujo nuevo + evidencia visual.

Recorre, sin ventana, la cadena completa:

    TITLE -> CINEMATIC -> MENU -> ACT_INTRO -> GAMEPLAY

y ejercita las dos features nuevas:

  1. MENU (BLOQUE 73.7): NEW GAME / BOSS TIME / BACKGROUND, y el submenu
     SPACE VOID / ASTEROID NEBULA.
  2. bg_mode (BLOQUE 73.8): renderiza el MISMO frame de gameplay en modo 0
     y en modo 1 y mide el porcentaje de pixeles distintos. Si el back-ref
     _game no llegara al runtime, daria ~0% -- ese fue el defecto que se
     publico inerte en v1.6.3.

Uso:
    python tools/capture/capture_full_flow_v140.py

Salida: tools/playtest_out/flow_*.png + un resumen por stdout.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import pygame  # noqa: E402

pygame.init()
pygame.display.set_mode((320, 480))

from src.core.game import Game  # noqa: E402
from src.core.scene_manager import GameState  # noqa: E402

OUT = ROOT / "tools" / "playtest_out"
OUT.mkdir(parents=True, exist_ok=True)

SCENE: list[str] = []


def trace(label: str) -> None:
    SCENE.append(label)
    print(f"  {label}")


def key(k: int) -> None:
    """Encola un KEYDOWN y lo drena con un update de la escena activa."""
    pygame.event.clear(pygame.KEYDOWN)
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=""))
    pygame.event.pump()
    scene = game.scenes.scenes.get(game.scenes.current_state)
    if scene is not None:
        scene.update(1.0 / 60.0)


def save(name: str, surf: pygame.Surface) -> None:
    path = OUT / name
    pygame.image.save(pygame.transform.scale(surf, (320 * 3, 480 * 3)), str(path))
    print(f"    -> {path.name}")


def draw_current() -> pygame.Surface:
    surf = pygame.Surface((320, 480))
    surf.fill((0, 0, 0))
    scene = game.scenes.scenes.get(game.scenes.current_state)
    if scene is not None:
        scene.draw(surf)
    return surf


print("=" * 64)
print("BLOQUE 67 — smoke del flujo completo (v1.4.0 + GOLIATH + menu)")
print("=" * 64)

game = Game()
print(f"\n[1] TITLE -> CINEMATIC -> MENU")
trace(f"arranque en {game.scenes.current_state.name}")

# TITLE -> CINEMATIC (la transicion normal la dispara una tecla)
game.scenes.transition_to(GameState.CINEMATIC)
trace(f"transicion a {game.scenes.current_state.name}")

# ESC saltea la cinematica -> MENU
key(pygame.K_ESCAPE)
trace(f"ESC en cinematica -> {game.scenes.current_state.name}")

if game.scenes.current_state is not GameState.MENU:
    print("  !! la cinematica no encadeno al MENU")
    sys.exit(1)

menu = game.scenes.scenes[GameState.MENU]

print(f"\n[2] MENU: items = {menu._items()}")
for i, label in enumerate(menu._ITEMS_TOP):
    menu._cursor = i
    trace(f"menu cursor {i} = {label}")
    save(f"flow_menu_{i}_{label.lower().replace(' ', '_')}.png", draw_current())

print(f"\n[3] Submenu BACKGROUND")
menu._cursor = 2
key(pygame.K_RETURN)          # abre el submenu
trace(f"layer = {menu._layer}, items = {menu._items()}")
save("flow_menu_bg_submenu.png", draw_current())

# SPACE VOID (modo 0)
key(pygame.K_1)
trace(f"pulsado 1 -> bg_mode = {game.bg_mode} (esperado 0)")
assert game.bg_mode == 0, f"bg_mode deberia ser 0, es {game.bg_mode}"
save("flow_menu_bg_applied_space_void.png", draw_current())

# ASTEROID NEBULA (modo 1)
menu._cursor = 2
key(pygame.K_RETURN)
key(pygame.K_2)
trace(f"pulsado 2 -> bg_mode = {game.bg_mode} (esperado 1)")
assert game.bg_mode == 1, f"bg_mode deberia ser 1, es {game.bg_mode}"
save("flow_menu_bg_applied_asteroid_nebula.png", draw_current())

# ESC en el submenu vuelve al top SIN aplicar
menu._cursor = 2
key(pygame.K_RETURN)
key(pygame.K_ESCAPE)
trace(f"ESC en submenu -> layer = {menu._layer}, bg_mode sigue = {game.bg_mode}")
assert menu._layer == "top", "ESC deberia volver al top"
assert game.bg_mode == 1, "ESC en el submenu no debe cambiar el bg_mode"

print(f"\n[4] ESC en el menu top -> TITLE")
key(pygame.K_ESCAPE)
trace(f"ESC en menu top -> {game.scenes.current_state.name}")
assert game.scenes.current_state is GameState.TITLE

# Volvemos al menu para seguir con NEW GAME (TITLE -> CINEMATIC -> MENU)
game.scenes.transition_to(GameState.CINEMATIC)
key(pygame.K_ESCAPE)
trace(f"de vuelta en {game.scenes.current_state.name}")
menu = game.scenes.scenes[GameState.MENU]

print(f"\n[5] MENU -> NEW GAME -> ACT_INTRO -> GAMEPLAY")
menu._cursor = 0
key(pygame.K_RETURN)
trace(f"NEW GAME -> {game.scenes.current_state.name}")
assert game.scenes.current_state is GameState.ACT_INTRO

# La cinematica de act intro dura 4s; la saltamos con ENTER
key(pygame.K_RETURN)
trace(f"ENTER en act intro -> {game.scenes.current_state.name}")
assert game.scenes.current_state is GameState.GAMEPLAY

gp = game.scenes.scenes[GameState.GAMEPLAY]

# Tick para que aparezcan enemigos/proyectiles y el frame no sea negro.
print(f"\n[6] Gameplay: 180 ticks para poblar la escena")
for _ in range(180):
    gp.update(1.0 / 60.0)
trace(f"{gp._rt.__class__.__name__} vivo, boss={gp._rt._boss}")

print(f"\n[7] bg_mode 0 vs 1 sobre el MISMO frame de gameplay")
frames = {}
for mode in (0, 1):
    game.bg_mode = mode
    surf = pygame.Surface((320, 480))
    surf.fill((0, 0, 0))
    gp.draw(surf)
    frames[mode] = surf
    save(f"flow_gameplay_bg{mode}.png", surf)

import numpy as np  # noqa: E402

a = pygame.surfarray.array3d(frames[0]).astype(np.int16)
b = pygame.surfarray.array3d(frames[1]).astype(np.int16)
diff = (np.abs(a - b).sum(axis=2) > 0).mean() * 100.0
print(f"    pixeles distintos entre bg_mode 0 y 1: {diff:.2f}%")
if diff < 50.0:
    print("  !! el selector de fondo esta INERTE (esperado >50%)")
    sys.exit(1)

print(f"\n[8] GAMEPLAY -> BOSS_INTRO -> BOSS_FIGHT (BOSS TIME)")
game.scenes.transition_to(GameState.BOSS_INTRO)
trace(f"transicion a {game.scenes.current_state.name}")
game.scenes.transition_to(GameState.BOSS_FIGHT)
trace(f"transicion a {game.scenes.current_state.name}")
boss_scene = game.scenes.scenes[GameState.BOSS_FIGHT]
for _ in range(180):
    boss_scene.update(1.0 / 60.0)
rt = boss_scene._rt
trace(f"boss vivo: id={rt._boss.id if rt._boss else None}, "
      f"anim={rt._boss.animation_state if rt._boss else '-'}, "
      f"frame={rt._boss.animation_frame if rt._boss else '-'}")
save("flow_boss_fight.png", draw_current())

print("\n" + "=" * 64)
print("TRACE DE ESTADOS")
for i, s in enumerate(SCENE, 1):
    print(f"  {i:2}. {s}")
print("=" * 64)
print("SMOKE OK — flujo completo sin excepciones.")
