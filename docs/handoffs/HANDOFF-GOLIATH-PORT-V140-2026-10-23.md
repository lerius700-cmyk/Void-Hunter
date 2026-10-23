# HANDOFF — GOLIATH (BLOQUE 66) + menú principal post-cinematica portados a v1.4.0

**Fecha:** 2026-10-23
**Rama:** `bloquec-67-goliath-port` (worktree aislado en `.worktrees/bloquec-67-goliath-port`)
**Base:** `d70b8da` (v1.4.0, BLOQUE 71)
**Fuente de verdad:** `master` @ `a40fdaf` (v1.6.3) — port **archivo por archivo**, sin merge.

> El trabajo NO está mergeado a `master`. `master` sigue con sus 8 commits sin
> pushear, intactos. Este handoff describe la rama de trabajo.

---

## 1. Qué se cambió

### Código (`src/`)

| Archivo | Qué se portó | Origen |
|---|---|---|
| `src/systems/tile_manager.py` | Degradación graceful: `available=False` cuando falta el set de tiles, `draw()` no-op. **Sin esto v1.4.0 crasheaba al arrancar** (158 tests en rojo) | BLOQUE 73.1 |
| `src/ui/scenes.py` | `get_sprite_eye_anchor()`, `get_sprite_centroid_offset()`, `get_sprite_arm_anchor()` (con clamp de sanity 73.3) | BLOQUE 66.4l / 73.3 |
| `src/ui/scenes.py` | `MainMenuScene` (NEW GAME / BOSS TIME / BACKGROUND) + submenu de fondo | 73.7 |
| `src/ui/scenes.py` | `TitleScene`: selector de tema de fondo 1-4 / ←-→ + label `BG: <tema>` | 73.6 |
| `src/ui/scenes.py` | `GameplayScene.on_enter()`: inyecta `_game` al runtime (**73.8**) + aplica el tema elegido | 73.6 + 73.8 |
| `src/ui/scenes.py` | `BossFightScene.on_enter()`: aplica el tema de fondo | 73.6 |
| `src/ui/scenes.py` | `CinematicScene`: la cinemática ahora encadena a `MENU`, no a `ACT_INTRO` | 73.7 |
| `src/ui/gameplay_runtime.py` | `GOLIATH_SHIELD_DX/DY/R/RX/RY` + `GOLIATH_SHIELD_MAX_HITS` + constantes del láser | 66.4o / 53a |
| `src/ui/gameplay_runtime.py` | `_goliath_shield_center()` — **un solo ancla para los 3 consumidores** (visual, hitbox, origen del láser) | 73.2 |
| `src/ui/gameplay_runtime.py` | `_draw_goliath_shield()` — óvalo translúcido con rampa de carga (hierro → azul → cyan) | 73.2 |
| `src/ui/gameplay_runtime.py` | `_handle_shield_collisions()` — hitbox = caja del óvalo (`max(R,RX)+1 × max(R,RY)+1`) | 73.2 / 73.4 |
| `src/ui/gameplay_runtime.py` | `_draw_shield_laser()` — el haz sale del óvalo, no del pecho | 73.2 |
| `src/ui/gameplay_runtime.py` | Láser del ojo: nace en el ojo real del frame (búsqueda de rojo saturado) | 73.4 |
| `src/ui/gameplay_runtime.py` | `_draw_goliath()`: offset por centroide del sprite + dibujo del escudo | 73.2 |
| `src/ui/gameplay_runtime.py` | `Boss.update_animation(dt)` **cableado** en `_update_boss` — antes nadie lo llamaba, el boss quedaba en 1 pose | 73.5 |
| `src/ui/gameplay_runtime.py` | Branch de render por `bg_mode`; modo 1 = galaxy **+ parallax encima**; la galaxy ahora se **dibuja** (antes sólo se actualizaba) | 73.7 / 73.8 |
| `src/core/scene_manager.py` | `GameState.MENU` + transiciones `CINEMATIC→MENU`, `MENU→{ACT_INTRO, BOSS_INTRO, TITLE}` | 73.7 |
| `src/core/game.py` | `bg_mode: int = 1`, `bg_variant_idx: int = 3`, `_register_with_back_ref()`, registro de `MainMenuScene` | 73.6 / 73.7 |
| `main.py` | `--boss`/`--act` dejan de ser stub: caminan `TITLE→ACT_INTRO→GAMEPLAY→BOSS_INTRO→BOSS_FIGHT` | 73.5 |
| `main.py` | `--check` reporta 15 escenas | 73.7 |
| `src/audio/music.py` | Docstring con escape inválido `\A` → documenta la resolución real sin backslashes | — |

### Assets

