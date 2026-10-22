# PROMPT-WEAPON-DEFINITIVO — 8 DIMENSIONES
## Portar GOLIATH BLOQUE 66 + Main Menu a VOID HUNTER v1.4.0 (BLOQUE 71)

**Destinatario**: agente implementador con contexto limpio.
**Autor del prompt**: Mavis (sesión 2026-10-20/22).
**Fecha**: 2026-10-22.

---

## ⚠️ DIMENSIÓN 0 — CONTEXTO CRÍTICO (leer antes que todo)

### El problema central: divergencia de historia

```
v1.4.0 (d70b8da)  ──── NO tiene ────→  BLOQUE 65/66 (GOLIATH con escudo)
                                         │
                                         └── está solo en la rama local
                                             que se publicó como v1.5.0…v1.6.3
```

**Verificado con `git merge-base --is-ancestor`:** tanto `ac53596` (BLOQUE 65 regen) como
`ed13dab` (BLOQUE 66 final) devuelven exit=1 contra `d70b8da`. Es decir: **v1.4.0 nunca
recibió el trabajo del escudo de GOLIATH.**

### Commits fuente (EXACTOS, no adivinar)

| Commit | Contenido | Qué portar |
|---|---|---|
| `ac53596` | BLOQUE 65: 60 frames PNG distintos (10 por cada una de 6 animaciones) | **Los 60 PNGs** |
| `50f072e` | 66.4e: escudo como elemento runtime (no mask del torso) | `_goliath_shield_center` |
| `b0bcdb6` | 66.4g/h: ancla por frame + tinte de la placa real | helpers de scenes.py |
| `17ce2d1` | 66.4k: escudo = disco dibujado anclado al brazo por frame | `_draw_goliath_shield` |
| `530530f` | 66.4l: eye laser arranca en el ojo real por frame | `get_sprite_eye_anchor` |
| `910d11c` | 66.4n: verificador por medición escudo↔laser = 0px | test de coincidencia |
| `0837a86` | **66.4o: ÓVALO montado sobre la placa — APROBADO POR EL USUARIO** | constantes finales |
| `ed13dab` | **66.6: revert del óvalo (DX=-11, DY=6) + shield test bypass** | **TIP de la historia** |

### Constantes APROBADAS (no tocar, no ajustar, no "optimizar")

```python
GOLIATH_SHIELD_DX = -11    # tira el óvalo 11px izquierda, sobre la placa
GOLIATH_SHIELD_DY = 6       # baja 6px, centro vertical de la placa
GOLIATH_SHIELD_R  = 11      # radio del hitbox (para colisiones circulares)
GOLIATH_SHIELD_RX = 11      # semi-eje horizontal del ÓVALO dibujado
GOLIATH_SHIELD_RY = 17      # semi-eje vertical del ÓVALO dibujado
GOLIATH_SHIELD_MAX_HITS = 20  # hits para cargar el láser
```

El usuario dijo textualmente: **"no vayas a cambiar el ovalo, ya que quedo bien"**.
BLOQUE 66.5 las achicó a `RX=7, RY=10, DX=-2, DY=0` y el usuario lo rechazó.
**El valor correcto es el de 0837a86 / ed13dab, NO el de 954d298 (66.5).**

### Comandos de recuperación (PowerShell, `;` como separador)

```powershell
cd F:\AI\MM\void-hunter

# 1. Verificar el estado base
git log --oneline -1 v1.4.0          # debe dar d70b8da
git merge-base --is-ancestor ed13dab v1.4.0
Write-Host "exit=$LASTEXITCODE"      # debe dar 1 (= no es ancestro)

# 2. Crear rama de trabajo desde v1.4.0
git checkout -b bloquec-67-goliath-port v1.4.0

# 3. Extraer los 60 frames (SOLO los PNG, no el código)
git checkout ac53596 -- Assets/sprites/bosses/goliath/
# verificar:
foreach ($a in @("phase1_idle","phase2_idle","javelin","laser","purple_bullet","death")) {
  $u = @((Get-ChildItem "Assets\sprites\bosses\goliath\$a\frame_*.png" |
    ForEach-Object { (Get-FileHash $_.FullName -Algorithm MD5).Hash }) |
    Select-Object -Unique).Count
  Write-Host "$a $u/10"
}

# 4. Extraer el código del escudo (para portar archivo por archivo)
git show ed13dab:src/ui/gameplay_runtime.py > $env:TEMP\runtime_b66.py
git show ed13dab:src/ui/scenes.py         > $env:TEMP\scenes_b66.py
git show ed13dab:src/entities/enemies/boss.py > $env:TEMP\boss_b66.py
git show ed13dab:tests/test_shield_laser_color.py > $env:TEMP\test_shield_b66.py
git show ed13dab:tests/test_boss_eye_laser.py    > $env:TEMP\test_eye_b66.py
git show ed13dab:tests/test_goliath_sprite.py     > $env:TEMP\test_sprite_b66.py
```

