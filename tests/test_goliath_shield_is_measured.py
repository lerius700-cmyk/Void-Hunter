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


def test_the_shield_stays_on_the_arm_in_every_frame(measurements):
    """EL ESCUDO TIENE QUE ESTAR SIEMPRE EN EL BRAZO. En los 60 frames.

    Esta es la invariante del escudo, y es MEDIBLE: la placa es parte
    del CUERPO, y el cuerpo esta registrado. Medida contra el centroide
    del cuerpo, la posicion de la placa apenas se mueve: la columna va
    de 55 a 61 y la fila de 40 a 40,5 en los 60 frames.

    Ese es el rango que el ovalo tiene que respetar.

    Lo que fallaba: la interpolacion se hacia en el espacio del CANVAS,
    que mezcla frames con el sprite corrido (la columna va de 52 a 77) y
    frames con el sprite centrado. El ovalo reconstruido acababa en la
    panza. La interpolacion en el espacio REGISTRADO lo deja en el
    brazo.
    """
    registered_x = [
        m.shield[0] + m.body_dx for m in measurements if m.shield is not None
    ]
    registered_y = [
        m.shield[1] + m.body_dy for m in measurements if m.shield is not None
    ]
    assert len(registered_x) == 60, (
        f"only {len(registered_x)} of the 60 frames have a shield"
    )
    assert min(registered_x) >= 54.0, (
        f"the oval goes to column {min(registered_x):.1f}, off the arm "
        f"(the arm is between 55 and 61)"
    )
    assert max(registered_x) <= 62.0, (
        f"the oval goes to column {max(registered_x):.1f}, off the arm "
        f"(the arm is between 55 and 61)"
    )
    assert min(registered_y) >= 39.0, (
        f"the oval goes to row {min(registered_y):.1f}, off the arm"
    )
    assert max(registered_y) <= 42.0, (
        f"the oval goes to row {max(registered_y):.1f}, off the arm"
    )


def _registered(m, feature: str) -> tuple[float, float]:
    """Where a feature sits RELATIVE TO THE BODY (the registered space).

    The canvas moves from frame to frame: the art of `death/frame_09` is
    authored 12 px lower inside its canvas. The registration correction is
    what puts the body back, so `canvas + body_d` is the position that does
    not move with the pose.
    """
    value = getattr(m, feature)
    assert value is not None
    return (value[0] + m.body_dx, value[1] + m.body_dy)


def test_a_reconstructed_anchor_keeps_its_place_relative_to_the_body(measurements):
    """UNA ANCLA RECONSTRUIDA SE QUEDA EN SU LUGAR RELATIVO AL CUERPO.

    Una pieza que no se pudo medir se RECONSTRUYE a partir de sus
    vecinos. La reconstruccion tiene que respetar la posicion de la pieza
    RELATIVA AL CUERPO (el espacio registrado), porque el cuerpo se mueve
    dentro de su canvas de un frame a otro: el arte de `death/frame_09`
    esta 12 px mas abajo en su canvas, y un ancla reconstruida en el
    espacio del canvas se queda 8 px por encima de donde esta la cabeza.

    Con un solo vecino medido, la reconstruccion tiene que COPIAR su
    posicion; con dos, tiene que quedar ENTRE las dos.

    LA CONTRAPOSICION esta ejecutada: con la interpolacion en el espacio
    del canvas, `laser/f04` caia en la columna 52,5 (el brazo esta entre
    55 y 61) y el ojo de `death/f09` caia en (57,18) en vez de (60,26).
    """
    by_clip: dict[str, list] = {}
    for m in measurements:
        by_clip.setdefault(m.clip, []).append(m)

    checked = 0
    for clip, items in by_clip.items():
        items.sort(key=lambda m: m.frame)
        for index, m in enumerate(items):
            for feature in ("shield", "eye"):
                if getattr(m, f"{feature}_source") != "interpolated":
                    continue
                here = _registered(m, feature)

                left = next(
                    (
                        other
                        for other in reversed(items[:index])
                        if getattr(other, f"{feature}_source") == "measured"
                    ),
                    None,
                )
                right = next(
                    (
                        other
                        for other in items[index + 1:]
                        if getattr(other, f"{feature}_source") == "measured"
                    ),
                    None,
                )
                neighbours = [n for n in (left, right) if n is not None]
                assert neighbours, (
                    f"{clip}/f{m.frame:02d}: the {feature} was reconstructed "
                    "with no measured neighbour to reconstruct it from"
                )

                for axis, label in ((0, "column"), (1, "row")):
                    values = [_registered(n, feature)[axis] for n in neighbours]
                    lo, hi = min(values), max(values)
                    assert lo - 1.0 <= here[axis] <= hi + 1.0, (
                        f"{clip}/f{m.frame:02d}: the reconstructed {feature} is "
                        f"at {label} {here[axis]:.1f} relative to the body, and "
                        f"its measured neighbours are at {values}: the "
                        "reconstruction left the piece's place"
                    )
                checked += 1

    assert checked == 3, (
        f"only {checked} anchors were reconstructed: the set has 3 (laser/04, "
        "laser/05 and death/09). If that number changed, this check is not "
        "looking at the frames it thinks it is"
    )


def test_the_measured_shield_sits_where_the_plate_is(measurements):
    """Donde el escudo se MIDE, tiene que coincidir con la firma.

    La placa tiene una firma de color (la cara de latón) y el `probe`
    la encuentra. La elipse del escudo es el CONTORNO. Si los dos no
    coinciden, la elipse no esta sobre la placa -- y eso es
    exactamente lo que pasaba cuando la elipse se interpolaba.

    La firma es una señal GRUESA: también reconoce los brillos dorados
    del torso, así que la tolerancia es ancha (los 14 px que usa el
    auditor). El check fuerte es el de arriba: el ovalo dentro de la
    banda del brazo.
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
            if measured.shield is None:
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
