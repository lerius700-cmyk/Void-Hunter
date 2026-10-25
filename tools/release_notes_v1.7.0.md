# VOID HUNTER v1.7.0 (BLOQUE 67) — GOLIATH completo, menú post-cinematica y el fondo morado de v1.4.0

> La línea v1.4.0 (BLOQUE 71) con todo el trabajo de GOLIATH (BLOQUE 66) y
> el menú post-cinematica (BLOQUE 73.7) portados encima, más el sistema de
> 4 armas (BLOQUE 72 + 73 Fase A/B/C). Todo lo que venía en v1.6.3 sigue
> estando: esta release no pierde nada de la anterior.

---

## 🐉 GOLIATH: el escudo, el ojo y la animación

**El escudo ahora está donde tiene que estar.** Antes el óvalo quedaba 11 px
a la izquierda, sobre el torso, y nunca coincidía con la placa. Ahora:

- El óvalo se **mide** sobre la silueta real de la placa en cada frame
  (`scenes.get_sprite_shield_ellipse`), así que encaja perfecto y se mueve
  con el brazo.
- Está en el **brazo derecho**, que es el que lleva el escudo.
- La misma medición alimenta el **hitbox** y el **origen del láser**: la
  imagen, lo que colisiona y de dónde sale el rayo no pueden desincronizarse.

**El óvalo es invisible.** No se dibuja ni el cuerpo, ni el borde, ni el
remache. Lo único que se ve sobre la placa son dos capas:

| Capa | Qué es | Cuándo |
|---|---|---|
| **Calor** | resplandor que se pone **rojo al primer impacto** y se calienta (rojo → naranja → ámbar → blanco caliente) | desde el 1er impacto |
| **Impacto** | parpadeo blanco de 0.30 s por disparo | cada vez que entra un bala |

**El láser del escudo es grueso y naranja** (núcleo de 8 → 14 px) y sale de la
placa, no del pecho.

**El láser del ojo sale del ojo.** El sprite del rayo es una columna de 360 px
que el pool dibuja *centrada* en el proyectil: al aparecer en el ojo, media
columna quedaba por encima (fuera de pantalla) y el rayo parecía salir del
tope de la pantalla. Ahora el borde superior del rayo cae justo en el ojo, y
el rayo **sigue al ojo** cuando GOLIATH se desplaza (±80 px).

**GOLIATH se mueve de verdad.** `Boss.update_animation()` existía desde
BLOQUE 64.B pero **nadie lo llamaba nunca**: el boss se quedaba en una sola
pose durante toda la pelea.

## 🌌 El fondo ASTEROID NEBULA es el de verdad

El gameplay de v1.4.0 usaba la secuencia de **6 tiles pintados** del
"Asteroid Approach" (el morado procedural). Esos PNGs **nunca se
commitearon** — los generaba `tools/tiles/ai_gen/` en la máquina de dev —
y por eso **v1.4.0 crasheaba al arrancar**.

Estaban en dos copias locales del repo (verificadas con MD5 idéntico), así
que se recuperaron: 78 KB, 6 tiles de 320×480. **No se regeneraron con AI**
— son los originales.

Además, el fondo ya no es "la galaxia de 3 panels de v1.6 encima del
parallax" (dos fondos superpuestos, el de arriba tapaba el bueno): ahora
el modo ASTEROID NEBULA dibuja **los tiles** y el SPACE VOID dibuja solo
estrellas.

## 🎮 Menú post-cinematica

Después de la cinemática (o `ESC` para saltarla) aparece el menú:

```
VOID HUNTER

> NEW GAME
  BOSS TIME
  BACKGROUND

ARROWS: NAVIGATE   ENTER: SELECT   ESC: BACK
```

- **NEW GAME** → el flujo normal
- **BOSS TIME** → directo a la pelea con GOLIATH
- **BACKGROUND** → SPACE VOID / ASTEROID NEBULA

En el título, `1-4` o `←→` cambian el tema del fondo (azul / teal / ámbar /
**purple_dusk**, que es el default).

