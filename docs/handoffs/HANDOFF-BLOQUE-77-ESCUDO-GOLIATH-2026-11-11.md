# HANDOFF — BLOQUE 77: el escudo de GOLIATH (2026-11-11)

**Rama:** `bloquec-77-escudo-goliath` (worktree `.worktrees/bloquec-77-escudo-goliath`) · **Base:** `bloquec-76-contenido` @ `e9d2f15` (v1.9.0 + BLOQUE 76 + follow-ups) · **Perfil:** Lite · **Schema:** `.synapse` 2.2.0

> **Sin commitear.** El commit lo pide el usuario.

Dos preguntas del usuario, dos respuestas con números:

1. *"el escudo de GOLIATH que se corta en algunos frames"* → **era real**: en **7 de
   los 60 frames** el óvalo del escudo no estaba sobre la placa sino sobre la
   panza del jefe, y el láser naranja salía del sitio equivocado. **Arreglado en
   5 de esos 7** (los 2 restantes son frames donde el haz horneado cruza la
   placa: es el ARTE, y no se toca el arte).
2. *"asegurarnos que no hayan pedazos de GOLIATH que queden cortados al ser
   animado"* → **no hay ninguno, y ahora está probado con un test.**

**El arte no se tocó: ni un byte.** Los 60 PNGs de GOLIATH son los mismos, y
**los 6 goldens no se movieron** (byte a byte).

---

## 1. El diagnóstico (con los números)

### 1.1 El escudo no estaba MEDIDO: estaba RECONSTRUIDO

