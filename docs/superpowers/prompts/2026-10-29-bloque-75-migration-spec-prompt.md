# PROMPT — Especificación BLOQUE 75: migración del pipeline de sprites, 2 fases con gate

> **Nivel:** `°°°°` Ultimate · **Dominio:** arquitectura de juegos 2D / pipeline de assets / pixel-art
> **Destino:** el agente que escriba el spec de BLOQUE 75. Este prompt NO es el spec: es el prompt que produce el spec.
> **Cómo usarlo:** pasame este prompt tal cual. El agente debe devolver **un solo documento de spec**, sin escribir código.

---

## 📌 0. Antes de empezar: dónde estás y qué leés primero

Este prompt es la **semilla** del spec, no el spec. El **contexto vive en el repo**, no en este documento: antes de escribir una línea, leé el repo. El orden es el del protocolo ADUANA del proyecto:

| # | Archivo | Qué te da |
|---|---|---|
| 1 | `CLAUDE.md` | La identidad del proyecto, las reglas que no se rompen, y la sección **"Trabajo multi-agente"** (un worktree y una rama por agente). |
| 2 | `CONTEXT.md` | El switch: qué silos existen y a cuál pertenece este trabajo (`docs/superpowers/`). |
| 3 | `docs/superpowers/CONTEXT.md` | La misión del silo y dónde viven los prompts, specs y planes. |
| 4 | `.synapse` | El puntero: `active_context_pointers` dice qué archivos leer primero. |
| 5 | `docs/superpowers/specs/2026-10-29-agent-context-handoff-design.md` | Por qué el repo es el único canal entre agentes, y qué se decidió acá. |

**Dónde trabajás.** La base de todo trabajo nuevo es la rama `bloquec-67-goliath-port` (v1.8.0). **`master` NO es la base**: está en v1.6.3, es otra línea y no recibe merges (ver R3). No trabajes sobre `master` ni sobre `bloquec-67-goliath-port` directamente — creá tu propia rama y tu propio worktree, porque puede haber otro agente sobre este mismo repo al mismo tiempo:

```powershell
cd F:\AI\MM\void-hunter
git worktree add .worktrees\bloquec-75-<tu-rama> -b bloquec-75-<tu-rama> bloquec-67-goliath-port
```

**Antes de tocar nada, verificá que el pipeline sigue bien.** Este es el guard de contrato que se versionó junto a este prompt: mide sobre el código que se está por migrar, no sobre un plan.

```powershell
python tools\sprite_pipeline\verify_contract.py goliath    # -> CONTRACT OK, exit 0
python -m pytest tests/ --tb=no                            # -> todo pass salvo test_paths_no_star_shapes (fallo pre-existente) + 6 skipped
```

> **No comitees nada hasta que el usuario lo pida.** Es una regla explícita del proyecto (BLOQUE 58.14).

---

## 📌 1. Contexto y Rol

Sos un **game architect senior specialize en pipelines de assets 2D para juegos pixel-art**, con experiencia concreta en: registro de sprites por medición de silueta, composición por capas declarativa, y migración incremental de un runtime procedural a uno data-driven sin regresiones visuales.

**El proyecto es VOID HUNTER**: un shoot'em up vertical 2D pixel-art, Python 3.11 + pygame 2.6, resolución interna 320×480, 120 FPS fijo, ~29.000 LOC en `src/`, ~25.500 LOC en `tests/`. Todo el runtime es pygame directo: `Surface.blit` y `pygame.draw.*`, sin motor externo, sin numpy (salvo el lowpass de audio de la pausa).

**Dónde estamos.** En BLOQUE 74 (v1.8.0) se construyó un **pipeline de sprites** que ya está en producción y funcionando sobre el jefe GOLIATH:

