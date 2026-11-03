# BLOQUE 75 Fase 2 — El motor de capas del frame: diseño

**Date:** 2026-11-03
**Status:** READY FOR PLAN
**Author:** Lerius (decisiones) + Mavis (diseño)
**Spec:** `docs/superpowers/specs/2026-10-30-bloque-75-migration-spec.md` (§Fase 2: la arquitectura del motor por capas (decidida))
**Decidido por:** brainstorming, 2026-11-02/03 — A1, A2 y A3 con A1/A2/A3 recomendados y aceptados

---

## 1. El problema que resuelve

`src/ui/gameplay_runtime.py` tiene **6 501 líneas**. Su frame loop (`3969-4165`)
son ~200 líneas de llamadas secuenciales donde cada una repite
`(target, shx, shy)`:

```python
self._draw_ambient_dust(target)
...
for e in self.enemies:
    self._draw_enemy_scaled(target, e, shx, shy)
...
self._hud.draw(target, self._player, self._weapon, self._scoring, t=self._t, kill_ratio=ratio)
```

Tres consecuencias concretas:

1. **El orden de dibujo es código**: no se puede leer de un vistazo qué se
   pinta encima de qué, ni guaranteeing que un cambio no altere el orden.
2. **El desplazamiento de pantalla se pasa a mano**: `shx, shy` viajan a cada
   llamada, y el fallback procedural recalcula `offset_x/offset_y` por entidad
   para centrar un scratch (64×64 del jugador, 48×48 del enemigo, 64×64 del
   sub-boss).
3. **El cambio de orden es invisible en el review**: nadie puede ver que
   "mover el HUD dos líneas" cambia el frame.

El motor por capas convierte el frame en **datos** (30 capas con `z`) y la
pantalla en **un contexto** (`DrawContext`). Es un refactor de **orquestación**:
el cuerpo de cada capa es el código de dibujo que existe hoy.

## 2. El vocablo: tres niveles de "capa", no uno

| Nivel | Concepto | Dónde | Qué ordena |
|---|---|---|---|
| entidad | `Part.z` | `src/anim/parts.py` (BLOQUE 74) | las partes **dentro** de un set: `body` 0, `shield_plate` 1, `eye` 2, `fx_eye_beam` 3 |
| frame | **capa de frame** (nuevo) | `src/render/layer.py` | las **operaciones de dibujo del frame** (las 30 del gameplay) |
| escena | stack de `SceneManager` | `src/core/scene_manager.py` | qué pantalla está activa (15 `GameState` excluyentes) + overlays |

El `ClipPlayer` **ya es un compositor** — de las *partes de un set* (nivel
entidad). El motor nuevo es un compositor de **frame** (nivel escena). Son
distintos y ambos hacen falta. Lo que hay que evitar es que "layer" signifique
tres cosas: por eso el tercer nivel se llama **capa de frame** y vive en su
propio paquete, y los otros dos no se tocan.

## 3. Las decisiones (ya tomadas)

| # | Decisión | Razón |
|---|---|---|
| **A1** | El motor vive en **`src/render/layer.py`**: `Layer`, `LayerStack`, `DrawContext`. Genérico, **sin imports de `src/ui/`** ni `src/entities/` | L6: `src/anim/` tiene prohibido importar `src/ui/` porque el gate de mypy corre sobre `src/anim/`. El motor nuevo hereda esa frontera por construcción y sacamos el concepto de la zona del monolito. |
| **A2** | El **`SceneManager` no se toca** | 15 estados excluyentes ("qué pantalla") vs. capas simultáneas ("en qué orden"). Unificarlas = modelo combinatorio sin capacidad nueva, sin proof pixel-a-pixel para 14 escenas. |
| **A3** | La Fase 2 va en **dos checkpoints**, cada uno con su golden | 2A = el stack con los mismos cuerpos; 2B = enemigos y boss por el pipeline. Una falla se localiza. |
| **B1** | `Layer` **no** lleva `visible` | Es `frozen`: un flag inmutable es inútil, y los draws condicionales los decide el **cuerpo** de la capa. |
| **B2** | `ctx.origin` = centro del playfield; `ctx.with_origin(x, y)` para los scratch | Un campo congelado no puede ser dos cosas; hay tres superficies scratch. |
| **B3** | Los **golden frames se commitean** | Sin ellos, B2 no es reproducible en otra máquina. Misma disciplina que los `anchors.toml`: la medición, versionada. |
| **B4** | `ctx.scale` = 1.0, `ctx.size` = (320, 480) | El escalado a ventana sigue en `Game._present()` (F6). |
| **B5** | El fondo queda **fuera** del stack | Es lo único que va detrás de todo y tiene su propio ciclo de update. Su lugar: "el fondo del stack". |
| **B6** | El HUD **entra** en `z = 23` | Se dibuja dentro de la secuencia del playfield y antes de los flashes de pantalla completa. |
| **B7** | Los **14 estados restantes** no se tocan | No tienen playfield. `src/render/` queda genérico para que los adopten después sin reescribir el motor. |
| **B8** | El pipeline conecta a **enemigos y boss**; el jugador queda fuera | El jugador tiene rotación y escala propias (`PLAYER_SPRITE_SCALE`), y su arte no es un set del pipeline (N9). |