**⚠️ NO hagas `git merge ed13dab` ni `git cherry-pick`.** La historia divergió
(v1.4.0 tiene BLOQUE 67-73 que no existen en `ed13dab`). Un merge produciría
84 conflictos. El puerto es **archivo por archivo, copiando las funciones
específicas**, no un merge.

---

## DIMENSIÓN 1 — OBJETIVO Y ALCANCE

### Objetivo
Producir un `.exe` de VOID HUNTER basado en **v1.4.0 (BLOQUE 71, commit `d70b8da`)**
que incluya:

1. **GOLIATH de BLOQUE 66**: 60 frames animados, escudo con óvalo hitbox
   sobre la placa, carga que vuela de gris a naranja, láser grueso al 100%.
2. **Main Menu** post-cinematica con 3 items (NEW GAME / BOSS TIME / BACKGROUND)
   y submenu de 2 fondos.

### Lo que NO está en alcance
- Regenerar frames con AI (el usuario lo prohíbe: "no agresivo regen").
- Cambiar las constantes del óvalo (ver Dimensión 0).
- Tocar el sistema de armas de BLOQUE 72/73 (no existe en v1.4.0).
- Mover el fondo del boss fight (el selector sólo aplica a waves/sub-boss).
- Arreglar los tests con paths hardcodeados `D:\AI\void-hunter\...` (bug
  pre-existente, documentado aparte).

### Criterio de éxito (verificable)
- `[ ] python main.py --boss goliath --easy --scale 2 --duration 60` muestra
      GOLIATH **animándose** (≥10 poses distintas en 6s).
- `[ ] El óvalo del escudo está montado SOBRE la silueta del escudo,
      NO al lado.
- `[ ] El óvalo cambia de color con los hits (gris → naranja).
- `[ ] A 20 hits, el láser grueso sale del óvalo, no del pecho.
- `[ ] `--check` imprime `VOID HUNTER check OK`.
- `[ ] La cinemática lleva al Main Menu con los 3 items.
- `[ ] SPACE VOID muestra polvo estelar cayendo. ASTEROID NEBULA muestra el
      fondo procedural de v1.4.0.
- `[ ] 0 regresiones en la suite de v1.4.0.

---

## DIMENSIÓN 2 — ARQUITECTURA Y BOUNDARIES

### Principio: UN ancla, TRES consumidores

El bug que más tiempo costó en BLOQUE 65/66 fue que la hitbox, el visual y
el origen del láser se desincronizaban. La solución que funcionó:

```
_goliath_shield_center(runtime) -> (world_x, world_y)
        │
        ├──► _draw_goliath_shield()      VISUAL    (dibuja el óvalo)
        ├──► _handle_shield_collisions() HITBOX    (rect de colisión)
        └──► _draw_shield_laser()        LÁSER     (origen del haz)
