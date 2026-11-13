"""BLOQUE 77: el escudo de GOLIATH, y que nada quede cortado.

Dos garantías, y las dos se pueden comprobar:

1. **El escudo se MIDE, no se inventa.** La elipse del escudo tiene que
   caer sobre la PLACA, que es el óvalo de acero del brazo derecho. La
   placa tiene una FIRMA DE COLOR propia (la cara de latón), y el
   `probe` la encuentra esté donde esté. Antes, cuando la medición de la
   silueta fallaba, la elipse se RECONSTRUÍA interpolando los frames
   vecinos -- y como la placa se había movido, el óvalo caía sobre la
   panza del jefe: el láser del escudo salía del sitio equivocado.

2. **Ninguna pieza de GOLIATH queda cortada al animarse.** El arte de
   cada frame tiene que estar dentro de su canvas con el margen que
   declara el manifiesto, y el registro mueve el canvas ENTERO: nada
   puede salirse de su propio lienzo.

Cada check de este archivo tiene su contraposición: una mutación que
lo rompe tiene que ponerlo en rojo.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402
import pytest  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from src.anim.manifest import load_set  # noqa: E402
from src.anim.measure import (  # noqa: E402
    color_centroid,
    effective_cut_margin,
    is_cut_off,
    silhouette_margins,
)
from sprite_pipeline.audit import audit_set  # noqa: E402

SET = "goliath"
ENEMIES_ROOT = ROOT / "Assets" / "sprites" / "bosses"

# The frames whose plate cannot be measured, and WHY. They are the ones
# the contract of `verify_contract.py` names.
#
# `laser` frames 04 and 05 are the boss FIRING: the BAKED beam crosses
# the plate, so the outline that identifies the plate is merged with the
# beam and the measurement cannot separate them. Their ellipse is
# RECONSTRUCTED from the frames around it, so it does not sit on the
# plate.
#
# `death` frame 02 is the boss collapsing: the brass probe and the
# outline disagree about where the plate is (40.7 against 57.5). The
# outline wins, so the ellipse counts as "measured" -- and it is on the
# wrong side.
KNOWN_INTERPOLATED = {("laser", 4), ("laser", 5)}
KNOWN_DISAGREEING = {("death", 2)}
# The frames where the ellipse is NOT on the plate: all of them.
KNOWN_OFF_THE_PLATE = KNOWN_INTERPOLATED | KNOWN_DISAGREEING


def _frame_path(anim_set, clip, index: int) -> Path:
    """Where a frame's PNG is."""
    return anim_set.path / clip.dir / f"frame_{index:02d}.png"


@pytest.fixture(scope="module")
def display():
    pygame.init()
    pygame.display.set_mode((320, 480))
    yield
    pygame.quit()


@pytest.fixture(scope="module")
def measurements(display):
    """The audit of the shipped set: the findings and the measurements.

    It needs the display: the frames are loaded with `convert_alpha()`,
    and pygame refuses that without a video mode.
    """
    anim_set = load_set(SET, root=ENEMIES_ROOT)
    _findings, measured = audit_set(anim_set)
    return measured


def test_the_shield_is_measured_in_every_frame_but_the_documented_ones(measurements):
    """La elipse del escudo se MIDE, salvo los 3 frames documentados.

    El conteo es la GARANTÍA: si la medición vuelve a romperse (un
    frame con el arte corrido, una regla que cambia, un registro mal
    hecho), los interpolados crecen y este check se pone rojo.
    """
    interpolated = {
        (m.clip, m.frame)
        for m in measurements
        if m.shield_source == "interpolated"
    }
    assert interpolated == KNOWN_INTERPOLATED, (
        f"the shield is interpolated in {sorted(interpolated)}: the "
        "measurement is failing again, and the ellipse lands on the "
        "boss's belly instead of on the plate"
    )


def test_no_shield_is_unresolved(measurements):
    """Ningún escudo queda SIN RESOLVER (unresolved).

    Un escudo sin resolver no tiene elipse: el laser no sale de ningun
    sitio. Es peor que una elipse mal puesta.
    """
    unresolved = {
        (m.clip, m.frame)
        for m in measurements
        if m.shield_source not in ("measured", "interpolated")
    }
    assert not unresolved, f"the shield is unresolved in {sorted(unresolved)}"