- `Assets/sprites/bosses/goliath/manifest.toml` — la **spec** editada a mano de un set de animación: canvas, anchor, clips (id ↔ dir), fps, tolerancias, y las reglas de detección de cada feature.
- `Assets/sprites/bosses/goliath/anchors.toml` — la **medición horneada** de los 60 frames (offset de cuerpo, ancla del ojo, elipse del escudo + procedencia).
- `src/anim/` (1.003 LOC): `manifest.py` (loader, 339), `measure.py` (primitivas de píxel, 316), `parts.py` (renderer de una part, 158), `anchors.py` (lector, 100), `clip.py` (`ClipPlayer`, 90).
- `tools/sprite_pipeline/` (820 LOC): `audit.py` (mide y clasifica cada frame en 7 estados, 546), `repair.py` (reparaciones deterministas, dry por default, 129), `run.py` (validate → audit → repair → re-audit → anchors, 121).
- ~10 archivos de test nuevos como guards.

**El modelo de composición que ya existe.** Una `Part` declara: `id`, `draw` (`frames` | `ellipse` | `point` | `procedural`), `pivot` (`centroid` | `detect` | `fixed`), `z` (orden), `offset`, `scale`, `radii`, `detect` (la regla de detección) y `on_missing` (`interpolate` | `fallback` | `skip`). El `ClipPlayer` compone las parts de un clip en orden de `z`.

**Por qué este BLOQUE.** La metodología de BLOQUE 74 es genérica en diseño pero está probada **solo sobre un set que es un jefe**. Y el juego **no** usa capas de forma declarativa: el frame de gameplay sigue siendo una lista de draws escritas a mano: el bucle principal (`src/ui/gameplay_runtime.py:3973-4165`) invoca ~16 de ellos, y el archivo tiene **42** métodos `self._draw_*` en total.

---

## 🎯 2. Consulta / Tarea

Escribí el **spec de BLOQUE 75: la migración del pipeline de sprites**, en **dos fases con un gate explícito entre ellas**.

### Fase 1 — Los sets de enemigos entran al pipeline

Los enemigos **ya están guardados en layout de frames**, igual que GOLIATH. Hay que convertirlos en sets declarados:

| set | animaciones | frames por anim | canvas declarado |
|---|---|---|---|
| `cruiser` | damage, death, idle, thrust | 10 | 14×10 |
| `drone` | damage, death, idle, thrust | 10 | **medir** |
| `heavy` | damage, death, idle, thrust | 10 | 18×12 |
| `kamikaze` | damage, death, idle, thrust | 10 | 10×10 |
| `mine_asteroid` | closed (5), death (10), open (1), open1 (1), open2 (1) | — | **medir** |
| `scout` | damage, death, idle, thrust | 10 | 12×8 |
| `sniper` | damage, death, idle, thrust | 10 | **medir** |
| `turret` | damage, death, idle, thrust | 10 | **medir** |

Total: **304 archivos `frame_*.png`**, de los cuales **298 son vivos** (280 de los 7 sets × 4 animaciones × 10 frames, más 18 de `mine_asteroid`) en **34 directorios de animación**. Los 6 restantes están en un backup anidado: `Assets/sprites/enemies/mine_asteroid/_backup_pre_bloque_65/closing/` (3 frames) y `.../opening/` (3 frames). Además hay **2 PNG sueltos fuera del layout de frames** en `mine_asteroid/`: `_new_reference_closed.png` y `_new_reference_open.png` (49 KB y 51 KB, uno por cada estado visual).

El spec tiene que decidir qué se hace con las tres cosas: el backup anidado (¿se borra, se mueve, o se declara set archivado?), los 2 PNG de referencia sueltos (¿son material de referencia para el arte, o assets que el juego lee?), y si `_backup_pre_bloque_65` debe ser un set más del pipeline o quedar fuera.

El objetivo de la Fase 1 es **probar que la metodología es genérica**: un set que no es un jefe entra al pipeline, se audita, se repara si hace falta, y produce un `anchors.toml` determinista con 0 FAIL.

Cosas que el spec tiene que resolver por set: el **canvas propio** (NO es 96×80 como GOLIATH), el **fps**, el **loop** (la muerte es one-shot; `idle` y `thrust` probablemente no), las **tolerancias** (`scale_tolerance`, `side_tolerance`), y si hay **features que detectar** (el telegrafiado rojo y el flash blanco de daño se dibujan hoy como overlay en `src/ui/gameplay_runtime.py:4910 _draw_enemy`, no como parte del sprite).

### Gate entre fases