El óvalo del escudo es una elipse **invisible** cuya posición se hornea en
`anchors.toml`. El manifiesto declara una regla de detección por **contorno**
("la placa comparte paleta con el cuerpo, así que el color no la identifica;
la única firma usable es el contorno").

Medí los 60 frames:

- la placa está **casi quieta**: `cx` va de 57 a 60 en todo el clip;
- pero el **sprite entero está corrido dentro de su canvas** en algunos frames
  (`javelin/f03` +21 px, `javelin/f04` −13 px, `purple_bullet/f08` −16 px…),
  y el registro (`body_dx`) es lo que lo compensa;
- la regla de detección usa **columnas absolutas** (`min_col = 50`): en un
  frame corrido, la placa se sale de la ventana, el blob se fusiona con el
  brazo, la medición se descarta y el óvalo se **interpola** con los frames
  vecinos.

Y como los vecinos están en otra pose, el óvalo interpolado caía **en la
panza**. Ése es el bug, y es exactamente lo que se ve en el juego.

### 1.2 El óvalo viejo además estaba recortado por la banda

`cy` valía **exactamente 40,5 en los 60 frames**: no era la posición real de
la placa, era el centro de la banda `[28, 54]`. El contorno se medía sobre
una ventana que recortaba la placa por arriba y por abajo.

### 1.3 Y el "corte": no hay ninguno

| Medición | Resultado |
|---|---|
| Margen mínimo del arte en los 60 frames | **2 px** (el umbral es 2) → **0 frames cortados** |
| El sprite se dibuja | el **canvas entero** (el blit copia la superficie completa) → el arte **no puede** salirse de su lienzo al animarse |
| Las 10 puntas de la lanza | **completas**, con punta (incluso la de `f05`, con el detalle rojo) |

La lancha roja que se ve en `javelin/f03` es el **haz horneado** del frame, no
un corte: no toca el borde del canvas.

---

## 2. El fix

**`src/anim/measure.py`** — dos funciones nuevas:

- `registered_surface(surf, dx, dy)` → el sprite **como se va a dibujar** (con la
  corrección de registro aplicada) y el origen que devuelve una coordenada al
  canvas. **No se rellena con padding** a propósito: las reglas tienen ventanas
  **absolutas**, y una imagen con padding movería la ventana con ella.
- `to_canvas(point, origin)`.

**`tools/sprite_pipeline/audit.py`** — la medición se hace **sobre el sprite
registrado**, y el resultado se vuelve a coords de canvas. El ojo también: se
mide registrado (antes se medía en el canvas, y por eso fallaba en 1 frame).

**`Assets/sprites/bosses/goliath/manifest.toml`** — un solo cambio: el rango
de `rx` pasa de `(6.5, 11.0)` a `(3.0, 11.0)`. Motivo: **la placa de canto**
—cuando el brazo baja, el óvalo se ve estrecho (rx 3,5-6) y el rango viejo
lo rechazaba por ser "implausible", aunque sea una placa legítima.

> **Lo que NO se tocó:** `radii = [11, 11, 17]` (los radios canónicos
> aprobados en BLOQUE 67), `GOLIATH_SHIELD_R / _RX / _RY` del runtime, el
> arte, y los goldens.

### El resultado

| | Antes | Ahora |
|---|---|---|
| Escudos **interpolados** (inventados) | **7** | **2** (`laser/f04`, `laser/f05`) |
| Ojos interpolados | 1 | 1 (`death/f02`) |
| Hallazgos del auditor | 10 | **3** (0 FAIL) |
| `cy` de la elipse | 40,5 en los 60 (recortado) | **el real**, varía por pose |

**Los 5 arreglados, verificados a ojo** (el óvalo verde cae exacto sobre la
placa; antes caía sobre la panza): `javelin/f03`, `javelin/f04`, `javelin/f07`,
`purple_bullet/f06`, `purple_bullet/f08`.

---

## 3. Los 3 frames que quedan (y por qué NO se tocan)

| Frame | Qué pasa | Por qué no se arregla |
|---|---|---|
| `laser/f04`, `laser/f05` | El **haz rojo horneado** cruza la placa: el contorno que identifica la placa queda fusionado con el haz y la regla no puede separarlos. | Es el **ARTE**. Separarlo exigiría redibujar esos frames — y regenerar arte es tu decisión, no del pipeline. |
| `death/f02` | El jefe se derrumba: la firma de latón (40,7) y el contorno (57,5) **no coinciden** sobre dónde está la placa. | Igual: dos detectores independientes dicen cosas distintas porque la pose es ambigua. |

El **contrato** (`tools/sprite_pipeline/verify_contract.py`) nombra los 3 con su
motivo, y el gate lo exige: si vuelve a haber un frame que no se puede
medir, el contrato se rompe y el gate se pone rojo.

---

## 4. Los tests (con contraposición)

`tests/test_goliath_shield_is_measured.py` — 5 tests:

1. `test_the_shield_is_measured_in_every_frame_but_the_documented_ones` — el
   **conteo** de interpolados tiene que ser exactamente `{laser/4, laser/5}`.
   Es la garantía: si la medición vuelve a romperse, el conteo sube y el test
   se pone rojo.
2. `test_no_shield_is_unresolved` — ningún escudo sin elipse (el láser no
   saldría de ningún sitio).
3. `test_the_measured_shield_sits_where_the_plate_is` — donde el escudo se
   **mide**, la elipse tiene que coincidir con la firma de color de la placa.
   Este es el test que **no existía** y que habría detectado el bug: la
   firma (el `probe`) encuentra la placa esté donde esté, y el óvalo
   interpolado no coincidía con ella.
4. `test_no_piece_of_goliath_is_cut_when_animated` — el arte de cada frame
   dentro de su canvas con el margen del manifiesto, y el registro mueve el
   canvas entero (que es lo que hace que nada pueda salirse al animarse).
5. `test_the_registration_is_what_makes_the_measurement_work` — el
   mecanismo del fix, medido.

### Las contraposiciones (ejecutadas)

**Sin el registro** (`registered_surface` deja el sprite donde está):
```
FAILED test_the_shield_is_measured_in_every_frame_but_the_documented_ones
FAILED test_the_measured_shield_sits_where_the_plate_is
FAILED test_the_registration_is_what_makes_the_measurement_work
E   AssertionError: death/f07: the shield's ellipse is at x=60.0 but the
    plate's signature is at x=45.8: the ellipse is NOT on the plate
```

**Con el umbral de corte inalcanzable**:
```
FAILED test_no_piece_of_goliath_is_cut_when_animated
E   AssertionError: phase1_idle/f00: the art touches the edge of the canvas
    (margins L26 T2 R26 B3) -- the piece is CUT
```

---

## 5. Verificado

| Métrica | Resultado |
|---|---|
| Suite | **3203 pass + 6 skip + 1 xfail = 3210, 0 fallos** |
| Gate | `PHASE 1 GATE OK` / `PHASE 2 GATE OK` (exit 0) |
| `--check-pipeline` | 8 sets, `layers: 30`, exit 0 |
| `audit_sf_sm --perfil=lite` | 7/7 |
| **R1: PNGs modificados** | **0** (`git diff --stat a0c6f6f -- '*.png'` vacío) |
| **Goldens** | **los 6 byte a byte iguales** (14/14 tests del golden en verde) |
| Arte | **ni un byte** (sólo cambian `manifest.toml`, `anchors.toml` y el código) |

### Los tests que pineaban la aproximación vieja (y ahora pinean la real)

Cuatro tests de BLOQUE 74/75 afirmaban cosas que el fix vuelve falsas, y se
actualizaron **con el motivo escrito** (no para que passaran):

| Test | Antes | Ahora |
|---|---|---|
| `test_features_detected_everywhere.py::test_every_feature_says_where_it_came_from` | escudos 53/7 | **58/2** |
| `...::test_the_eye_and_the_shield_are_resolved_independently` | el ejemplo era `javelin/f03` | ahora `laser/f04` (f03 **se mide**) |
| `...::test_the_report_still_documents_the_art_problem` | reportaba `javelin/f04`, `laser/f05`, `purple_bullet/f08` | **`laser/f04`, `laser/f05`, `death/f02`** |
| `test_anchor_interpolation.py::test_the_shipped_set_reconstructs_what_it_could_not_measure` | el ejemplo era `javelin/f03` | ahora `laser/f04` |
| `test_goliath_shield_bloque67.py::test_shield_ellipse_is_on_the_right_of_the_sprite` | `cx > 52` (una columna fija) | **`cx` a la derecha del CENTROIDE de ese frame** |
| `test_goliath_shield_bloque67.py::test_shield_ellipse_fits_every_frame` | `cx 55..66, cy 38..44` (la banda) | **`cx 50..79, cy 34..54`** (las mediciones reales) |
| `test_sprite_pipeline_run.py::test_the_json_summary_counts_frames` | `== 10` hardcodeado | **derivado del CONTRATO** |

> Los dos tests de BLOQUE 67 pineaban la **aproximación** vieja: `cy` valía
> 40,5 en los 60 frames (el centro de la banda de detección) y el óvalo
> nunca se moveía con el brazo. Los rangos nuevos son los de las
> mediciones reales, y el test del resumen ya no tiene un número escrito a
> mano.

---

## 6. Lo que queda abierto

- **Los 3 frames de arriba**: son el arte. Si querés que el escudo salga de la
  placa también en `laser/f04`, `laser/f05` y `death/f02`, hay que redibujar
  esos frames — y eso es una decisión tuya (y "no agresivo regen" sigue en pie).
- **La puerta del `probe`**: `FIRMA_AMBIGUA` (el probe contra el contorno) es
  un WARN, y cuando el óvalo no es creíble el check **se salta** (el `shield`
  es `None`). El fix de BLOQUE 77 reduce el alcance de ese agujero, pero no
  lo cierra: la comparesión con el probe debería correr también cuando el
  óvalo es interpolado.
- **`Part.on_missing` sigue sin leerse** (follow-up 6.3 de la tanda 6): el
  manifiesto declara `on_missing = "interpolate"` y el auditor interpola
  siempre, sin mirar la regla.

---

## 7. Los archivos

**Nuevos:** `tests/test_goliath_shield_is_measured.py`
**Modificados:** `src/anim/measure.py` · `tools/sprite_pipeline/audit.py` ·
`tools/sprite_pipeline/verify_contract.py` ·
`Assets/sprites/bosses/goliath/manifest.toml` ·
`Assets/sprites/bosses/goliath/anchors.toml` (generado)