```

**Regla dura**: los tres LEEN el mismo helper. Si alguno calcula su propia
posición, el bug vuelve. Un test debe verificar que el rect de hitbox
contiene todos los píxeles del borde del óvalo visible.

### Componentes a portar (uno a uno)

| Archivo destino | Qué agregar | Origen |
|---|---|---|
| `src/ui/scenes.py` | `get_sprite_centroid_offset(name)` | `ed13dab` |
| `src/ui/scenes.py` | `get_sprite_arm_anchor(name)` | `ed13dab` |
| `src/ui/scenes.py` | `get_sprite_eye_anchor(name)` | `ed13dab` |
| `src/ui/gameplay_runtime.py` | 6 constantes `GOLIATH_SHIELD_*` | `0837a86` |
| `src/ui/gameplay_runtime.py` | `_goliath_shield_center(runtime)` | `50f072e` |
| `src/ui/gameplay_runtime.py` | `_draw_goliath_shield()` | `17ce2d1` |
| `src/ui/gameplay_runtime.py` | `_boss_shield_laser_t` en state | `50f072e` |
| `src/ui/gameplay_runtime.py` | `_handle_shield_collisions()` | `50f072e` |
| `src/ui/gameplay_runtime.py` | `_draw_shield_laser()` | BLOQUE 53a |
| `src/ui/gameplay_runtime.py` | llamada a `update_animation(dt)` | **73.5** |
| `src/entities/enemies/boss.py` | `update_animation()` + `ANIMATION_FRAME_DURATION` | BLOQUE 64.B |
| `src/core/scene_manager.py` | `GameState.MENU` + transiciones | **73.7** |
| `src/ui/scenes.py` | `MainMenuScene` | **73.7** |
| `src/core/game.py` | `bg_mode: int` | **73.7** |
| `src/ui/gameplay_runtime.py` | branch de render por `bg_mode` | **73.7** |

### Main Menu — flujo de estados

```
TITLE ──(key)──► CINEMATIC ──(10s o Esc)──► MENU
                                               │
                              ┌────────────────┼────────────────┐
                              ▼                ▼                ▼
                        ACT_INTRO       BOSS_INTRO      (submenu bg)
                              │                │
                              ▼                ▼
                          GAMEPLAY      BOSS_FIGHT
                              │
                              ▼
                        BOSS_INTRO ──► BOSS_FIGHT
```

`VALID_TRANSITIONS` debe incluir:
```python
GameState.CINEMATIC: {..., GameState.MENU, ...}
GameState.MENU: {GameState.ACT_INTRO, GameState.BOSS_INTRO, GameState.TITLE}
```

---

## DIMENSIÓN 3 — FLUJO DE DATOS Y ANCLAS

### Ancla del escudo: por color, con clamp

El sprite de GOLIATH **no tiene arte de escudo separado** — el escudo y el
torso son la misma masa dorada continua (~688px). Por eso:

1. **No se puede usar el borde derecho de la silueta** → es la juncia de la
   jabalina, no el escudo.
2. **Se usa la firma de color del latón**: `(r>185, g>145, b<130, r>b+70)`.
   Es el único cúmulo así dentro de la armadura dorada.
3. **Se clampa** a una caja alrededor del centro del canvas, porque la firma
   también dispara en remaches de hombrera, punta de la jabalina y cresta
   del casco:
   ```python
   col = min(max(col, _GOLIATH_ANCHOR_X - 6), _GOLIATH_ANCHOR_X + 6)
   row = min(max(row, _GOLIATH_ANCHOR_Y - 8), _GOLIATH_ANCHOR_Y + 8)
   ```

### Centroid del cuerpo

```python
get_sprite_centroid_offset(name) -> (dx, dy)
    # suma alfa sobre (x, y); offset = round((48 - cx), (40 - cy))
    # frames que se inclinan (javelin/frame_03 = dx +20) se realinean
    # al ancla del mundo en vez de amontonarse en el borde del viewport
```

El blit del sprite usa el MISMO offset:
```python
blit_x = cx - vw // 2 + centroid_dx
blit_y = cy - vh // 2 + int(bob) + centroid_dy
```

### Eye anchor

```python
get_sprite_eye_anchor(name) -> (col, row)
    # píxeles rojos saturados (r>170, r-g>70) en el rango de cabeza
    # (rows 0-29, cols 24-70); toma el centroide
    # rows resultantes: 13-28 según la pose
```

El láser del ojo (ataque 9) debe nacer en:
```python
laser_x = boss.x - 48 + centroid_dx + eye_col
laser_y = boss.y - 40 + centroid_dy + eye_row
```

### Carga del escudo → color

| `charge_ratio` (hits/20) | Color |
|---|---|
| < 0.50 | hierro `(110,110,125)` |
| 0.50–0.85 | hierro → azul medio |
| > 0.85 | azul medio → cyan/blanco `(220,240,255)` |

El usuario menciona "anaranjado". La rampa aprobada usa `iron → blue → cyan`.
**Si el usuario quiere naranja, cambiar sólo el tramo final a `(255,140,40)`,
manteniendo la forma del óvalo y el anclaje intactos.**

### Background modes

| `bg_mode` | Qué dibuja |
|---|---|
| `0` SPACE VOID | sólo `ParallaxBackground` (polvo estelar cayendo hacia abajo) |
| `1` ASTEROID NEBULA | `ScrollingGalaxyBackground` (el fondo procedural de v1.4.0) + parallax encima |

**Default = 1** (ASTEROID NEBULA), porque es el look de v1.4.0.

El render branchea:
```python
if self._is_boss:
    # boss tiene su propio fondo, NO lo cambia bg_mode
    self._tiling_bg.draw(target)  # o self._bg.draw(target)
