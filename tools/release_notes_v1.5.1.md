# VOID HUNTER v1.5.1 — GOLIATH Shield + crash fix

> Hotfix sobre v1.5.0. Dos cambios: el escudo de GOLIATH ahora se ve, y el
> juego ya no crashea al abrir.

---

## 🛡️ El escudo de GOLIATH ahora es visible

El escudo **ya existía como mecánica** desde BLOQUE 53a — los disparos del
jugador lo consumían, la barra de carga subía, y a los 20 hits el jefe
disparaba su láser. Pero **nunca se dibujó**. El jugador disparaba a un
hitbox invisible y no tenía forma de saber cuándo venía el láser.

Ahora el escudo es un **óvalo translúcido montado en el brazo izquierdo**
de GOLIATH, que cambia de color con la carga:

| Hits | Color | Qué se ve |
|------|-------|-----------|
| 0 | Hierro gris | Estado normal, sin glow |
| 1-9 | Hierro → azul medio | Empieza a brillar |
| 10-16 | Azul medio | Carga media |
| 17-19 | Cyan → blanco brillante | Casi listo, glow máximo |
| 20 | — | El jefe dispara el láser cargado |

El glow exterior pulsa y crece con la carga, así que el estado del escudo
se lee desde cualquier distancia.

### Un solo ancla para tres consumidores

El óvalo visual, la hitbox contra la que colisionan tus disparos, y el
origen del láser leen **la misma función** (`_goliath_shield_center`).
No pueden desincronizarse entre sí — que fue exactamente lo que pasó
repetidamente entre BLOQUE 65 y 66.4f, y lo que el usuario reportó como
"el escudo no coincide con lo que veo".

### Ancla por frame

El óvalo se ancla a la placa de escudo **por color**, no por posición
fija. La placa es un disco de latón dentro de la armadura dorada; es el
único cúmulo con esa firma de color en todo el sprite, así que el ancla
sigue la placa en cada frame de cada animación sin tabla de coordenadas
a mano.

Un intento anterior anclaba en el borde derecho de la silueta — que es la
junta de la jabalina, no el escudo — y ponía el óvalo completamente
fuera del cuerpo.

### Centroid alignment

Los frames que se inclinan (javelin/frame_03 tiene `dx=+20`) ahora alinean
su cuerpo con el ancla del mundo en vez de amontonarse contra el borde
del viewport. El escudo sigue al cuerpo porque leen el mismo offset.

---

## 🐛 Fix: el juego crasheaba al abrir

**Este bug venía desde antes de la sesión** — es por eso que v1.4.0 no
arrancaba.

**Causa raíz**: `Assets/background/tiles/act1/` no existe en el repo. Los
6 PNGs de tiles fueron generados por `tools/tiles/ai_gen/` y nunca se
commitearon. `TileManager` lanzaba `FileNotFoundError` desde su
constructor, y `ParallaxBackground` lo construye durante
`Game.register_scenes()` — o sea, antes de llegar a la pantalla de título.

```
Unhandled exception in script
Failed to execute script 'main' due to unhandled exception:
Tiles directory not found: ...\Assets\bac...
  File "src\systems\tile_manager.py", line 27, in __init__
```

**Fix**: `TileManager` ahora trata un directorio de tiles ausente,
incompleto o con un archivo ilegible como un estado soportado
(`available=False`) y dibuja nada. El strip procedural de galaxy — que ya
era el default de los actos 2-4 — pasa a ser el fondo. El juego es
jugable sin los tiles; solo pierde el fondo pintado a mano del nivel 1.

Los 31 tests que fallaban por esto también están arreglados: los 5 que
dependen de los tiles llevan un `skipif` que se re-activan solos si los
assets alguna vez se commitean.

---

## ✅ Verificación

| Check | Resultado |
|-------|-----------|
| `void-hunter-v1.5.1.exe --check` | `VOID HUNTER check OK` — 9 escenas, 18 waves, 4 bosses |
| Tests boss/goliath/shield/javelin | **212 passed, 1 skipped** |
| Tests de tile_manager | **9 passed, 5 skipped** (los 5 = assets ausentes) |
| Evidencia visual | `tools/playtest_out/goliath_shield_3states_bloque73.png` |

Captura de evidencia (3 paneles, 3x zoom): shield en 0 hits (hierro),
12 hits (azul medio), 19 hits (cyan brillante).

---

## ⬇️ Como jugar

1. Descargá `VoidHunter-v1.5.1-win64.zip` (~422 MB).
2. Extraé en cualquier carpeta.
3. Doble-click en `void-hunter-v1.5.1.exe`.

```
void-hunter-v1.5.1.exe --check
void-hunter-v1.5.1.exe --boss goliath --easy --duration 60
```

## 💻 Requisitos

Windows 10/11 64-bit · ~430 MB disco · ~200 MB RAM

---

## 📚 Documentación

- `docs/OPERATIONS.md` — guía de `gh` CLI, PAT, workflow de releases
- `docs/KNOWN_ISSUES.md` — issues conocidos
- `docs/superpowers/specs/` — specs de diseño por BLOQUE