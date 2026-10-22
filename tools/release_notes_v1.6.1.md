# VOID HUNTER v1.6.1 — todo el trabajo de GOLIATH de la sesión

> Hotfix sobre v1.6.0. Trae las últimas piezas del polish de GOLIATH que
> faltaban, y dos bugs reales que los tests nuevos encontraron.

---

## 🎯 El láser del ojo ahora sale del ojo

Antes el láser nacía en `boss.y + 30` — un offset fijo. Pero al medir los
píxeles rojos del ojo en el sprite, sale en la **fila 18** en `phase1_idle` y
en la **fila 22** en `javelin`/`laser`. O sea: el haz arrancaba entre 2 y 6
píxeles **por debajo** del ojo, y a simple vista parecía salir del pecho.

Ahora se ancla al ojo real de cada frame (las filas ahora varían entre 13 y
28 según la pose):

```python
eye_col, eye_row = get_sprite_eye_anchor(path)
laser_x = boss.x - 48 + centroid_dx + eye_col
laser_y = boss.y - 40 + centroid_dy + eye_row
```

---

## 🛡️ El escudo ahora colisiona completo

El hitbox era un cuadrado armado desde `GOLIATH_SHIELD_R` (11). Pero el óvalo
es **11 × 17** — así que los **6 píxeles de arriba y abajo** del escudo
visible no colisionaban. Las balas pasaban de largo a través de un escudo
que el jugador veía clarísimo.

Ahora el rect usa las semi-extensiones reales del óvalo, más 1 px porque
`pygame.Rect` es half-open y si no excluía los píxeles de los extremos:

```python
hx = max(GOLIATH_SHIELD_R, GOLIATH_SHIELD_RX) + 1   # 12
hy = max(GOLIATH_SHIELD_R, GOLIATH_SHIELD_RY) + 1   # 18
```

---

## ✂️ 7 frames con el sprite cortado al borde del canvas

El "GOLIATH se ve cortado" original. Siete frames tenían la silueta a 1 píxel
del borde superior — la llama del casco se cortaba contra el marco:

| Frame | Antes | Después |
|-------|-------|---------|
| `laser/01` | T=1 | T=3, B=2 |
| `phase2_idle/04` | T=1 | T=3, B=2 |
| `phase2_idle/08` | T=1 | T=3, B=2 |
| `phase1_idle/02` | T=1 | T=3 |
| `phase1_idle/03` | T=1 | T=3 |
| `javelin/00` | T=1 | T=7 |
| `purple_bullet/02` | T=5 | T=4, B=4 |

Ahora **ningún sprite toca el borde** en las 6 animaciones.

`tools/fix_sprite_padding_bloque73.py` hace el ajuste: recompone el sprite
desplazado sobre un canvas transparente del mismo tamaño. El contenido
visual no se toca — solo su posición, y los anclas (centroid / arm / eye)
se recalculan solas en el siguiente acceso.

---

## 🧪 8 tests permanentes que weren't written before

BLOQUE 66.4n había dejado esto como un script de captura que había que
correr a mano (`tools/capture/verify_shield_laser_coincidence.py`). Una
imagen que hay que acordarse de regenerar es una imagen que se pudre en
silencio. Ahora son asserts:

| Test | Qué garantiza |
|------|---------------|
| `shield_centre_is_independent_of_charge` | El hitbox no se mueve al cargar |
| `shield_hitbox_rect_contains_the_drawn_oval` | Cada píxel del óvalo visible colisiona |
| `shield_laser_origin_matches_shield_centre` | El haz sale del escudo |
| `eye_anchor_varies_with_pose` | El ancla del ojo no es fija |
| `eye_anchor_sits_in_the_head_band` | El ojo está en la cabeza (fila 8-30) |
| `eye_laser_spawns_at_the_eye` | El haz nace en el ojo, no en `boss.y + 30` |
| `all_ten_frames_are_distinct` | **Guarda contra la regresión de 73.3** |
| `no_sprite_touches_the_canvas_edge` | **Guarda contra el "cortado" original** |

Los últimos dos son guardas de regresión por cosas que **de verdad** pasaron
y que son baratas de reintroducir.

---

## ✅ Verificación

| Check | Resultado |
|-------|-----------|
| `void-hunter-v1.6.1.exe --check` | `VOID HUNTER check OK` |
| Tests boss/goliath/shield/javelin | **220 passed, 1 skipped** (era 212) |
| Frames únicos | **60/60** |
| Margen mínimo del canvas | **2 px** (0 frames tocados) |

---

## ⬇️ Como jugar

1. Descargá `VoidHunter-v1.6.1-win64.zip` (~423 MB)
2. Extraé en cualquier carpeta
3. Doble-click en `void-hunter-v1.6.1.exe`

```
void-hunter-v1.6.1.exe --check
void-hunter-v1.6.1.exe --boss goliath --easy --duration 60
```

## 💻 Requisitos

Windows 10/11 64-bit · ~430 MB disco · ~200 MB RAM