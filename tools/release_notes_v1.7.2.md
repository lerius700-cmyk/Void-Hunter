# VOID HUNTER v1.7.2 (BLOQUE 67) — la línea v1.4.0 sin armas de más

> Release de corrección. La v1.7.1 había metido el sistema de 4 armas
> (BLOQUE 72 + 73 Fase A/B/C), que **no pertenece a la base v1.4.0**.
> Esto lo saca.

---

## 🐛 Qué estaba mal

La base de este trabajo es **v1.4.0 (BLOQUE 71)**, y v1.4.0 **no tiene
sistema de armas**:

- no hay 4 tipos de arma (THICK / LASER / FLAME / DOUBLE)
- no hay los 4 cuadros del HUD donde se guardan las armas
- no hay remap de input para cambiar de arma
- no hay los 4 SFX de disparo por arma

Peor: el port arrastraba el commit `d43f7be` de BLOQUE 73 Fase A, que
**elimina el láser de carga del LMB** — o sea, una feature que v1.4.0 sí
tenía. Se perdía algo de la base para ganar algo que no correspondía.

## 🔧 El fix

Se revierte el commit del sistema de armas completo. Vuelven a su estado
exacto de v1.4.0 (`d70b8da`):

| Archivo | Estado |
|---|---|
| `src/ui/hud.py` | sin los 4 cuadros de slots |
| `src/entities/asteroid.py` | `PowerupKind` solo con `WEAPON` |
| `src/entities/enemies/enemy.py` | sin los 4 tipos de arma |
| `src/audio/synth.py` | sin los 4 SFX de arma |
| `src/core/settings.py` | sin el remap de input de armas |
| `src/entities/weapon_slot.py` | eliminado |
| `Assets/sprites/weapons/*.png` | eliminados (4) |
| `Assets/sounds/{shoot_thick,laser_hum,flame_loop,shoot_double}.wav` | eliminados (4) |
| 7 tests del sistema de armas | eliminados |

**Se conserva** el powerup `WEAPON` original de v1.4.0
(`PowerupKind.WEAPON`) y los eventos `WEAPON_LEVEL_UP` /
`WEAPON_SPECIAL_UNLOCKED` del event bus: son de la base y no se tocan.

## ✅ Qué trae esta release

Exactamente lo que corresponde a la línea v1.4.0 + el trabajo pedido:

- **GOLIATH** (BLOQUE 66): 60 frames animados, escudo con el óvalo
  **invisible** medido sobre la placa de su brazo derecho, capa de calor
  que se pone **roja al primer impacto** y se calienta, parpadeo de
  impacto, **láser naranja grueso** al cargar, y el **láser del ojo
  saliendo del ojo** (y siguiendo al ojo cuando GOLIATH se mueve)
- **Menú post-cinematica** (BLOQUE 73.7): NEW GAME / BOSS TIME /
  BACKGROUND, con submenu SPACE VOID / ASTEROID NEBULA
- **Fondo ASTEROID NEBULA real de v1.4.0**: los 6 tiles del "Asteroid
  Approach" (BLOQUE 64), que nunca se commitearon y se recuperaron de
  dos copias locales del repo
- **El `.exe` completo**: la v1.7.0 se publicó sin
  `Assets/imagen fondo del juego.jpg`, así que el fondo pintado del boss
  fight no aparecía (negro con estrellas). Corregido en v1.7.1 y
  verificado en v1.7.2 comparando capturas del `.exe` contra
  `python main.py`

## 📦 Descarga

- `VoidHunter-v1.7.2-win64.zip` → descomprimir y correr
  `void-hunter-v1.7.2.exe`
- Un solo archivo, sin instalador. Windows x64.

---

**Suite:** 8 failed / 2772 passed / 7 skipped — los 8 son fallos
pre-existentes documentados. Cero regresiones.

**Verificación visual:** el `.exe` y `python main.py` corriendo desde el
mismo worktree se ven **idénticos** — mismo fondo, mismo HUD (sin los 4
cuadros de armas), mismo GOLIATH.

## ⬇️ Como jugar

1. Descargá `VoidHunter-v1.7.2-win64.zip` (~276 MB).
2. Extraé en cualquier carpeta.
3. Doble-click en `void-hunter-v1.7.2.exe`.
4. Pasá la title screen y la cinemática para llegar al menú.

## 💻 Requisitos

Windows 10/11 64-bit · ~290 MB disco · ~200 MB RAM

> El `.exe` tarda ~2.3 s en abrir la ventana (extracción onefile). No es
> un bug: es el costo del ejecutable de un solo archivo.