**La Fase 2 no arranca hasta que la Fase 1 cumpla su criterio de aceptación** (ver §4). El spec tiene que hacer el gate explícito y verificable, no una frase.

### Fase 2 — El juego por capas: `LayerStack`

Hoy el frame se compone con una lista de draws hardcodeados. El bucle principal del frame (`src/ui/gameplay_runtime.py:3973-4165`) invoca estos, en este orden:

```
polvo ambiente → enemigos → asteroides/powerups → boss → lanza del boss →
láser del escudo → balas → misiles → afterimage del jugador → jugador →
láser continuo → retícula → score popups → indicador de oleada →
frame del área de juego → líneas de velocidad
```

**Ese orden no puede cambiar.** Es la diferencia entre "refactorizar" y "romper el juego": el afterimage se dibuja ANTES del jugador, y los popups de score DESPUÉS del retículo. Un LayerStack que reordene aunque sea un draw cambia lo que se ve.

Además, el HUD y el fondo (`ParallaxBackground`) **no pasan por el compositor**: tienen su propio camino de dibujo. Y el `SceneManager` (`src/core/scene_manager.py`) tiene **15** `GameState` — que es una máquina de estados de **escenas**, no de capas.

El spec tiene que diseñar:

- **`Layer`**: la abstracción que falta. Hoy `Part` cuelga de un clip; una capa de juego necesita identidad, `z`, y `draw(target, ctx)`, con animación **opcional**.
- **`LayerStack`**: el orden global del frame, declarativo, reemplazando la lista de draws del bucle principal.
- **`DrawContext`**: hoy cada draw recibe `target, ox, oy` o `shx, shy` a mano; hace falta un contexto único (origen, escala, tiempo).
- **La frontera con el `SceneManager`**: cómo conviven capas y `GameState` sin duplicar el concepto.

Y el spec tiene que decidir explícitamente si la Fase 2 incluye o excluye: HUD, fondo, balas, jugador, partículas, overlays de depuración.

### Lo que el spec NO tiene que hacer

No tiene que escribir código, ni implementar, ni migrar assets. Es el **documento de diseño** que precede a la implementación.

---

## ⚙️ 3. Especificaciones

### 3.1 Restricciones no negociables

| # | Restricción | Origen |
|---|---|---|
| R1 | **Prohibido regenerar arte con IA.** Los frames de GOLIATH (BLOQUE 73.3) y de los enemigos (BLOQUE 64/65) son curados y aprobados por el usuario. | `CLAUDE.md`; memoria del proyecto |
| R2 | **Las constantes del escudo de GOLIATH no se tocan**: `DX=0`, `DY=3`, `RX=11`, `RY=17`, `R=11`, `RX_SCALE=0.78`. El óvalo es **invisible** por diseño (BLOQUE 67): solo se dibujan la capa de calor (elíptica) y el parpadeo de impacto. | `src/ui/gameplay_runtime.py`, `src/anim/parts.py` |
| R3 | **`master` no es la base.** `master` está en v1.6.3 con 8 commits sin pushear. La línea v1.4.0 vive en la rama `bloquec-67-goliath-port`. Todo merge es contra esa rama. | git |
| R4 | `src/` es **stdlib + pygame**. `numpy` está prohibido en `src/` (excepción única: el lowpass de audio de la pausa). `tools/` puede usar lo que haga falta. | `CLAUDE.md` |
| R5 | `pyproject.toml` exige **mypy `strict = true`** con 0 errores. `src/ui/` y `src/entities/` arrastran ~145 errores pre-existentes fuera del gate; no es trabajo de este BLOQUE, pero **no se puede empeorar el delta**. | `pyproject.toml` |
| R6 | **El hash del manifest se calcula sobre texto normalizado**, no sobre bytes crudos: con `core.autocrlf=true` y sin `.gitattributes` el mismo blob sale LF o CRLF según el checkout, y un hash crudo vuelve rojo el test de frescura en la mitad de los checkouts. | BLOQUE 74, fix `def5fe4` |
| R7 | El pipeline es **headless y determinista**. Sin IA, sin red, sin reloj. Mismo input → mismo `anchors.toml` byte a byte. | `tools/sprite_pipeline/` |

### 3.2 Requisitos técnicos de la Fase 1

