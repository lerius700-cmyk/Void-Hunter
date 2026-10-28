# VOID HUNTER v1.8.0 (BLOQUE 74) — el pipeline de sprites: el runtime deja de medir el arte

> Release de la línea v1.4.0 (BLOQUE 71) + GOLIATH + menú post-cinematica.
> Esta vez el `.exe` **sí** trae el trabajo: la medición del arte se hace en
> build time y se hornea en un archivo. El runtime solo lee.

---

## 🐛 Qué estaba mal

El runtime **medía el arte** cada vez que veía un frame por primera vez:
escaneba los píxeles del PNG para encontrar el ojo y la placa del escudo
(3.9 ms por frame, 60 frames). Eso es trabajo de build time, no de runtime.

Y el arte generado por IA venía **desregistrado**: cada frame de una misma
animación tenía al jefe en otro lugar dentro del canvas, con el escudo
hasta 20 px corrido. El motor lo compensaba a ojo, con constantes.

Dos frames estaban directamente **rotos**: el generador había dibujado a
GOLIATH **girado**, con el escudo en el brazo izquierdo. El juego lo
compensaba con una elipse fija clavada en un lado, así que el escudo
invisible no seguía al brazo.

## 🔧 El fix

BLOQUE 74 separa las dos cosas:

- **`manifest.toml`** (`Assets/sprites/bosses/goliath/`) es la **spec** del
  set, editada a mano: canvas, anchor, clips (id ↔ dir), fps, tolerancias y
  las reglas de detección de cada feature.
- **`anchors.toml`** es la **medición horneada** de los 60 frames: el offset
  que cancela el desregistro, el ancla del ojo y la elipse del escudo, con
  su procedencia (`measured` / `interpolated`).
- **`tools/sprite_pipeline/`** es el pipeline: `audit.py` clasifica cada
  frame en uno de siete estados, `repair.py` repara lo reparable y `run.py`
  corre todo.

El runtime ahora **lee la tabla** en vez de escanear píxeles.

### Lo que se ve

- Los **dos frames girados** quedaron espejados: el escudo vuelve al brazo
  derecho y el pipeline da **0 FAIL** (antes: 2).
- El **óvalo invisible** y el **origen del láser** pasan de una constante
  de fallback a la **posición real medida** en 8 de los 60 frames. Antes el
  láser salía siempre de (48, 20); ahora sale del ojo de verdad.
- El óvalo **sigue invisible** (decisión de BLOQUE 67): solo se dibujan la
  capa de calor y el parpadeo de impacto.

### Lo que además se arregló

- **7 de los 8 "fallos pre-existentes" del proyecto no eran fallos.** Eran
  accidentes de orden de recolección: seis módulos de test llamaban
  `pygame.quit()` en su teardown y sin `tests/conftest.py` el resultado
  depended de qué módulo salía primero por orden alfabético. Ahora la suite
  da el mismo resultado con cualquier orden.
- Un **bug real de color**: la firma que identifica la placa del escudo
  también la cumplía el haz del ojo horneado, así que el detector medía el
  haz en vez de la placa. El filtro correcto es un **predicado** (el haz es
  un degradado, no cuatro colores exactos) y con eso el detector coincide
  exactamente con el runtime.

## ✅ Qué trae esta release

| | |
|---|---|
| **Línea base** | v1.4.0 (BLOQUE 71) — **sin** sistema de armas extra |
| **Jefes** | 4 (GOLIATH incluido, con sus 6 animaciones de 10 frames) |
| **Escenas** | 15 · 18 oleadas |
| **Suite** | 2,886 pass · 1 fail pre-existente · 6 skipped |
| **`.exe`** | 278 MB, un solo archivo, Windows x64 |

## 📦 Descarga

- `VoidHunter-v1.8.0-win64.zip` → descomprimir y correr
  `void-hunter-v1.8.0.exe`
- Un solo archivo, sin instalador. Windows x64.

---

**Suite:** 1 failed / 2,886 passed / 6 skipped — el único fallo es
`test_paths_no_star_shapes`, una aserción real de geometría del
LissajousPath que ya venía de antes. Cero regresiones.

**Verificación del `.exe` congelado:** el bundle incluye el `manifest.toml`
y el `anchors.toml` en `<_MEIPASS>/Assets/sprites/bosses/`, comprobado
leyendo el archivo y en vivo mientras el juego corría el boss fight.
`void-hunter.exe --check` → 15 scenes / 18 waves / 4 bosses.
`void-hunter.exe --boss goliath --easy --duration 25` → exit 0.

## ⬇️ Como jugar

1. Descargá `VoidHunter-v1.8.0-win64.zip` (~278 MB).
2. Extraé en cualquier carpeta.
3. Doble-click en `void-hunter-v1.8.0.exe`.
4. Pasá la title screen y la cinemática para llegar al menú.

## 💻 Requisitos

Windows 10/11 64-bit · ~290 MB disco · ~200 MB RAM

> El `.exe` tarda ~2.3 s en abrir la ventana (extracción onefile). No es
> un bug: es el costo del ejecutable de un solo archivo.

---

**Si te interesa el pipeline:** `docs/handoffs/HANDOFF-SPRITE-PIPELINE-2026-10-27.md`
tiene los cuatro comandos, los siete estados y los truth anchors.