elif bg_mode == 0:
    self._parallax_bg.draw(target)
else:
    self._galaxy_bg.draw(target)
```

**⚠️ BUG HISTÓRICO A NO REPETIR**: en v1.6.0 el `ScrollingGalaxyBackground`
se llamaba en `update()` pero **nunca en `draw()`**. El strip se animaba y
los píxeles se descartaban. Al portar a v1.4.0, **verificar que `draw()`
esté en el path de render** con un test que compare píxeles con/sin strip.

---

## DIMENSIÓN 4 — EDGE CASES Y ERROR HANDLING

| Caso | Comportamiento esperado |
|---|---|
| Sprite falta (`_load_sprite` devuelve `None`) | helpers devuelven `(48, 40)` canvas anchor; el óvalo se dibuja centrado. **Nunca crashear.** |
| Sprite sin alfa (todo opaco o todo transparente) | centroid `(0,0)`; arm anchor canvas center |
| Frames idénticos en una animación | los helpers cachean por path; el test `all_ten_frames_are_distinct` falla explícito |
| Sprite toca el borde del canvas (T=1px) | ver Dimensión 5 (padding) |
| Esc en el submenu BACKGROUND | vuelve al top SIN aplicar el cambio |
| Esc en el top del menu | vuelve a TITLE |
| Boss desconocido en `BOSS TIME` | mensaje a stderr + exit 2, no arranca juego normal en silencio |
| `bg_mode` fuera de rango (tests) | clamp a `(0, 1)` |
| Alto de la tira del galaxy < alto de pantalla | `ScrollingGalaxyBackground` ya dibuja una copia extra; verificar |
| `Assets/background/tiles/act1/` ausente | `TileManager` con `available=False`, dibuja nada, galaxy strip es el fondo. **Este bug crasheó v1.4.0 al lanzar.** |
| Presionar key durante la cinemática | se ignora (la cinemática sólo escucha Esc) |
| `update_animation` con `dt <= 0` | return temprano (guardas existentes) |
| `death` animation | **NO hace loop** — se queda en frame 9 para siempre |

### Regla de oro del puerto
Si una función de `ed13dab` depende de algo que **no existe** en v1.4.0,
**no la portes** — reescribla contra las APIs de v1.4.0. El ejemplo
concreto: `ed13dab` referencia `self._boss_spear_phase`, que sí existe en
v1.4.0, pero `ed13dab` también asume `get_sprite_arm_anchor` con
`set_theme` que en v1.4.0 tiene otra firma. **Verificar cada import.**

---

## DIMENSIÓN 5 — ASSETS Y VERIFICACIÓN VISUAL

### Los 60 PNGs

```
Assets/sprites/bosses/goliath/
├── phase1_idle/   frame_00.png … frame_09.png   (10 distintos)
├── phase2_idle/   frame_00.png … frame_09.png   (10 distintos)
├── javelin/       frame_00.png … frame_09.png   (10 distintos)
├── laser/         frame_00.png … frame_09.png   (10 distintos)
├── purple_bullet/ frame_00.png … frame_09.png   (10 distintos)
└── death/         frame_00.png … frame_09.png   (10 distintos)
```

Origen: `git checkout ac53596 -- Assets/sprites/bosses/goliath/`

**Dimensiones**: 96×80 px, RGBA, transparente.

### Padding mínimo

Ninguno de los 60 sprites debe tocar el borde del canvas. En BLOQUE 66
fueron 4 frames; en 73.4 fueron 3 más. **Verificar TODOS:**

```powershell
python -c "
from PIL import Image
import glob
bad = 0
for p in sorted(glob.glob('Assets/sprites/bosses/goliath/*/frame_*.png')):
    im = Image.open(p).convert('RGBA')
    bb = im.split()[-1].getbbox()
    if bb is None: continue
    w, h = im.size
    m = min(bb[0], bb[1], w-bb[2], h-bb[3])
    if m < 2:
        print(f'  {p}: margin={m}px')
        bad += 1