## 4. El diseño

### 4.1 `DrawContext` — la pantalla

```python
@dataclass(frozen=True)
class DrawContext:
    """Everything a layer needs to know about WHERE and WHEN it draws.

    target  the surface being painted (the 320x480 internal surface).
    origin  the world point that maps to the CENTRE of `target`.
            For the playfield: the centre of the internal surface.
            For a scratch surface: the entity's own position.
    scale   the uniform scale of `target`. Always 1.0: the window
            scaling happens in Game._present(), never here (F6).
    time    seconds since the scene started (the runtime's `self._t`).
    shake   the screen-shake offset (shx, shy), already computed.
    size    the target's size.
    """
    target: pygame.Surface
    origin: tuple[float, float]
    scale: float
    time: float
    shake: tuple[int, int]
    size: tuple[int, int]

    def with_origin(self, x: float, y: float) -> "DrawContext":
        """A copy whose origin is another world point.

        The procedural fallback draws into a scratch surface centred on
        the entity: the scratch is 64x64 (player), 48x48 (enemy) or 64x64
        (sub-boss), and the current code computes
        `offset = scratch_size // 2 - entity_pos` per entity
        (gameplay_runtime.py:5351-5353). `with_origin` replaces that
        arithmetic: the layer asks for a context centred on the entity
        and the scratch draw becomes ordinary code.
        """
        return replace(self, origin=(x, y))

    def at(self, x: float, y: float) -> tuple[int, int]:
        """A world position mapped to screen pixels, shake included."""
        return (int(x) + self.shake[0], int(y) + self.shake[1])
```

`at()` es el sustituto de `e.x + shx` disperso por 30 llamadas: **el shake se
suma en un solo lugar**.

### 4.2 `Layer` — una operación de dibujo

```python
@dataclass(frozen=True)
class Layer:
    """One draw operation of the frame.

    id    stable identity: the order guard and the golden-frame report
          name layers by what they draw ("enemies", "boss", "hud").
    z     the global order. The stack sorts by z with a STABLE sort, so
          two layers with the same z keep their insertion order.
    draw  the drawing body. It receives the target and the context.
    """
    id: str
    z: int
    draw: Callable[[pygame.Surface, DrawContext], None]
```

Sin `visible` (B1). Los draws condicionales —el boss sólo existe en el modo
boss, el banner sólo cuando hay banner— los decide el **cuerpo** de la capa,
que es el que sabe de su propia precondición.

### 4.3 `LayerStack` — el orden

```python
class LayerStack:
    """The ordered set of layers that compose one frame.

    The stack owns the ORDER and nothing else. It never draws a layer
    itself, never mutates a layer and never reorders at runtime: the
    order is fixed at build time and asserted by a guard test.
    """

    def __init__(self, layers: Sequence[Layer]) -> None:
        self._layers = tuple(sorted(layers, key=lambda l: l.z))

    @property
    def layers(self) -> tuple[Layer, ...]:
        return self._layers

    def render(self, ctx: DrawContext) -> None:
        for layer in self._layers:
            layer.draw(ctx.target, ctx)
```

`render` recibe **el contexto**, no el target: el target viaja en el contexto,
así que una capa nunca ve una superficie que no sea la que se está pintando.

### 4.4 Las 30 capas del gameplay

`src/ui/gameplay_layers.py` expone `build_layers(rt) -> LayerStack`. Cada capa
**llama** al método de dibujo que ya existe; no lo mueve.

| z | Layer | Body (el método que ya existe) |
|---|---|---|
| 0 | `ambient_dust` | `rt._draw_ambient_dust(target)` |
| 1 | `player_damage_flash` | el flash rojo a pantalla completa (inline hoy) |
| 2 | `powerups` | el loop de powerups (inline) |
| 3 | `enemies` | el loop de enemigos → `rt._draw_enemy_scaled` |
| 4 | `asteroids_and_powerups` | `rt._draw_asteroids_and_powerups(target)` |
| 5 | `leader_glows` | `draw_leader_glows(...)` |
| 6 | `boss` | `rt._draw_boss(target, shx, shy)` |
| 7 | `boss_spears` | el loop de lanzas (inline) |
| 8 | `shield_laser` | `rt._draw_shield_laser(target, shx, shy)` |
| 9 | `shockwaves` | el loop (inline) |
| 10 | `bomb_bursts` | el loop (inline) |
| 11 | `bullets` | `rt._draw_bullets_with_glow(target, shx, shy)` |
| 12 | `missiles` | `rt._draw_missiles(target, shx, shy)` |
| 13 | `tron_trail` | `rt._tron_trail.draw(target, (shx, shy))` |
| 14 | `player_afterimage` | `rt._draw_player_afterimage(target, shx, shy)` |
| 15 | `player` | `rt._draw_player_scaled(target, shx, shy)` |
| 16 | `continuous_laser` | `rt._draw_continuous_laser(target, shx, shy)` |
| 17 | `reticle` | `rt._draw_reticle(target, shx, shy)` |
| 18 | `bomb_flash` | el flash blanco (inline) |
| 19 | `particles` | `rt._particles.draw(target, (shx, shy))` |
| 20 | `score_popups` | `rt._draw_score_popups(target, shx, shy)` |
| 21 | `wave_indicator` | `rt._draw_wave_indicator(target)` |
| 22 | `play_area_frame` | `rt._draw_play_area_frame(target)` |
| 23 | `hud` | `rt._hud.draw(target, ...)` |
| 24 | `pattern_banner` | inline |
| 25 | `screen_flash` | inline |
| 26 | `charge_release_flash` | inline |
| 27 | `pickup_flash` | inline |
| 28 | `level_up_flash` | inline |
| 29 | `speed_lines` | `rt._draw_speed_lines(target)` |

El **fondo** (parallax + galaxy, `3938-3948`) se dibuja **antes** de
`stack.render(ctx)` — sigue siendo "el fondo del stack" (B5).

### 4.5 El flujo de un frame

```python
# gameplay_runtime.py, el loop
self._draw_background(target)                 # fuera del stack (B5)
ctx = DrawContext(
    target=target,
    origin=(INTERNAL_W / 2, INTERNAL_H / 2),
    scale=1.0,
    time=self._t,
    shake=(shx, shy),
    size=(INTERNAL_W, INTERNAL_H),
)
self._layers.render(ctx)
```

Y el frame loop pasa de ~200 líneas a ~12.

### 4.6 Checkpoint 2A — el stack sin cambiar nada

**Cambio:** el frame loop usa el stack; cada capa llama al mismo cuerpo.
**Cero** cambio de comportamiento, **cero** cambio de píxel.
**Prueba:** los golden frames son idénticos byte a byte.

### 4.7 Checkpoint 2B — los enemigos y el boss por el pipeline

**Cambio:** el layer `enemies` dibuja el cuerpo de cada enemigo a través del
`ClipPlayer`, y el `boss` sigue como está (ya usa el pipeline).

Tres detalles hacen que esto NO rompa un píxel:

**(a) La escala.** El runtime dibuja el enemigo a `1.05`
(`_ship_scale_enemy`, `gameplay_runtime.py:408`) pero el `ClipPlayer` dibuja
el PNG **crudo** (`ClipPlayer.surface()` no escala; `draw_part` blita tal cual).
Sin resolver esto, el enemigo saldría 32×32 en vez de 33×33 → un píxel de
diferencia por borde → los golden frames NO coincidirían.

**Decisión:** el compositor aplica `Part.scale` a las partes de tipo `frames`,
con **la misma truncación** que el runtime actual (`int(w * scale)`:
`32 * 1.05 → 33`). El `Part.scale` ya existe en el manifest (default
`(1.0, 1.0)`), así que GOLIATH no cambia (su body no declara scale → 1.0, que
es lo que ya hace hoy por el pipeline).

Consecuencia: **los manifests de enemigos ganan `scale = [1.05, 1.05]`** en su
parte `body`. Es un cambio de Fase 2, no de Fase 1: en Fase 1 el pipeline
nunca dibuja al enemigo, así que el campo no hacía falta.

**(b) El pivote.** `pivot = "fixed"` (el pivot de centro del canvas) es lo que
reproduce el blit centrado actual. `src/anim/parts.py::_base()` hoy **ignora**
el pivote y siempre suma `body_dx/body_dy` (que para estos sets NO son cero:
`body_dy = round(16 - centroid_y)` da hasta ±4). Sin el cambio, las naves se
moverían hasta 4 px respecto de su hitbox.

**Decisión:** `parts.py::_base()` usa `(0, 0)` cuando `part.pivot == "fixed"`.
GOLIATH (`pivot = "centroid"`) no cambia.

**(c) El timing.** El `ClipPlayer.state(clip_id, elapsed)` deriva el frame del
tiempo transcurrido; el runtime lleva su propio contador
(`animation_frame`, `ANIMATION_FRAME_DURATION = 0.08`).

**Decisión:** el layer **no mueve el timing**. Pasa el frame del runtime
(`enemy.animation_frame`) y sólo pide la superficie y el ancla. El `fps` del
manifest queda como **documentación verificada** por
`tests/test_enemy_clip_semantics.py` (que afirma `clip.fps == 1/0.08`), no como
un cálculo nuevo. Motivo: cambiar quién calcula el frame es un cambio de
comportamiento que no hace falta para el objetivo, y el proof pixel-a-pixel
debe ser el único que decida.

**El flash de daño** sigue siendo un overlay del runtime (N4: los overlays no
son features del manifest). El pipeline expone la superficie **escalada** para
que el overlay se construya con exactamente los mismos píxeles que hoy.

### 4.8 El harness de golden frames

**El problema:** el runtime usa el RNG global en 31 lugares que afectan la
pantalla (`random.uniform`, `random.random`, `random.shuffle`) y sólo siembra
`_asteroid_rng`. Una captura no reproducible produce falsos negativos.

**El arnés** (`tools/capture/layerstack_frames.py`):

1. `random.seed(N)` con N fijo, **antes** de construir la escena.
2. **Reconstruir la escena** en cada captura (una escena reutilizada conserva
   su estado de RNG y sus posiciones).
3. `dt` fijo por tick; nunca tiempo de reloj.
4. Una secuencia de input guionizada.
5. Escribe el frame interno de 320×480 a `tools/golden/layerstack/<name>.png`.

**El auto-chequeo:** antes de confiar en el golden, el arnés captura el mismo
frame **dos veces** y compara los bytes. Si difieren, la captura no es
determinista y el golden no sirve → el gate falla antes de comparar nada.

**La prueba** (`tests/test_layer_stack_renders_identical_frames.py`): vuelve a
capturar y compara **pixel a pixel** (RGB + alfa). **0 píxeles distintos** es
la condición de paso; el test imprime cuántos píxeles difieren y la primera
coordenada cuando falla.

**Los frames** (al menos 5): un frame con enemigos, uno con el boss, uno con
la mina en `open3`, uno con el jugador disparando, y uno con el HUD poblado.

### 4.9 Errores y degradación

| Situación | Comportamiento |
|---|---|
| Una capa lanza una excepción | **propaga**. El juego ya falla ruidosamente; un layer que se traga su error escondería el frame roto. |
| Un manifest que no carga | `loaded_set` devuelve `None` → la capa usa su fallback actual (el Procedural). El pipeline degrada, no rompe. |
| Una superficie que no se puede cargar | `ClipPlayer.surface()` devuelve `None` → `draw_part` no dibuja (ya es el comportamiento de hoy). |
| Un set sin anchors | `NO_OFFSET` (ya existe en `parts.py`): el cuerpo se dibuja sin la corrección de registro. |

### 4.10 Pruebas

| Prueba | Qué prueba |
|---|---|
| `test_layer_stack_order.py` | los ids y los `z` de las 30 capas contra la tabla de §4.4 — un reordenamiento falla aunque los píxeles coincidan |
| `test_layer_stack_renders_identical_frames.py` | los golden frames: **0 píxeles distintos** |
| `test_layer_stack_context.py` | `with_origin` mueve el origen; `at()` suma el shake una sola vez |
| `test_draw_context_scale.py` | `ctx.scale == 1.0` y `ctx.size == (320, 480)` (F6) |
| `test_fixed_pivot.py` | con `pivot = "fixed"` el blit queda centrado en el canvas, con los offsets medidos sin aplicar |
| `test_enemy_scale_matches_runtime.py` | el enemigo por el pipeline mide lo mismo que por el runtime (`int(32 * 1.05) == 33`) |

## 5. Lo que esta Fase NO hace

- **No** generaliza el `SceneManager` (A2).
- **No** toca los 14 estados restantes (B7).
- **No** mueve los cuerpos de dibujo a archivos nuevos: las capas los **llaman**.
  El split de `gameplay_runtime.py` (6 501 líneas) es otro BLOQUE.
- **No** cambia la resolución ni el escalado a ventana (B4).
- **No** mete al jugador ni al flash de daño en el manifest (B8, N4).
- **No** toca el arte: ni un PNG (R1).

## 6. File map de la Fase 2

| Archivo | Acción | Rol |
|---|---|---|
| `src/render/__init__.py` | crear | el paquete |
| `src/render/layer.py` | crear | `DrawContext`, `Layer`, `LayerStack` — genérico, stdlib + pygame, **sin imports de `src/ui/`** |
| `src/ui/gameplay_layers.py` | crear | `build_layers(rt)`: las 30 capas, en el orden medido |
| `src/ui/gameplay_runtime.py` | modificar | el frame loop pasa a construir el contexto y llamar `stack.render(ctx)`; el layer `enemies` pasa a dibujar por el pipeline (2B) |
| `src/anim/parts.py` | modificar | `_base()` respeta `pivot == "fixed"` |
| `src/anim/clip.py` | modificar | la superficie de tipo `frames` se escala con `Part.scale` y se cachea escalada |
| `src/anim/manifest.py` | modificar | enforcement de `mode`/`on_end` (N14 termina acá) + la raíz de enemigos en source y `_MEIPASS` |
| `Assets/sprites/enemies/*/manifest.toml` | modificar | `scale = [1.05, 1.05]` en el body (2B) |
| `tools/capture/layerstack_frames.py` | crear | el arnés determinista |
| `tools/golden/layerstack/*.png` | crear | los frames de referencia (commiteados) |
| `tests/test_layer_stack_order.py` | crear | el guard del orden |
| `tests/test_layer_stack_renders_identical_frames.py` | crear | el proof pixel a pixel |
| `tests/test_layer_stack_context.py` | crear | el contexto |
| `tests/test_draw_context_scale.py` | crear | la resolución |
| `tests/test_fixed_pivot.py` | crear | el pivote |
| `src/core/scene_manager.py` | **no tocar** | A2 |

## 7. Riesgos

| # | Riesgo | Mitigación |
|---|---|---|
| R1 | Un píxel cambia sin que nadie lo note | El golden frame es el gate: 0 píxeles distintos, y el auto-chequeo de determinismo antes de comparar. |
| R2 | El reordenamiento de las capas altera el frame | El guard de `z` + los ids (prueba estructural) + el golden (prueba visual). |
| R3 | El timing de la animación cambia al pasar al pipeline | El layer pasa el frame del runtime; el pipeline no calcula el frame. El `fps` del manifest es documentación verificada por un test. |
| R4 | El enemigo se corre 1 px por la escala | La escala es una decisión de diseño explícita (§4.7a) y hay un test que compara `int(32 * 1.05) == 33` con el runtime. |
| R5 | El flash de daño se arma sobre píxeles distintos | El pipeline expone la superficie escalada; el overlay usa exactamente esos píxeles. |
| R6 | El golden no es reproducible en otra máquina | El arnés es determinista por construcción (semilla, escena nueva, dt fijo) y el auto-chequeo de dos capturas lo prueba. |
| R7 | El `src/render/` Drag imports `src/ui/` y rompe el gate de mypy | La regla es del paquete: `src/render/` no importa `src/ui/` ni `src/entities/`. Un guard lo verifica. |
| R8 | El motor queda genérico sin un segundo consumidor | YAGNI: `src/render/` son ~150 líneas sin features de juego; si un día otro estado lo adopta, ya tiene su casa. |

## 8. Métricas de aceptación

| # | Métrica |
|---|---|
| F2-M1 | El frame loop del gameplay tiene **una** llamada `stack.render(ctx)` y ninguna lista de `self._draw_*` |
| F2-M2 | `src/render/` no importa `src/ui/` ni `src/entities/` (guard) |
| F2-M3 | `ctx.scale == 1.0` y `ctx.size == (320, 480)` |
| F2-M4 | El golden: **0 píxeles distintos** en los 5 frames, en los dos checkpoints |
| F2-M5 | El arnés captura el mismo frame dos veces → bytes idénticos |
| F2-M6 | El enemigo por el pipeline y por el runtime miden lo mismo (33×33) |
| F2-M7 | La suite no empeora; `mypy src/anim/ src/render/` → 0 errores |

---

## Appendix — el registro del brainstorming

| # | Pregunta | Respuesta del owner | Decisión |
|---|---|---|---|
| 1 | ¿Dónde vive el motor? | `src/render/` separado | A1 |
| 2 | ¿El `SceneManager` se generaliza? | No, no se toca | A2 |
| 3 | ¿Fase 2 en un paso o dos checkpoints? | Dos checkpoints | A3 |

Y las que el spec dejó abiertas antes (Q1-Q5) quedaron resueltas en §"Open
questions (resolved)" del spec de BLOQUE 75.