- **Un `manifest.toml` por set** en `Assets/sprites/enemies/<kind>/manifest.toml`, con la misma forma que el de GOLIATH.
- El **canvas de cada set sale de la medición real**, no de `ENEMY_CONFIGS` (que son el **hitbox**, no el canvas del sprite: scout 12×8 es el hitbox, el sprite es más grande). El spec tiene que distinguir **canvas del sprite** vs **hitbox de colisión** y decidir si el compositor necesita ambas medidas.
- Cada set produce `Assets/sprites/enemies/<kind>/anchors.toml`.
- `tools/sprite_pipeline/audit.py` tiene que poder auditar un set de enemigo **sin tocar GOLIATH**: el `set` del CLI es hoy un nombre bajo `Assets/sprites/bosses/`. El spec tiene que decidir cómo se generaliza el descubrimiento de sets (subdirectorios, índice, configuración).
- El spec tiene que decidir **qué se hace con las 3 piezas sueltas de `mine_asteroid`**: el backup anidado `_backup_pre_bloque_65/{closing,opening}/` (6 frames), los 2 PNG `_new_reference_{closed,open}.png`, y los clips `open` / `open1` / `open2` de 1 frame cada uno (¿son estados distintos o frames sueltos de una animación?).
- El spec tiene que decidir **cómo se expresa el telegrafiado y el flash de daño**: hoy son overlays de color en `_draw_enemy` (`src/ui/gameplay_runtime.py:4910`), no parte del sprite. ¿Se modelan como `Part` de tipo `procedural`, como feature del manifest, o se quedan fuera?

### 3.3 Requisitos técnicos de la Fase 2

- `Layer` con `z`, identidad y `draw(target, ctx)`, con animación opcional.
- `LayerStack` con orden declarativo.
- `DrawContext` que unifique origen/escala/tiempo y elimine el paso manual de `ox, oy` / `shx, shy`.
- **Cero regresión visual**: el orden de dibujo actual debe quedar **exactamente** el mismo. El spec tiene que incluir el mecanismo de verificación de eso (comparación de frames, no opinión).
- El spec tiene que(**sugerir**, no decidir por el usuario) qué hacer con el `SceneManager` de 15 `GameState`: si las capas son un concepto **nuevo** (dentro de una escena) o una **generalización** del `SceneManager`.

### 3.4 Arte del documento

- Spec en **inglés** (convención del repo: `docs/superpowers/specs/`), porque el código y la documentación técnica están en inglés. Las citas al usuario van en español.
- Ubicación: `docs/superpowers/specs/2026-XX-bloque-75-sprite-migration-design.md`.
- Formato de secciones: las de BLOQUE 74 (ver `docs/superpowers/specs/2026-10-26-sprite-pipeline-design.md` como referencia de tono y densidad).

---

## ✅ 4. Criterios de Calidad

### Del spec como documento

| # | Criterio | Cómo se verifica |
|---|---|---|
| Q1 | **Cubre las 2 fases con el gate explícito** | El gate dice qué se mide, con qué comando, y qué pasa si no se cumple. |
| Q2 | **Cada decisión tiene su razón** | No hay "se hace así" sin el porqué. |
| Q3 | **Cada afirmación técnica es verificable** | Cada claim tiene un comando o un test (ver §8 Truth Anchors). |
| Q4 | **Los 7 estados del auditor están mapeados a los enemigos** | Una tabla: para cada estado, qué significa en un enemigo y si es esperable. |
| Q5 | **El riesgo de regresión visual está cubierto** | El spec define cómo se verifica que el orden de capas no cambió. |
| Q6 | **El alcance excluye explícitamente lo que no entra** | Lista de "fuera de alcance" con la razón. |
| Q7 | **Es accionable por un agente sin contexto** | Un agente nuevo puede ejecutar el spec sin preguntar nada. |

### Del resultado de la Fase 1 (criterios de aceptación del gate)

