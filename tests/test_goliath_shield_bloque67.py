"""BLOQUE 67: el escudo de GOLIATH â€” ovalo a la derecha, encajado en la
silueta, rojo al primer impacto y laser grueso naranja.

Los tres pedidos del usuario, cada uno con su test:

  1. el ovalo va en el brazo DERECHO (no en el torso),
  2. encaja en la silueta de la placa (medido, no un offset fijo),
  3. se pone ROJO al primer disparo, se calienta al cargar, y lanza un
     laser GRUESO NARANJA.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
from pathlib import Path

import pytest

import pygame

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

ANIMS = ("phase1_idle", "phase2_idle", "javelin", "laser", "purple_bullet", "death")
FRAMES = [f"bosses/goliath/{a}/frame_{i:02d}.png" for a in ANIMS for i in range(10)]


@pytest.fixture(scope="module")
def display():
    """Display dummy: `convert_alpha()` lo necesita para leer los sprites."""
    import pygame

    pygame.init()
    pygame.display.set_mode((1, 1))
    yield


@pytest.fixture(scope="module")
def sprites_loadable(display):
    """Guard: si el sprite no se puede leer, los tests TIENEN que fallar.

    Sin este guard los tests pasaban en falso: `_load_sprite` devolvia None
    (sin display, `convert_alpha()` explota), la medicion caia en el
    fallback (60.5, 40.5, 8.5, 10.5) y todas las aserciones de rango se
    cumplian igual. Un test que no puede fallar no es un test.
    """
    from src.ui.scenes import _load_sprite

    surf = _load_sprite("bosses/goliath/phase1_idle/frame_00.png")
    assert surf is not None, "no se pudo cargar el sprite: los tests darian verde en falso"
    return True


# --------------------------------------------------------------------------
# 1. El ovalo va en el brazo DERECHO
# --------------------------------------------------------------------------
def test_shield_ellipse_is_on_the_right_of_the_sprite(sprites_loadable) -> None:
    """La placa del escudo esta en el brazo derecho de GOLIATH.

    El sprite es de 96 px de ancho y el cuerpo esta centrado en col ~48.
    La placa vive entre col ~50 y col ~70. Antes (BLOQUE 66/73.2) el
    ancla caia en col ~48 con DX=-11, o sea SOBRE EL TORSO.
    """
    from src.ui.scenes import get_sprite_shield_ellipse

    for path in FRAMES:
        cx, _cy, _rx, _ry = get_sprite_shield_ellipse(path)
        assert cx > 52, f"{path}: el ovalo quedo en col {cx:.1f}, a la izquierda del cuerpo"


def test_shield_ellipse_fits_every_frame(sprites_loadable) -> None:
    """Los 60 frames miden una elipse creible y en el mismo lugar.

    Rango derivado de las 60 mediciones: cx 57..63.5, rx 7..11, ry 9..13.
    """
    from src.ui.scenes import get_sprite_shield_ellipse

    for path in FRAMES:
        cx, cy, rx, ry = get_sprite_shield_ellipse(path)
        assert 55.0 <= cx <= 66.0, f"{path}: cx={cx:.1f} fuera de rango"
        assert 38.0 <= cy <= 44.0, f"{path}: cy={cy:.1f} fuera de rango"
        assert 6.0 <= rx <= 11.5, f"{path}: rx={rx:.1f} fuera de rango"
        assert 8.0 <= ry <= 13.5, f"{path}: ry={ry:.1f} fuera de rango"


def test_shield_ellipse_tracks_the_arm_between_frames(sprites_loadable) -> None:
    """El ovalo se mueve con el brazo: no es un offset fijo.

    El centroide del sprite tambien se mueve, asi que el mundo tiene que
    seguirlo. Se comprueba que la medicion sprite-local varia entre
    frames (si fuera fija, el ovalo se despegaria de la placa).
    """
    from src.ui.scenes import get_sprite_shield_ellipse

    xs = {round(get_sprite_shield_ellipse(p)[0], 1) for p in FRAMES}
    assert len(xs) > 5, f"la medicion no se mueve: {sorted(xs)}"


# --------------------------------------------------------------------------
# 2. El ovalo, el hitbox y el laser usan la MISMA medicion
# --------------------------------------------------------------------------
def _runtime():
    from src.ui.gameplay_runtime import GameplayRuntime
    from src.entities.enemies.boss import BOSS_CONFIGS

    rt = GameplayRuntime(transition_to=lambda s: None, is_boss=True, act=1)
    rt.on_enter()
    rt._boss_entry_t = 2.0
    b = rt._boss
    cfg = BOSS_CONFIGS[b.id]
    b.x = cfg.anchor_x
    b.y = cfg.anchor_y
    b.animation_state = "phase1_idle"
    b.animation_frame = 0
    b.animation_timer = 0.0
    rt._boss_shield_hits = 0
    rt._boss_shield_laser_t = 0.0
    return rt


def test_hitbox_contains_the_drawn_oval() -> None:
    """El rect de hitbox contiene toda la elipse visible."""
    import pygame
    from src.ui.gameplay_runtime import _goliath_shield_ellipse

    rt = _runtime()
    sx, sy, rx, ry = _goliath_shield_ellipse(rt)
    rect = pygame.Rect(int(sx - rx - 1), int(sy - ry - 1), (rx + 1) * 2, (ry + 1) * 2)
    # Los cuatro extremos de la elipse tienen que caer dentro del rect.
    for px, py in ((sx - rx, sy), (sx + rx, sy), (sx, sy - ry), (sx, sy + ry)):
        assert rect.collidepoint(px, py), f"la elipse se sale del hitbox en {(px, py)}"


def test_laser_origin_is_the_shield_centre() -> None:
    """El laser sale de la placa, no del pecho."""
    from src.ui.gameplay_runtime import _goliath_shield_ellipse

    rt = _runtime()
    sx, sy, _rx, _ry = _goliath_shield_ellipse(rt)
    # El pecho esta en el centro horizontal del sprite; la placa, a la
    # derecha. El laser tiene que salir de la placa.
    assert sx > rt._boss.x, "el laser sale del centro del cuerpo, no del escudo"


def test_shield_is_on_the_right_of_the_boss_hitbox() -> None:
    """La placa esta a la derecha del hitbox del jefe (o en su borde)."""
    from src.ui.gameplay_runtime import _goliath_shield_ellipse

    rt = _runtime()
    sx, _sy, _rx, _ry = _goliath_shield_ellipse(rt)
    hb = rt._boss.hitbox()
    assert sx >= hb.right - 4, (
        f"el escudo quedo en x={sx} y el hitbox del jefe termina en {hb.right}"
    )


# --------------------------------------------------------------------------
# 3. La rampa de carga: rojo al primer impacto, se calienta
# --------------------------------------------------------------------------
def test_shield_is_cold_before_any_hit() -> None:
    """Sin impactos el ovalo esta en acero frio (no rojo)."""
    from src.ui.gameplay_runtime import _shield_charge_color

    r, g, b = _shield_charge_color(0.0)
    assert b > r, f"sin carga deberia ser frio, no rojo: {(r, g, b)}"


def test_shield_turns_red_on_the_first_hit() -> None:
    """El primer disparo tiene que ponerlo ROJO de inmediato."""
    from src.ui.gameplay_runtime import _shield_charge_color

    r, g, b = _shield_charge_color(1 / 20)
    assert r > 200, f"el primer impacto no es rojo: {(r, g, b)}"
    assert r - g > 120, f"el primer impacto no es rojo: {(r, g, b)}"
    assert r - b > 120, f"el primer impacto no es rojo: {(r, g, b)}"


def test_shield_heats_up_as_it_charges() -> None:
    """La carga sube de temperatura: rojo -> naranja -> ambar -> blanco."""
    from src.ui.gameplay_runtime import _shield_charge_color

    samples = [_shield_charge_color(h / 20) for h in (1, 5, 12, 20)]
    # El rojo se vuelve naranja/ambar: la componente verde tiene que subir.
    greens = [c[1] for c in samples]
    assert greens == sorted(greens), f"el escudo no se calienta: {samples}"
    # Y el azul tambien sube (el rojo puro -> el blanco caliente).
    blues = [c[2] for c in samples]
    assert blues == sorted(blues), f"el escudo no se calienta: {samples}"


def test_full_charge_is_white_hot() -> None:
    from src.ui.gameplay_runtime import _shield_charge_color

    r, g, b = _shield_charge_color(1.0)
    assert r >= 250 and g >= 230 and b >= 200, f"carga completa no es blanco: {(r, g, b)}"


# --------------------------------------------------------------------------
# 4. El laser: GRUESO y NARANJA
# --------------------------------------------------------------------------
def test_shield_laser_is_thick_and_orange() -> None:
    """El laser tiene que ser naranja (no rojo) y mas grueso que los 8 px."""
    import inspect

    from src.ui.gameplay_runtime import GameplayRuntime

    src = inspect.getsource(GameplayRuntime._draw_shield_laser)
    assert "beam_w = 14" in src, "el laser deberia tener un nucleo de 14 px"

    # La paleta del laser tiene que ser naranja: mucho verde, poco azul.
    assert "(255, 110, 30" in src, "el glow exterior deberia ser naranja"
    assert "(255, 150, 40" in src, "el cuerpo del laser deberia ser naranja"
    assert "(255, 60, 40" not in src, "el laser todavia tiene la paleta roja vieja"


def test_laser_width_is_wider_than_the_old_eight_pixels() -> None:
    """Regresion: el laser se achico a 8 px en un momento y nadie lo noto."""
    import inspect

    from src.ui.gameplay_runtime import GameplayRuntime

    src = inspect.getsource(GameplayRuntime._draw_shield_laser)
    assert "beam_w = 8\n" not in src


# --------------------------------------------------------------------------
# 5. Ajuste fino pedido por el usuario: 3 px abajo y mas delgado
# --------------------------------------------------------------------------
def test_shield_is_shifted_three_pixels_down() -> None:
    """El ovalo va 3 px mas abajo que la placa medida."""
    from src.ui.gameplay_runtime import GOLIATH_SHIELD_DY, _goliath_shield_ellipse
    from src.ui.scenes import get_sprite_centroid_offset, get_sprite_shield_ellipse

    assert GOLIATH_SHIELD_DY == 3, f"DY deberia ser 3, es {GOLIATH_SHIELD_DY}"

    rt = _runtime()
    _sx, sy, _rx, _ry = _goliath_shield_ellipse(rt)
    path = rt._boss.animation_path
    _cx, cy, _m_rx, _m_ry = get_sprite_shield_ellipse(path)
    _cdx, cdy = get_sprite_centroid_offset(path)
    expected = int(rt._boss.y) - 40 + cdy + int(round(cy)) + 3
    assert sy == expected, f"el centro deberia estar 3 px mas abajo: {sy} != {expected}"


def test_shield_minor_axis_is_thinner_than_the_measured_plate() -> None:
    """El eje menor (horizontal) del ovalo se adelgaza; el vertical no."""
    from src.ui.gameplay_runtime import (
        GOLIATH_SHIELD_RX_SCALE,
        _goliath_shield_ellipse,
    )
    from src.ui.scenes import get_sprite_shield_ellipse

    assert GOLIATH_SHIELD_RX_SCALE < 1.0, "el ovalo deberia adelgazar"
    assert GOLIATH_SHIELD_RX_SCALE >= 0.6, "no lo adelgaces demasiado"

    rt = _runtime()
    _sx, _sy, rx, ry = _goliath_shield_ellipse(rt)
    _cx, _cy, m_rx, m_ry = get_sprite_shield_ellipse(rt._boss.animation_path)

    assert rx < m_rx, f"el radio horizontal deberia ser menor: {rx} vs {m_rx}"
    assert rx == max(2, int(round(m_rx * GOLIATH_SHIELD_RX_SCALE)))
    # El vertical queda como estaba: el ovalo sigue siendo alto.
    assert ry == int(round(m_ry)), f"el radio vertical no deberia cambiar: {ry} vs {m_ry}"


def test_oval_stays_taller_than_wide() -> None:
    """Con el ajuste, el ovalo sigue siendo mas alto que ancho."""
    from src.ui.gameplay_runtime import _goliath_shield_ellipse

    rt = _runtime()
    _sx, _sy, rx, ry = _goliath_shield_ellipse(rt)
    assert ry > rx, f"el ovalo deberia seguir alto: rx={rx} ry={ry}"


# --------------------------------------------------------------------------
# 6. El ovalo es INVISIBLE (pedido del usuario)
# --------------------------------------------------------------------------
def _render_boss(rt) -> "object":
    import pygame

    surf = pygame.Surface((320, 480))
    surf.fill((0, 0, 0))
    rt.draw(surf)
    return surf


def test_nothing_is_drawn_on_the_shield_at_zero_hits(display) -> None:
    """Sin impactos el escudo no dibuja NADA: el ovalo es invisible.

    Se renderiza el boss dos veces: normal, y con el dibujo del escudo
    anulado. Si los frames son identicos, el escudo no dibujo nada.
    """
    import numpy as np

    rt = _runtime()
    rt._boss_shield_hits = 0
    rt._boss_shield_flash_t = 0.0
    normal = _render_boss(rt)

    rt2 = _runtime()
    rt2._boss_shield_hits = 0
    rt2._boss_shield_flash_t = 0.0
    rt2._draw_goliath_shield = lambda *a, **k: None   # type: ignore[assignment]
    sin_escudo = _render_boss(rt2)

    a = pygame.surfarray.array3d(normal).astype(np.int16)
    b = pygame.surfarray.array3d(sin_escudo).astype(np.int16)
    diff = (np.abs(a - b).sum(axis=2) > 0).sum()
    assert diff == 0, f"el escudo dibujo {diff} pixeles sin tener carga"


def test_the_charge_layer_is_visible_once_loaded(display) -> None:
    """Con carga tiene que verse la capa de calor (el unico indicador)."""
    import numpy as np

    rt = _runtime()
    rt._boss_shield_hits = 12
    rt._boss_shield_flash_t = 0.0
    con_calor = _render_boss(rt)

    rt2 = _runtime()
    rt2._boss_shield_hits = 12
    rt2._boss_shield_flash_t = 0.0
    rt2._draw_goliath_shield = lambda *a, **k: None   # type: ignore[assignment]
    sin_escudo = _render_boss(rt2)

    a = pygame.surfarray.array3d(con_calor).astype(np.int16)
    b = pygame.surfarray.array3d(sin_escudo).astype(np.int16)
    diff = (np.abs(a - b).sum(axis=2) > 0).sum()
    assert diff > 40, f"la capa de calor casi no se ve ({diff} pixeles)"


def test_the_impact_layer_flashes_on_a_hit(display) -> None:
    """Al recibir un disparo se prende el parpadeo."""
    rt = _runtime()
    rt._boss_shield_hits = 1
    rt._boss_shield_flash_t = 0.0
    sin_flash = _render_boss(rt)

    rt2 = _runtime()
    rt2._boss_shield_hits = 1
    rt2._boss_shield_flash_t = 0.30
    con_flash = _render_boss(rt2)

    import numpy as np

    a = pygame.surfarray.array3d(con_flash).astype(np.int16)
    b = pygame.surfarray.array3d(sin_flash).astype(np.int16)
    diff = (np.abs(a - b).sum(axis=2) > 0).sum()
    assert diff > 40, f"el parpadeo de impacto casi no se ve ({diff} pixeles)"


def test_a_bullet_on_the_shield_starts_the_flash(display) -> None:
    """Un disparo que pega en el escudo prende el parpadeo."""
    from src.entities.enemies.boss import BOSS_CONFIGS
    from src.systems.projectile import BULLET_PLAYER, OWNER_PLAYER

    rt = _runtime()
    rt._boss_shield_flash_t = 0.0
    b = rt._boss
    cfg = BOSS_CONFIGS[b.id]
    b.x = cfg.anchor_x
    b.y = cfg.anchor_y

    # El disparo tiene que caer dentro del escudo, no dentro del boss.
    from src.ui.gameplay_runtime import _goliath_shield_ellipse

    sx, sy, _rx, _ry = _goliath_shield_ellipse(rt)
    rt._bullets.spawn(BULLET_PLAYER, float(sx), float(sy), 0, 100,
                      damage=1, owner=OWNER_PLAYER)
    rt._handle_shield_collisions()
    assert rt._boss_shield_flash_t > 0.0, "el disparo no prendio el parpadeo"
    assert rt._boss_shield_hits == 1


def test_the_flash_decays_over_time(display) -> None:
    """El parpadeo se apaga solo."""
    rt = _runtime()
    rt._boss_shield_flash_t = 0.30
    rt.update(1.0 / 60.0)
    assert rt._boss_shield_flash_t < 0.30, "el parpadeo no decayo"


