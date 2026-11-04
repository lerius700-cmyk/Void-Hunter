"""BLOQUE 75 Fase 2: the gameplay frame as an ordered list of layers.

The order the frame used to be drawn in is now DATA: thirty layers, each
with a `z`, each calling the drawing code that already exists. Nothing is
moved OUT of the runtime -- the bodies stay there -- so this module is an
ORDER, not a rewrite.

The bridge is deliberate: the layer bodies call the runtime's draw
helpers, including the `_`-prefixed ones. Splitting the 6 750-line runtime
into focused modules is another BLOQUE; until then, the order lives here
and the bodies live there.

THE ARITY IS NOT OPTIONAL. The runtime's draw helpers are a MIX: some
take `(target)` and some take `(target, ox, oy)`. Every layer therefore
carries the arity of the helper it calls, and `build_layers` picks the
matching call form -- one call form per helper, never one generic one.
`tests/test_layer_stack_order.py` pins every arity against the REAL
signature, so a renamed or re-shaped helper breaks the test instead of
raising TypeError in the middle of a frame.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Callable

import pygame

from src.render.layer import DrawContext, Layer, LayerStack

if TYPE_CHECKING:  # pragma: no cover - the import cycle is broken on purpose
    # gameplay_runtime imports THIS module (BLOQUE 75 Fase 2, Task 4), so
    # the runtime type must NOT be imported at runtime.
    from src.ui.gameplay_runtime import GameplayRuntime

# A runtime draw helper: `(target)`, `(target, ox, oy)` -- the layer body
# decides which one of the two it is.
_DrawFn = Callable[..., None]

# The arity of the helper a layer calls: how many arguments the layer
# body has to pass.
_PLAIN = 1  # (target)
_SHAKE = 3  # (target, shx, shy)

# (layer id, runtime method, z, arity of the runtime method)
#
# The order is the one the frame used to be drawn in, measured -- see
# docs/superpowers/specs/2026-10-30-bloque-75-migration-spec.md. The
# BACKGROUND is not here: it is the stack's backdrop and it is drawn
# before the stack renders.
_LAYERS: tuple[tuple[str, str, int, int], ...] = (
    ("ambient_dust", "_draw_ambient_dust", 0, _PLAIN),
    ("player_damage_flash", "_draw_player_damage_flash", 1, _PLAIN),
    ("powerups", "_draw_powerup_pass", 2, _SHAKE),
    ("enemies", "_draw_enemy_pass", 3, _SHAKE),
    ("asteroids_and_powerups", "_draw_asteroids_and_powerups", 4, _PLAIN),
    ("leader_glows", "_draw_leader_glows", 5, _PLAIN),
    ("boss", "_draw_boss_pass", 6, _SHAKE),
    ("boss_spears", "_draw_boss_spear_pass", 7, _SHAKE),
    ("shield_laser", "_draw_shield_laser_pass", 8, _SHAKE),
    ("shockwaves", "_draw_shockwave_pass", 9, _SHAKE),
    ("bomb_bursts", "_draw_bomb_burst_pass", 10, _SHAKE),
    ("bullets", "_draw_bullets_with_glow", 11, _SHAKE),
    ("missiles", "_draw_missiles", 12, _SHAKE),
    ("tron_trail", "_draw_tron_trail", 13, _SHAKE),
    ("player_afterimage", "_draw_player_afterimage", 14, _SHAKE),
    ("player", "_draw_player_pass", 15, _SHAKE),
    ("continuous_laser", "_draw_continuous_laser", 16, _SHAKE),
    ("reticle", "_draw_reticle_pass", 17, _SHAKE),
    ("bomb_flash", "_draw_bomb_flash", 18, _PLAIN),
    ("particles", "_draw_particles", 19, _SHAKE),
    ("score_popups", "_draw_score_popups", 20, _SHAKE),
    ("wave_indicator", "_draw_wave_indicator", 21, _PLAIN),
    ("play_area_frame", "_draw_play_area_frame", 22, _PLAIN),
    ("hud", "_draw_hud", 23, _PLAIN),
    ("pattern_banner", "_draw_pattern_banner", 24, _PLAIN),
    ("screen_flash", "_draw_screen_flash", 25, _PLAIN),
    ("charge_release_flash", "_draw_charge_release_flash", 26, _PLAIN),
    ("pickup_flash", "_draw_pickup_flash", 27, _PLAIN),
    ("level_up_flash", "_draw_level_up_flash", 28, _PLAIN),
    ("speed_lines", "_draw_speed_lines_pass", 29, _PLAIN),
)

# The runtime method each layer calls. Exported so the order test can
# assert that every one of them still exists.
LAYER_BODIES: tuple[str, ...] = tuple(method for _, method, _, _ in _LAYERS)

# The arity of each of those methods, in the same order. Exported so the
# order test can check the factory against the REAL signature.
LAYER_ARITY: tuple[int, ...] = tuple(arity for _, _, _, arity in _LAYERS)


def build_layers(rt: "GameplayRuntime") -> LayerStack:
    """The thirty layers of the gameplay frame, in the measured order.

    `rt` is the `GameplayRuntime`. Each layer calls one of its draw
    helpers; the helpers are the code that exists today. The helpers
    that take the shake get it from the context -- the very same
    `shx, shy` the frame computed.
    """
    layers: list[Layer] = []
    draw: Callable[[pygame.Surface, DrawContext], None]
    for layer_id, method_name, z, arity in _LAYERS:
        method: _DrawFn = getattr(rt, method_name)
        if arity == _SHAKE:
            draw = lambda target, ctx, _method=method: _method(
                target, ctx.shake[0], ctx.shake[1],
            )
        else:
            draw = lambda target, ctx, _method=method: _method(target)
        layers.append(Layer(id=layer_id, z=z, draw=draw))
    return LayerStack(layers)