- **60 frames de GOLIATH** restaurados desde `ac53596` (BLOQUE 65) + el re-padding de `6c71e1b` (73.4).
  La base v1.4.0 tenía los frames **colapsados** (10 copias idénticas por animación, MD5 único = 1).
  Sin regenerar nada con AI: se tomaron los PNGs ya aprobados.

### Tests

- **Nuevos:** `test_goliath_anchor_coincidence.py` (8), `test_goliath_animation_advances.py`,
  `test_bg_mode_render.py` (5, Gate 8), `test_bg_variant_selector.py`, `test_main_menu_scene.py`.
- **Actualizados:** `test_game_state_machine.py` (14→15 estados, aristas de `MENU`),
  `test_cinematic_scene.py` (`CINEMATIC→MENU`), `test_tile_manager.py` (reescrito en 73.1),
  `test_gameplay_runtime.py` (el proyectil apunta a `boss.x + 8`, fuera del escudo),
  `test_goliath_sprite.py` (`_boss_shield_laser_t`).

---

## 2. Números reales de la suite

```powershell
python -m pytest tests/ --tb=no
```

| | failed | passed | skipped | total |
|---|---|---|---|---|
| **v1.4.0 crudo (baseline)** | **158** | 2,539 | 7 | 2,704 |
| **v1.4.0 + port** | **8** | **2,726** | 12 | 2,746 |

Los **8 que quedan son pre-existentes** (idénticos a los que ya fallaban en v1.6.3, ver
`HANDOFF-GOLIATH-MENU-2026-10-23.md` §6):

- 4 × `tests/test_sub_boss_full_flow.py` (contaminación de estado entre tests)
- 1 × `tests/test_sub_boss_real_flow.py` (ídem)
- 2 × `tests/test_asteroid_sprites.py`
- 1 × `tests/test_paths.py::test_paths_no_star_shapes` (aserción real de geometría del LissajousPath)

**Cero regresiones introducidas por el port.** Los 158 del baseline eran una sola
causa raíz: `TileManager.__init__` levantaba `FileNotFoundError` porque
`Assets/background/tiles/act1/` nunca se commiteó → el juego no arrancaba.

---

## 3. Gates ejecutados

| Gate | Resultado |
|---|---|
| Gate 2 — MD5 único por animación | **10/10** en las 6 animaciones |
| Gate 5 — ningún sprite toca el borde (<2px) | **0 frames** con margen <2px |
| Gate 8 — `pytest tests/test_bg_mode_render.py` | **5 passed** |
| Gate 8b — `-k nebula_is_richer` | **1 passed** |
| `python main.py --check` | exit 0, `VOID HUNTER check OK`, 15 escenas |
| `python main.py --boss goliath --easy --duration 60` | `VOID HUNTER: jumped to GOLIATH (act 1)`, exit 0, 60 s en `BOSS_FIGHT` sin crash |
| `py_compile` / `compileall` sobre `src` + `tests` + `main.py` | exit 0 |

Capturas de evidencia en `tools/playtest_out/`:
`menu_top_newgame.png`, `menu_top_bosstime.png`, `menu_bg_submenu.png`,
`menu_bg_space_void.png`, `menu_bg_asteroid_nebula.png`,
`goliath_shield_3states_bloque73.png` (rampa de carga del escudo).

---

## 4. Qué quedó SIN portar (y por qué)

### 4.1 Tres tests de la rama BLOQUE 66 — NO portados

El spec lista `test_shield_laser_color.py`, `test_boss_eye_laser.py` y
`test_goliath_pixel_mask_hitbox.py` como "a portar desde `ed13dab`". **No se portaron**
porque necesitan APIs que **no existen ni en v1.4.0 ni en el `master` publicado (v1.6.3)**:

| API requerida | ¿En v1.4.0? | ¿En master v1.6.3? |
|---|---|---|
| `Boss.collides_with` | no | no |
| `Boss.trigger_eye_laser` | no | no |
| `src.ui.scenes._sprite_shield_mask_cache` | no | no |

Son APIs de la **rama BLOQUE 66**, que divergió y nunca llegó a `master`. Portarlas
exigía inventar tres APIs nuevas que v1.6.3 nunca tuvo — es decir, no portar, inventar.

**La cobertura equivalente sí está**, en `tests/test_goliath_anchor_coincidence.py`
(8 tests, viniendo de `master`, green):

| Invariante | Test de master que lo cubre |
|---|---|
| el haz sale del escudo, no del pecho | `test_shield_laser_origin_matches_shield_centre` |
| el rect de hitbox contiene todo el óvalo visible | `test_shield_hitbox_rect_contains_the_drawn_oval` |
| el centro del escudo no depende de la carga | `test_shield_centre_is_independent_of_charge` |
| el láser del ojo nace en el ojo | `test_eye_laser_spawns_at_the_eye_not_the_body` |
| el ancla del ojo varía con la pose | `test_eye_anchor_varies_with_pose` |
| los 10 frames de cada animación son distintos | `test_all_ten_frames_of_each_animation_are_distinct` |
| ningún sprite toca el borde del canvas | `test_no_sprite_touches_the_canvas_edge` |