## 🔫 Sistema de 4 armas (BLOQUE 72 + 73 Fase A/B/C)

Portado desde la línea de v1.5.0+ para que esta release **no sea una
regresión** respecto de v1.6.3:

- 4 slots de arma en el HUD, con animación de pop
- Los asteroides MINE sueltan THICK / LASER / FLAME / DOUBLE
- Cada arma tiene su propia función de disparo, su bullet y su SFX
- Input: rueda del mouse, teclas, y fire con el botón derecho

## 🔧 Fixes de fondo

- **El juego ya no crashea al arrancar.** `TileManager` pedía los tiles que
  nunca estuvieron en git. Ahora un set de tiles ausente es un estado
  soportado (degrada al fondo procedural) en vez de un `FileNotFoundError`.
- **`--boss` ya no es un stub.** Caminaba
  `TITLE → ACT_INTRO → GAMEPLAY → BOSS_INTRO → BOSS_FIGHT` en vez de
  imprimir "full integration in next BLOQUE".
- **El docstring de `src/audio/music.py`** tenía un escape inválido (`\A`)
  que rompía `py_compile`.

## 📦 Descarga

- `VoidHunter-v1.7.0-win64.zip` → descomprimir y correr `void-hunter-v1.7.0.exe`
- Un solo archivo, sin instalador. Windows x64.

---

## ✅ Verification

| Check | Resultado |
|---|---|
| `void-hunter-v1.7.0.exe --check` | `VOID HUNTER check OK` — 15 scenes, 18 waves, 4 bosses |
| Suite completa | 8 failed / 2818 passed / 7 skipped — los 8 son pre-existentes documentados |
| Tests del sistema de 4 armas | 55 passed |
| Escudo de GOLIATH | 20 tests (anclaje, rampa, láser, capa de impacto) |
| `get_sprite_shield_ellipse` en los 60 frames | cx 57..63.5, rx 7..11, ry 9..13 — todos a la derecha |
| Láser del ojo | borde superior en el ojo (y=62 vs ojo y=63); 1 s después, rayo x=191 = ojo x=191 |
| Tiles del Asteroid Approach | 10/10 MD5 únicos × 6 animaciones de GOLIATH; 0 frames con margen <2px |
| `--boss goliath --easy --duration 60` | `jumped to GOLIATH (act 1)`, exit 0, sin crash |
| Smoke del flujo completo | TITLE → CINEMATIC → MENU → ACT_INTRO → GAMEPLAY → BOSS_FIGHT, OK |

Evidencia visual en `tools/playtest_out/`:
- `goliath_shield_sin_ovalo_bloque67.png` — escudo sin óvalo: nada / parpadeo / calor
- `eye_laser_bloque67.png` — el rayo saliendo del ojo
- `bg_asteroid_nebula_v140.png` — el fondo morado de v1.4.0 vs space void
- `final_phase2_idle.png` — el óvalo medido sobre la placa

## ⬇️ Como jugar

1. Descargá `VoidHunter-v1.7.0-win64.zip` (~273 MB).
2. Extraé en cualquier carpeta.
3. Doble-click en `void-hunter-v1.7.0.exe`.
4. Pasá la title screen y la cinemática para llegar al menú.

El menú también está disponible vía flag:
```
void-hunter-v1.7.0.exe --boss goliath
```
salta directo a la pelea (no pasa por el menú).

En el título, `1-4` o `←→` cambian el tema del fondo. Default: **purple_dusk**.

## 💻 Requisitos

Windows 10/11 64-bit · ~290 MB disco · ~200 MB RAM

---

**Assets:** 321 MB (la línea v1.4.0 tiene 150 MB menos que v1.6.3: no
trae los sprites del sistema de armas ni los paneles de galaxia nuevos).

**Nota sobre la línea:** esta release sale de la rama
`bloquec-67-goliath-port`, que es la línea v1.4.0 con el trabajo de
GOLIATH y el menú portados encima. `master` sigue siendo la línea v1.6.3.