| # | Criterio |
|---|---|
| A1 | Al menos **1 set de enemigo** (no jefe) entra al pipeline: `manifest.toml` + `anchors.toml` generados, 0 FAIL. |
| A2 | `audit.py` corre sobre un set de enemigo **sin modificar** el comportamiento de GOLIATH. |
| A3 | `anchors.toml` regenerado es **byte-idéntico** en dos corridas (determinismo). |
| A4 | Los frames de los sets de enemigo **no cambian de bytes**: el pixel art es intocable (R1). |
| A5 | El hitbox y la colisión de cada enemigo **no cambian** (el juego se juega igual). |
| A6 | El pipeline corre **sin dependencia de red, IA ni reloj**. |

### Del resultado de la Fase 2

| # | Criterio |
|---|---|
| B1 | El frame de gameplay se compone **desde el `LayerStack`**, no desde la lista de `self._draw_*`. |
| B2 | El **orden de dibujo es idéntico** al actual, verificado por comparación de frames (no por inspección). |
| B3 | El HUD y el fondo tienen **un lugar definido** en el stack (o una razón explícita para quedar fuera). |
| B4 | `mypy src/anim/` sigue en 0 errores y el delta de errores en `src/ui/`/`src/entities/` no crece. |
| B5 | La suite completa no empeora: la línea base es **2.886 pass + 1 fail pre-existente + 6 skipped**. |

---

## 📋 5. Formato de Respuesta

**Un único documento Markdown**, el spec de BLOQUE 75. Estructura obligatoria:

```
# BLOQUE 75 — <título en una línea>

**Date:** <YYYY-MM-DD>
**Status:** READY FOR EXECUTION
**Author:** Lerius (idea) + <agente> (draft)
**Branch:** <a definir>
**Base:** <commit/tag de partida>

## Overview
Qué es la migración, en 3-6 líneas. La decisión en una frase.

## Contexto (el estado real, medido)
Los números verificados de hoy: sets, frames, directorios, LOC, líneas base
de la suite. Con el comando que produce cada número.

## Qué NO se hace (y por qué)
Lista de exclusiones con razón.

## Fase 1 — <los sets de enemigos>
### Qué se cambia
### El manifest por set (ejemplo completo y real, no esquemático)
### Qué tiene que decidir el implementador, y cómo se decide
### Criterios de aceptación

## El gate
Qué se mide, con qué comando, y qué pasa si no se cumple.

## Fase 2 — LayerStack
### La abstracción Layer
### LayerStack y el orden global
### DrawContext
### La frontera con SceneManager
### Criterios de aceptación

## Riesgos y mitigaciones
### FMEA
| Modo de falla | Prob. | Impacto | Mitigación | Cómo se verifica |

## Verificación
Los comandos exactos, con la salida esperada.

## File map
Qué archivo se toca, se crea o se borra, y por qué.
```

**Reglas de formato:**
- Nada de placeholders: `[...]`, `<TODO>`, `TBD`. Si un valor no se conoce, el spec dice **cómo se mide** y da el comando.
- Tablas para todo lo enumerable (sets, estados, archivos, riesgos).
- Código solo cuando sea el **contrato** (firma de una API, forma de un manifest), nunca la implementación completa.
- Español para las explicaciones al usuario; inglés para identificadores, nombres de archivo y citas textuales del código.

---

## 🧠 6. Conocimiento Experto

### 6.1 Patrones que el spec debe aplicar

**P1 — El registro del sprite se mide, no se corrige a mano.** El patrón de BLOQUE 74: el centroide ponderado por alpha de la silueta cancela el desregistro, y la corrección se aplica en el blit (`origin - canvas/2 + body_offset`). Un set nuevo hereda esto gratis. **El spec no debe proponer recentrar a mano ni "normalizar" los PNG.**

**P2 — La detección de features tiene tres niveles de robustez**, y el spec tiene que elegir el nivel por feature:
1. *Firma de color* — cuando la feature tiene color propio (`detect.method = "color"`).
2. *Forma* — cuando comparte paleta con el cuerpo: se mide el último bloque sólido de cada fila dentro de una banda (`detect.method = "shape"`).
3. *Predicado* — cuando la feature es un degradado (el haz del ojo): un predicado sobre rangos, no una lista de colores exactos. **El error de BLOQUE 74 fue exactamente usar una lista de 2 colores exactos donde hacía falta el predicado de 4.**