Los 3 archivos quedaron apartados en
`.worktrees/_srcrefs/_bloque66_branch_tests/` (fuera del repo) por si se quiere revisarlos.

### 4.2 No portado por ser otro BLOQUE (fuera de alcance)

- **Carga dearma (charge system)** — los cambios de `master` en `test_gameplay_runtime.py`
  ("BLOQUE 73 Phase A") reescriben el contrato de carga del jugador. Se aplicó **sólo**
  el fix del proyectil del test de phase-change, no el resto del archivo.
- **`Game.bg_variant_idx` + selector 1-4 del título (73.6)** — sí se portó, porque
  `_register_with_back_ref()` (de 73.6) es la tubería de la que dependen 73.7 y 73.8, y
  `bg_variant_idx = 3` (purple_dusk) es el default que pidió el usuario.
- **Backplate de GOLIATH** — prohibido explícitamente. No se tocó. Tampoco se corrieron
  `tools/capture/build_goliath_backplate.py` ni `bake_backplate_into_frames.py`.
- **`tools/capture/final_verification.py`** — no se portó (no es necesario para los gates).

---

## 5. Dos bugs reales encontrados (y arreglados en el port)

### 5.1 `TitleScene.draw` → `NameError` (bug vivo en master v1.6.3)

`master` (73.6) escribe `self._bg_variant_label_t - dt` dentro de `draw(self, target)`.
El contrato `Scene.draw` **no tiene `dt`**. El primer `draw()` tras pulsar 1-4 en el
título levanta `NameError: name 'dt' is not defined` y **crashea la pantalla de título**.

Reproducido contra el código publicado de `master` antes de tocar nada:

```
TitleScene.draw signature: ('self', 'target')
RESULT: NameError -> name 'dt' is not defined
```

**Arreglo en el port:** el timer decae en `update(dt)`, donde `dt` sí existe.

### 5.2 `--boss` con escena re-registrada perdía el tema de fondo

En `master`, el `--boss` re-registra `BOSS_FIGHT` con `register_scene(...)` pelado, sin
el back-ref `_game` → elThemes del boss arena no se aplicaba y quedaba el default
(`blue_void`) en vez del `purple_dusk` elegido. **Arreglo en el port:** se inyecta
`_game` también en la escena re-registrada.

### 5.3 El cache del lowpass ensuciaba el working tree con 64 MB

`src/audio/music.py` escribe la copia filtrada del gameplay track **en el mismo
directorio del asset fuente**:

```
Assets/keep kept - Lerius - soundtrack gameplay_lp<hz>.wav
```

Son ~64 MB por cutoff y es un **cache regenerable, no fuente**. Como `master` lo
commiteó por accidente (commit `30dd5df` — el propio mensaje lo admite: *"left out of
git by accident - one `git clean -fdx` away from being gone"*), el archivo reaparecía en
el working tree después de cada corrida de tests.

**Arreglo en el port:** regla `Assets/*_lp*.wav` en `.gitignore`. Los `.wav` ya
trackeados (`gameplay.wav`, `_lp600.wav`) no se ven afectados — gitignore no aplica a
archivos ya trackeados.

> Nota: `master` tiene el `lp8000.wav` **trackeado**, así que la regla no aplica ahí.
> Si querés sacarlo de `master` en otro momento, es `git rm --cached` de ese archivo.
> La release lo define `GAMEPLAY_TRACK = "keep kept - Lerius - soundtrack gameplay.wav"`,
> que sí está en el repo — el `lp8000` no lo referencia nadie.

---

## 6. Constantes sagradas — NO tocar

```
GOLIATH_SHIELD_DX = -11
GOLIATH_SHIELD_DY = 6
GOLIATH_SHIELD_R  = 11
GOLIATH_SHIELD_RX = 11
GOLIATH_SHIELD_RY = 17
```

Aprobadas por el usuario en BLOQUE 66.4o. El port las copió **sin modificar**.

`bg_mode` default = **1** (ASTEROID NEBULA). `bg_variant_idx` default = **3** (purple_dusk).

---

## 7. Cómo continuar

```powershell
cd F:\AI\MM\void-hunter\.worktrees\bloquec-67-goliath-port
python -m pytest tests/ --tb=no
python main.py --check
python main.py --boss goliath --easy --duration 60
```

La rama `bloquec-67-goliath-port` está lista para integrarse a `master` — pero la
integración es decisión del usuario (merge / PR / push). **No se hizo push, ni tag,
ni release.**