print(f'frames con margen <2px: {bad}')
"
```

Si sale `> 0`, paddear con `tools/fix_sprite_padding_bloque73.py`
(shift de 2px hacia abajo sobre canvas nuevo del mismo tamaño).

### Verificación visual obligatoria

Renderizar con el script de captura (NO a ojo):

```powershell
python tools/capture/capture_b73_all_anims.py    # strips de 10 frames por anim
python tools/capture/capture_goliath_shield_bloque73.py  # 3 estados del escudo
python tools/capture/capture_main_menu.py        # menú + submenu
python tools/capture/verify_boss_flag.py         # confirma que el boss anima
```

**Criterio visual del óvalo (el usuario lo approvals así)**:
> "el ovalo esta dentro de la silueta del escudo"

Es decir: el óvalo debe estar **DENTRO** del contorno del escudo del sprite,
no superpuesto ni al lado. Los cinco estados de carga deben ser distinguibles
a simple vista.

---

## DIMENSIÓN 6 — TYPING, STYLE Y CONVENCIONES

### Convenciones existentes del proyecto

- **Python 3.12**, `from __future__ import annotations` en todos los módulos.
- **Type hints** en toda función pública. El proyecto corre `ruff` (ver
  `pyproject.toml`).
- **Comments en inglés** con prefijo de BLOQUE:
  ```python
  # BLOQUE 73.5: advance the sprite animation. Boss.update() moves the
  # entity but never touched animation_frame, and update_animation() had
  # no caller anywhere in src/ — so the frame stayed pinned at 0.
  ```
  Explicar el **porqué**, no el **qué**.
- **Nombres de helpers**: `get_sprite_*` para medición, `_goliath_*` para
  lógica de GOLIATH, `_draw_*` / `_handle_*` para métodos del runtime.
- **Caches a nivel módulo** con flag `_loaded` para distinguir "no probado"
  de "probé y no hay archivo".
- **PowerShell para scripts, `;` como separador**, NUNCA `&&`.
- **Tests**: `pytest`, fixtures con `SDL_VIDEODRIVER=dummy`,
  `pygame.display.set_mode((1,1))`.

### Prohibido

- `# type: ignore` sin justificación real.
- Números mágicos sin nombre: `GOLIATH_SHIELD_RX = 11`, no `draw.ellipse(r, 11, 17)`.
- Cambiar constantes aprobadas sin que el usuario lo pida explícitamente.
- `git merge` / `git cherry-pick` de historias divergentes.

---

## DIMENSIÓN 7 — TESTING Y VERIFICATION GATES

### Gates (TODOS deben pasar antes de declarar terminado)

**Gate 1 — Import sin crashear**
```powershell
$env:SDL_VIDEODRIVER="dummy"
python main.py --check
# Debe imprimir: VOID HUNTER check OK
```

**Gate 2 — Los 60 frames son distintos**
```powershell
foreach ($a in @("phase1_idle","phase2_idle","javelin","laser","purple_bullet","death")) {
  $u = @((Get-ChildItem "Assets\sprites\bosses\goliath\$a\frame_*.png" |
    ForEach-Object { (Get-FileHash $_.FullName -Algorithm MD5).Hash }) |
    Select-Object -Unique).Count
  if ($u -ne 10) { Write-Error "FAIL: $a tiene $u/10 frames distintos" }
}
```
Expected: 10/10 en las seis. **Este gate detectó el bug de 73.3 donde
562eb58 había colapsado los 60 frames a 6 stills.**

**Gate 3 — La animación avanza**
```powershell
python tools/capture/verify_boss_flag.py
# Debe mostrar: "total de poses distintas: 15" (o ≥10)
```

**Gate 4 — Escudo ↔ láser con 0px de delta**
```powershell
python tools/capture/verify_shield_laser_coincidence.py
# Debe imprimir: 60/60 frames con 0 px de delta
```

**Gate 5 — Ningún sprite toca el borde**
Script de la Dimensión 5. Expected: `frames con margen <2px: 0`.

**Gate 6 — Suite de GOLIATH verde**
```powershell
python -m pytest tests/ -k "boss or goliath or shield or javelin" --ignore=tests/test_paths_legacy.py -q
```
Baseline v1.4.0 + port: ~196 passed. **Si baja, es regresión.**

**Gate 7 — Menú navegable**
```powershell
python -m pytest tests/test_main_menu_scene.py -q
# 10 passed
```

**Gate 8 — Los 2 fondos se ven distintos**
Renderizar con `bg_mode=0` y `bg_mode=1` y comparar capturas. Si se ven
iguales, el bug del strip sin `draw()` está presente.

**Gate 9 — Build limpio**
```powershell
python -m PyInstaller build.spec --clean --noconfirm
& "dist\void-hunter.exe" --check
```

### Tests a portar desde `ed13dab`