**P3 — La interpolación es la política por defecto para lo no medible.** `on_missing = "interpolate"`: se reconstruye desde los frames vecinos con Catmull-Rom. En GOLIATH, 7 de 60 frames no tienen placa medible y se interpolan; el óvalo igual sigue al brazo.

**P4 — La detección de lado es un probe independiente.** La regla de forma **no puede** detectar que el personaje está girado: encuentra el brazo y mide una elipse plausible que no es la placa. Hace falta un probe de color aparte, comparado contra la **mediana del clip**, con un margen explícito.

**P5 — La tolerancia se justifica con el margen, no con el número.** `side_tolerance = 14` funciona porque el desvío real de los 2 frames girados es 18.2 y 21.4, y el siguiente desvío en el lado equivocado es 10.9 (margen 3.1). **El spec tiene que exigir esa justificación para cada tolerancia nueva**, no copiarla de GOLIATH.

**P6 — Un umbral compartido o el pipeline sewedgea.** En BLOQUE 74 el auditor marcaba `CORTADO` por debajo de 2 px y el re-pad perseguía 3 px: un frame marcado podía no ser reparable nunca. Se resolvió con una constante compartida (`CORTADO_MARGIN` en `src/anim/measure.py`). **El spec tiene que auditar los umbrales del pipeline por separado de los de cada set.**

**P7 — Determinismo verificable, no declarativo.** `anchors.toml` se compara **como string** contra el re-renderizado. Por eso el hash del manifest va sobre texto normalizado (R6).

### 6.2 Anti-patrones que el spec debe evitar explícitamente

| Anti-patrón | Por qué está prohibido aquí |
|---|---|
| **Regenerar el arte** | R1. Si un set no sirve, se documenta el problema; no se regenera. |
| **Recentrar los PNG a mano** | El registro se mide. Tocar los bytes rompe la paridad con el `.exe` publicado y con R1. |
| **Heredar tolerancias de GOLIATH sin medirlas** | P5. `side_tolerance=14` no significa nada para un set de 12×8. |
| **Asumir que el canvas es 96×80** | Es de GOLIATH. Cada set tiene el suyo. |
| **Copiar el hitbox como canvas** | `ENEMY_CONFIGS.width/height` es el **hitbox**, no el sprite. El sprite es más grande. |
| **Poner el telegrafiado dentro del manifest** | El telegrafiado y el flash de daño son overlays de runtime, no features del sprite. Modelarlos como feature sería medir píxeles que no existen. |
| **Hacer la Fase 2 sin el gate** | La Fase 2 es un rewrite del frame. Sin la Fase 1 probada, no hay evidencia de que el compositor soporte sets no-jefe. |
| **UnLayerStack que reordene el frame** | B2: el orden de dibujo **no puede** cambiar. Es un refactor, no una mejora visual. |
| **Un spec sin Truth Anchors** | Q3. |

---

## 📚 7. Research Sintetizado

### 7.1 Estado real del repo (medido, con el comando que lo produce)

```powershell
# 8 sets, 304 frame_*.png (298 vivos + 6 en el backup anidado), 34 dirs de animacion
Get-ChildItem Assets\sprites\enemies -Directory | ForEach-Object { $_.Name }
Get-ChildItem Assets\sprites\enemies -Recurse -Filter 'frame_*.png' | Measure-Object

# el desglose: que hay dentro de mine_asteroid
Get-ChildItem Assets\sprites\enemies\mine_asteroid -Recurse -Filter '*.png' | ForEach-Object { $_.FullName }

# los 7 estados del auditor
Select-String -Path tools\sprite_pipeline\audit.py -Pattern 'STATES = \(' -Context 0,10

# el orden de dibujo hardcodeado de HOY
Select-String -Path src\ui\gameplay_runtime.py -Pattern '^\s*self\._draw_'

# la linea base de la suite
python -m pytest tests\ --tb=no
```

### 7.2 Lo que BLOQUE 74 ya resolvió y no hay que rehacer

- El **formato del manifest** y sus 7 campos de clip y 10 de part: `docs/superpowers/specs/2026-10-26-sprite-pipeline-design.md` §2.2.
- Los **7 estados** con su definición exacta: el mismo spec §2.4.
- Las **primitivas de medición**: `src/anim/measure.py`.
- El **formato del `anchors.toml`** y su procedencia por feature: el spec §2.3.
- El **modelo de `Part` y los 4 tipos de draw**: `src/anim/parts.py`.
- El **CLI del pipeline**: `python tools/sprite_pipeline/run.py <set> [--fix] [--json]`.