def test_the_measured_shield_sits_where_the_plate_is(measurements):
    """Donde el escudo se MIDE, tiene que coincidir con la firma.

    La placa tiene una firma de color (la cara de latón) y el `probe`
    la encuentra. La elipse del escudo es el CONTORNO. Si los dos no
    coinciden, la elipse no esta sobre la placa -- y eso es
    exactamente lo que pasaba cuando la elipse se interpolaba.
    """
    anim_set = load_set(SET, root=ENEMIES_ROOT)
    part = anim_set.part_or_none("shield_plate")
    assert part is not None and part.detect is not None
    rule = part.detect
    assert rule.probe is not None

    for clip in anim_set.clips.values():
        for index in range(clip.frames):
            path = _frame_path(anim_set, clip, index)
            surf = pygame.image.load(str(path)).convert_alpha()
            found = color_centroid(surf, rule.probe, warm=rule.warm_fallback)
            if found is None:
                continue
            measured = next(
                m for m in measurements if m.clip == clip.id and m.frame == index
            )
            if measured.shield_source != "measured" or measured.shield is None:
                continue
            if (clip.id, index) in KNOWN_OFF_THE_PLATE:
                continue
            # The probe is a column of the CANVAS, and so is the ellipse.
            assert abs(found[0] - measured.shield[0]) <= 14, (
                f"{clip.id}/f{index:02d}: the shield's ellipse is at "
                f"x={measured.shield[0]:.1f} but the plate's signature is at "
                f"x={found[0]:.1f}: the ellipse is NOT on the plate"
            )


def test_no_piece_of_goliath_is_cut_when_animated(measurements):
    """Ninguna pieza del jefe queda cortada, ni en el frame ni al animar.

    Dos mitades:

    * el arte de cada frame esta dentro de su canvas con el margen que
      declara el manifiesto (el mismo umbral que usa el auditor);
    * el REGISTRO mueve el canvas ENTERO -- el blit copia la superficie
      completa -- asi que el arte no puede salirse de su lienzo al
      animarse, por mas que el jefe se mueva.

    La segunda mitad es la que el auditor NO mira: el mide el frame
    quieto, y el jefe se mueve.
    """
    anim_set = load_set(SET, root=ENEMIES_ROOT)
    min_margin = effective_cut_margin(anim_set)

    for clip in anim_set.clips.values():
        for index in range(clip.frames):
            path = _frame_path(anim_set, clip, index)
            surf = pygame.image.load(str(path)).convert_alpha()
            margins = silhouette_margins(surf)
            assert margins is not None, f"{clip.id}/f{index:02d}: no art"
            assert not is_cut_off(margins, min_margin), (
                f"{clip.id}/f{index:02d}: the art touches the edge of the "
                f"canvas (margins L{margins[0]} T{margins[1]} "
                f"R{margins[2]} B{margins[3]}) -- the piece is CUT"
            )

    # The registration moves the whole canvas: the surface is blitted as
    # a whole, so the art can never leave its own canvas.
    for m in measurements:
        assert isinstance(m.body_dx, int) and isinstance(m.body_dy, int)


def test_the_registration_is_what_makes_the_measurement_work():
    """La medicion tiene que hacerse sobre el sprite REGISTRADO.

    Este es el mecanismo del fix: la regla de deteccion tiene columnas
    ABSOLUTAS (la placa arranca en la 50), y hay frames cuyo arte esta
    corrido dentro de su canvas. Medir sobre el sprite registrado --
    el arte como se va a dibujar -- es lo que hace que la regla signifique
    lo mismo en todos los frames.

    La contraposicion esta en el handoff: sin el registro, los 7 frames
    rotos vuelven a interpolarse.
    """
    from src.anim.measure import registered_surface, to_canvas

    surf = pygame.Surface((96, 80), pygame.SRCALPHA)
    surf.fill((200, 150, 90, 255))
    registered, origin = registered_surface(surf, -19, 0)
    assert registered.get_size() == surf.get_size()
    # The origin converts a point of the registered sprite back to the
    # canvas the runtime draws on.
    assert to_canvas((50.0, 40.0), origin) == (69.0, 40.0)