| Test | Qué garantiza |
|---|---|
| `test_shield_laser_color.py` | el color del escudo cambia con la carga |
| `test_boss_eye_laser.py` | el láser del ojo nace en el ojo |
| `test_goliath_sprite.py` | `_draw_goliath` usa el sprite |
| `test_goliath_pixel_mask_hitbox.py` | hitbox pixel-perfect |
| `test_shield_plate_is_oval_not_circle` | **el óvalo NO es un círculo** (guarda la proporción RX:RY) |
| `test_shield_hitbox_matches_visual` | **el rect de hitbox contiene todo el óvalo visible** |

El último es el que más valor tiene: si alguien "optimiza" el hitbox a un
círculo más chico, ese test falla y vuelve el bug de "disparar al vacío".

---

## DIMENSIÓN 8 — ENTREGABLES Y ORDEN DE EJECUCIÓN

### Orden de ejecución (respetar)

| # | Paso | Gate |
|---|------|------|
| 1 | `git checkout -b bloquec-67-goliath-port v1.4.0` | — |
| 2 | Recuperar los 60 PNGs desde `ac53596` | Gate 2 |
| 3 | Portar los 3 helpers a `scenes.py` | Gate 5 |
| 4 | Portar las constantes + `_goliath_shield_center` | Gate 5 |
| 5 | Portar `_draw_goliath_shield` (ÓVALO, constantes aprobadas) | Gate 4, 6 |
| 6 | Portar `_handle_shield_collisions` (usar el helper, NO calcular) | Gate 6 |
| 7 | Portar `_draw_shield_laser` (usar el helper) | Gate 4 |
| 8 | Portar `update_animation` a `boss.py` + **cablearlo** en `gameplay_runtime` | Gate 3 |
| 9 | Portar `get_sprite_eye_anchor` + fix del láser del ojo | Gate 6 |
| 10 | Portar los tests desde `ed13dab` | Gate 6 |
| 11 | Agregar `GameState.MENU` + `MainMenuScene` + `bg_mode` | Gate 7 |
| 12 | Branch de render por `bg_mode` (con el fix del `draw()`) | Gate 8 |
| 13 | Capturas visuales | Gate 5, 8 |
| 14 | Build + `--check` | Gate 9 |
| 15 | Commit + tag + release | — |

### Deliverables

```
1. dist/void-hunter.exe                          (~423 MB, onefile)
2. dist/VoidHunter-v1.5.0-win64.zip
3. Código commiteado en la rama bloquec-67-goliath-port
4. tests/ — los portados + los nuevos del menú
5. tools/playtest_out/ — capturas de evidencia
6. docs/KNOWN_ISSUES.md actualizado
```

### Checklist de cierre (para el usuario)

- [ ] Abrir el `.exe`, llegar al menú, entrar a BOSS TIME
- [ ] Ver GOLIATH **animándose** (contar ≥10 poses en 6s)
- [ ] Ver el óvalo **dentro** de la silueta del escudo
- [ ] Ver el óvalo cambiar de color al disparar
- [ ] Ver el láser grueso salir del escudo al llegar a 20 hits
- [ ] Entrar a NEW GAME y cambiar entre SPACE VOID y ASTEROID NEBULA
- [ ] Confirmar que los 2 fondos se ven **distintos**

---

## RESUMEN EJECUTIVO

**Qué hacer**: tomar v1.4.0 (BLOQUE 71, commit `d70b8da`) como base, y
portar archivo-por-archivo el GOLIATH de BLOQUE 66 que vive en la historia
local (`ed13dab` + `ac53596`), más el Main Menu de BLOQUE 73.7.

**El error más probable a repetir**: hacer `git merge` en vez de portar
archivo por archivo. Las historias divergieron; el merge da 84 conflictos
y el resultado es ilegible.

**El segundo error más probable**: cambiar el óvalo. Los valores correctos
son `DX=-11, DY=6, RX=11, RY=17`. BLOQUE 66.5 los achicó y el usuario los
rechazó explícitamente.

**El tercer error**: portar el `_draw_goliath_shield` pero olvidar el
`update_animation(dt)` en el loop. Sin eso, los 60 frames se cargan pero
solo se ve el frame 0 — el jefe se ve estático aunque los PNGs estén bien.

---

*Fin del prompt. 8 dimensiones + contexto crítico.*
*Generado por Mavis — sesión 2026-10-20/22, GOLIATH polish + ship v1.5.0/v1.6.3.*