### 7.3 Las lecciones que más caro salen, si el spec las ignora

| # | Lección | Costo real |
|---|---|---|
| L1 | **Un inline table multilínea no es TOML 1.0.** `tomllib` (Python 3.11) lo rechaza. | El manifest no parseaba. |
| L2 | **Una tupla `(0, 0)` es truthy.** Un default `head_band = (0, 0)` producía una ventana de escaneo **vacía** en vez de "todo el frame". | El probe no detectaba nada: 0 de 60 frames. |
| L3 | **La mediana es `statistics.median`**, no el elemento central superior de la lista ordenada. | El umbral se decidía contra otra mediana: desvíos distintos por hasta 0.2 px. |
| L4 | **El hash de un archivo no es estable entre checkouts** con `core.autocrlf=true` y sin `.gitattributes`. | El test de frescura se ponía rojo en la mitad de los checkouts, sin cambio de arte. |
| L5 | **Un `except` demasiado estrecho deja que un `TOMLDecodeError` escape** y rompa el game loop. | Un manifest mal editado mataba el juego en vez de degradar. |
| L6 | **El gate de mypy cubre `src/`, no `tools/`.** Un `from src.ui.scenes import ...` arrastra 145 errores pre-existentes al gate de `src/anim/`. | El módulo nuevo no podía pasar el gate que el proyecto sí exige. |
| L7 | **Un test que corre la herramienta contra el árbol real** puede reescribir artefactos commiteados a mitad de suite. | `anchors.toml` se regeneraba durante el test. |

### 7.4 Referencia de API actual (firma, no implementación)

```python
# src/anim/manifest.py
def load_set(name: str, root: Path = SETS_ROOT) -> AnimSet: ...

# src/anim/clip.py
class ClipPlayer:
    def __init__(self, anim_set: AnimSet, anchors: AnchorSet) -> None: ...
    def state(self, clip_id: str, elapsed: float) -> ClipState: ...
    def surface(self, clip_id: str, frame: int) -> pygame.Surface | None: ...
    def draw(self, target, clip_id, frame, origin, part_ids=None) -> None: ...

# src/anim/parts.py
def draw_part(target, part, surf, anchor, origin, canvas) -> None: ...
def shield_ellipse_rect(part, anchor, origin, canvas) -> pygame.Rect | None: ...

# tools/sprite_pipeline/audit.py
def audit_set(anim_set) -> tuple[list[Finding], list[FrameMeasurement]]: ...
def render_anchors_toml(anim_set, measurements) -> str: ...
```

---

## 🛡️ 8. Validación Integral

### 8.1 Checklist del spec (el agente la completa en el documento)

- [ ] Las 2 fases y el gate están definidos con criterios verificables.
- [ ] Los 8 sets de enemigo están covered, con su canvas medido.
- [ ] `mine_asteroid` (5 clips desiguales + un dir vacío) tiene una decisión.
- [ ] Cada set tiene su `fps`, `loop` y tolerancias **con su justificación de margen**.
- [ ] Los 7 estados del auditor están mapeados al caso enemigo.
- [ ] El descubrimiento de sets en el CLI está decidido.
- [ ] La abstracción `Layer`, `LayerStack` y `DrawContext` están delimitadas.
- [ ] La frontera con `SceneManager` está decidida.
- [ ] La no-regresión visual tiene mecanismo de verificación.
- [ ] Las 7 restricciones R1-R7 están reflejadas.
- [ ] El FMEA tiene al menos 6 modos de falla con mitigación verificable.
- [ ] "Qué NO se hace" está explícito.
- [ ] Cada claim técnico tiene un Truth Anchor.

### 8.2 FMEA — los modos de falla que el spec tiene que cubrir

