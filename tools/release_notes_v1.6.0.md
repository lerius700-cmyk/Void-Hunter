# VOID HUNTER v1.6.0 — GOLIATH actually animates

> La corrección que faltaba. El escudo de v1.5.1 ahora está montado sobre un
> jefe que **se mueve de verdad** — no sobre una imagen estática.

---

## 🎬 GOLIATH volvió a animarse (el bug de fondo)

**Lo que pasaba**: los 10 PNGs de cada animación de GOLIATH eran **copias
idénticas**. Seis animaciones, seis imágenes distintas, sessenta archivos que
se llamaban `frame_00` … `frame_09` pero no cambiaban nunca.

GOLIATH era una foto con nombre de animation frame. El escudo que pusimos en
v1.5.1 se veía bien sobre el torso — pero ese torso nunca se movía.

**Causa raíz**: el commit `562eb58` ("BLOQUE 64.B stage 1 — 6 GOLIATH anims
x 10 frames borderless") subió 10 copias byte-idénticas por animación. Ese
commit **es ancestro de master** y entró *después* de que BLOQUE 65 ya
hubiera generado los 10 frames distintos de cada animación. O sea: el
regenerado se revirtió en silencio y nadie lo notó.

**Prueba**: el md5 de los 10 PNGs de cada carpeta colapsa a **1 hash único**
en las seis animaciones. El mismo chequeo en `ac53596` da **60/60 únicos**.

```
phase1_idle    frames unicos: 1  ← antes
phase1_idle    frames unicos: 10 ← ac53596 (BLOQUE 65)
```

**Este también era tu "cortado"**. El `javelin/frame_03` que reportaste al
principio de la sesión no tenía bug de ancla ni de viewport — lo medí y lo
descarté. Era que `javelin/frame_03` era **la misma imagen que los otros
nueve frames**, así que no existía animación de lanzamiento. Y la pose de AI
que sí había, había perdido el hombro derecho.

**Restaurado**: los 60 frames desde `ac53596`. 60/60 únicos.

---

## 🛡️ El escudo (de v1.5.1), ahora recalibrado

El óvalo se ancla a la placa por color (latón dentro de la armadura dorada),
con un clamp nuevo a una caja alrededor del centro del sprite. La firma de
color también dispara en remaches de hombrera, la punta de hierro de la
jabalina y la cresta del casco — esos caían en col 28 (dentro del torso) y
col 66 (fuera del cuerpo). La placa siempre está en el torso, así que lo
que cae fuera de la caja no es la placa.

| Hits | Color | Estado |
|------|-------|--------|
| 0 | Hierro gris | Sin glow |
| 1-9 | Hierro → azul medio | Empieza a brillar |
| 10-16 | Azul medio | Carga media |
| 17-19 | Cyan → blanco | Casi listo, glow máximo |
| 20 | — | El jefe dispara el láser cargado |

Un solo ancla para los tres consumidores (visual, hitbox, origen del láser),
así que no pueden desincronizarse.

---

## 🐛 Fix: el juego crasheaba al abrir

**Este bug venía desde antes de la sesión.**

`Assets/background/tiles/act1/` no existe en el repo — los 6 PNGs de fondo
fueron generados por `tools/tiles/ai_gen/` y nunca se commitearon.
`TileManager` lanzaba `FileNotFoundError` desde su constructor, y
`ParallaxBackground` lo construye durante `Game.register_scenes()`, o sea
antes de llegar a la pantalla de título.

```
Unhandled exception in script 'main'
Tiles directory not found: ...\Assets\bac...
  File "src\systems\tile_manager.py", line 27, in __init__
```

Ahora un directorio ausente, incompleto o ilegible es un estado soportado
(`available=False`) y dibuja nada — el strip procedural de galaxy pasa a
ser el fondo. Los 31 tests que fallaban por esto también están arreglados.

---

## 🎮 Las seis animaciones

`tools/playtest_out/b73_<anim>_10f.png` — los 10 frames de cada una, a 4×,
tal como los ve el runtime:

| Animación | Qué hace ahora |
|-----------|----------------|
| `phase1_idle` | Respiración de reposo |
| `phase2_idle` | Reposo con grietas y armadura dañada |
| `javelin` | **10 poses de lanzamiento distintas** |
| `laser` | Apuntando el láser del escudo |
| `purple_bullet` | Disparo de balas púrpura |
| `death` | 10 pasos de derrumbe |

---

## ✅ Verificación

| Check | Resultado |
|-------|-----------|
| `void-hunter-v1.6.0.exe --check` | `VOID HUNTER check OK` — 9 escenas, 18 waves, 4 bosses |
| Frames únicos | **60/60** en las 6 animaciones |
| Tests boss/goliath/shield/javelin | **212 passed, 1 skipped** |
| Tests tile_manager | **9 passed, 5 skipped** (los 5 = assets ausentes) |

---

## ⬇️ Como jugar

1. Descargá `VoidHunter-v1.6.0-win64.zip` (~423 MB).
2. Extraé en cualquier carpeta.
3. Doble-click en `void-hunter-v1.6.0.exe`.

```
void-hunter-v1.6.0.exe --check
void-hunter-v1.6.0.exe --boss goliath --easy --duration 60
```

Para ver el jefe sin jugar: `--boss goliath` entra directo a la pelea.

## 💻 Requisitos

Windows 10/11 64-bit · ~430 MB disco · ~200 MB RAM