| # | Modo de falla | Prob. | Impacto | Mitigación | Verificación |
|---|---|---|---|---|---|
| F1 | El canvas del set se confunde con el hitbox de `ENEMY_CONFIGS` | Alta | Alto | El spec separa "canvas del sprite" de "hitbox" y exige medir el canvas | Un assert de que el canvas medido ≥ el hitbox |
| F2 | Se heredan tolerancias de GOLIATH sin medir | Alta | Alto | P5: justificación de margen obligatoria por set | El spec lista el desvío real medido por set |
| F3 | Un set tiene frames que se tocan entre sí (registro roto) y el runtime lo compensa mal | Media | Alto | El body offset lo cancela; el spec lo verifica frame a frame | Un assert de que el offset compensa el registro |
| F4 | Un clip de 1 frame (`mine_asteroid/open`) rompe el avance de la animación | Media | Medio | El spec define el avance con fps y el clamp a `frames-1` | Un test de clip de 1 frame |
| F5 | El LayerStack reordena el frame y el juego se ve distinto | Media | **Crítico** | B2: orden idéntico, verificado por comparación de frames | Comparación pixel a pixel del frame antes/después |
| F6 | El `DrawContext` cambia la escala del juego y todo se ve chiquito o gigante | Media | **Crítico** | Un único origen/escala, verificado con un test de dimensiones | Un assert de que el tamaño interno sigue siendo 320×480 |
| F7 | La migración de assets reescribe bytes del PNG | Baja | **Crítico** (R1) | El pipeline **no** escribe PNG salvo por el re-pad explícito | `git diff --stat` sobre `Assets/` después de correr el pipeline |
| F8 | El auditor de enemigo reporta FAIL permanentes y bloquea el pipeline | Media | Medio | El spec define el umbral por set antes de correr el auditor | El gate exige 0 FAIL en el set elegido |
| F9 | El `_backup_pre_bloque_65` (6 frames en 2 clips anidados) o los 2 PNG `_new_reference_*.png` se cuelan como set y rompen el descubrimiento | Media | Bajo | El spec decide la exclusión antes de la CLI | Un test de descubrimiento de sets |
| F10 | La Fase 2 crece sin límite y arrastra al juego entero | Media | Alto | El spec delimita qué capas entran | La lista de "fuera de alcance" |

### 8.3 Truth Anchors — cada claim del spec se verifica con uno de estos

```
SUITE BASE        python -m pytest tests\ --tb=no
                     → 2.886 pass + 1 fail pre-existente + 6 skipped (2.893 total)
MYPY GATE         python -m mypy src\anim\
                     → Success: no issues found in 6 source files
SETS              Get-ChildItem Assets\sprites\enemies -Directory | Measure-Object
                     → 8
FRAMES            Get-ChildItem Assets\sprites\enemies -Recurse -Filter 'frame_*.png' | Measure-Object
                     → 304  (298 vivos + 6 en _backup_pre_bloque_65)
ANIM DIRS         Get-ChildItem Assets\sprites\enemies -Directory | Get-ChildItem -Directory | Measure-Object
                     → 34
DRAW ORDER        Select-String -Path src\ui\gameplay_runtime.py -Pattern '^\s*self\._draw_'
                     → los 42 metodos _draw_* del archivo; el bucle del frame
                       (lineas 3973-4165) invoca ~16, en un orden que no puede
                       cambiar
STATES            Select-String -Path tools\sprite_pipeline\audit.py -Pattern 'STATES = \(' -Context 0,10
                     → los 7 estados
GAMESTATES        Select-String -Path src\core\scene_manager.py -Pattern '^\s+[A-Z_]+ = "'
                     → los 15 GameState
CANVAS REAL       el spec lo define; el comando es el que usa audit.py sobre el set
HITBOX            Select-String -Path src\entities\enemies\enemy.py -Pattern '_EnemyConfig\(' -Context 0,3
                     → width/height por enemigo (hitbox, NO canvas)
DETERMINISMO      python tools\sprite_pipeline\audit.py <set> --write-anchors ; (re-run) ; git diff --stat Assets\
                     → sin cambios: el anchors.toml es byte-identico
ARTE INTACTO     git diff --stat Assets\sprites\enemies\
                     → vacío: el pipeline no reescribió los PNG
```

---

**El agente debe devolver el documento completo, no un resumen, y no debe escribir código de implementación.**
