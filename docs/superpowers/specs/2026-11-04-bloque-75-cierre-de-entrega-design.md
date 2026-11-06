# BLOQUE 75 — Cierre de entrega: CI con los gates, changelog y release v1.9.0

**Fecha:** 2026-11-04
**Rama:** `bloquec-67-goliath-port` (la línea de release)
**Alcance:** Track A del cierre. No es una feature: es **publicar y blindar** lo que
la Fase 1 y la Fase 2 ya/are deliveraron.
**Estado del diseño:** aprobado por el usuario (CI en `windows-latest` sobre la línea
de release; versión `v1.9.0`).

---

## 1. El objetivo, en una frase

Que **lo que ya está hecho pase a ser publicable y verificable sin intervención
humana**: la puerta de la fase tiene que correr sola en el CI, el binario que se
descarga tiene que contener el motor de capas, y el changelog tiene que decir qué
cambió.

## 2. Los tres hechos que dan forma al diseño

**H1 — Los goldens son específicos de Windows.** El HUD dibuja el score con
`pygame.font.SysFont("consolas", ...)` (`src/ui/hud.py:111-113`) y **no hay ninguna
fuente empaquetada en el repo**. En un runner Linux la fuente no existe, pygame cae
a la que tenga por defecto y los píxeles del score cambian. Los seis goldens
contienen el HUD (el score `000000` abajo a la derecha se ve en la imagen), así que
**el gate de Fase 2 no puede correr en Linux tal como está**.

**H2 — `master` no tiene las bases de las fases.** Ni `773cf08` (base de la Fase 1)
ni `e619527` (base de la Fase 2) son ancestros de `master` (`git merge-base
--is-ancestor` → 1 en los dos casos). El gate de Fase 1 **hoy fallaría en master**
con "the base commit is not in this repository".

**H3 — El bloque `STATUS:GENERATED` se regenera, no se edita.** El generador real
es `tools/regen_status.py` y es el que dice la propia CLAUDE.md. El generador
produce un formato de la fila de tests que **no coincide** con el que está escrito
a mano ahora mismo (el xfail lleva el sufijo `(fallo conocido)`). La fila hay que
**volver a generarla**, no editarla.

## 3. Diseño

### 3.1 CI — el job `gates`

Un job nuevo en `.github/workflows/test.yml`, aparte del job `pytest` que ya
existe y **no se toca**:

```yaml
  gates:
    # The golden frames carry the HUD, and the HUD draws the score with
    # SysFont("consolas") -- a SYSTEM font, not a bundled one. On a Linux
    # runner the font is missing, pygame falls back to its default and the
    # score pixels change: the Phase 2 gate would be RED on every run for a
    # reason that has nothing to do with the code. So the gates run where
    # the goldens were captured.
    runs-on: windows-latest
    timeout-minutes: 25
```

**Por qué `25` y no `15`:** el presupuesto peor caso del gate de Fase 2 es
**1380 s** (tres llamadas git de 60 s + cuatro presupuestos de 300 s: el pytest
golden, el `--check` del arnés, mypy y el pytest del orden). El job de `pytest` mata
a los 900 s. Con 25 min el gate reporta **su propio diagnóstico** ("G13: the enemy
guards are red: timed out after 300s") en vez de morir sin explicación. La corrida
sana dura ~16 s.

**Qué corre:**

| paso | en qué ramas |
|---|---|
| `gate.py --phase 1` | solo si `773cf08` es ancestro de HEAD |
| `gate.py --phase 2` | solo si `e619527` es ancestro de HEAD |

La condición se evalúa **en el workflow**, con un `git merge-base --is-ancestor` que
sale con un mensaje explicando el salto. El gate **no cambia**: sigue siendo
estricto y falla si su base no está. Lo que decide es el workflow, y lo dice.

**Por qué solo en la línea de release:** por H2. En `master` las dos bases no
están, así que los dos gates se saltarían con un motivo. La Fase 1 y la Fase 2 no
existen en `master` — es la línea vieja.

**El job `pytest` de Linux queda intacto.** La suite completa (3.108 tests) y los
guards ya corren allí, y los guards son platform-independent. Windows solo corre
los gates.

**Cómo se valida antes de tocar la línea de release:** el workflow ya tiene
`workflow_dispatch` ("valida cualquier rama bajo demanda"). El cambio se sube
primero a una rama de prueba (`bloquec-75-ci-gates`), se despacha el workflow
contra esa rama, y **solo si el job `gates` sale verde** se mergea a
`bloquec-67-goliath-port`. Nunca se descubre un CI rojo en la línea de release.

### 3.2 El binario y el release v1.9.0

**El número:** `v1.9.0`. Es una release de feature: la Fase 1 (el pipeline de
sprites) y la Fase 2 (el motor de capas) entran juntas. El precedente es v1.8.0
("BLOQUE 74 — el pipeline de sprites").

**El generador primero.** `tools/regen_status.py` es el dueño del bloque:

- `VERSION = "v1.9.0"`, `BINARY_REL = "dist/void-hunter-v1.9.0.exe"`.
- **`_frozen_assets_verified` se extiende de 2 archivos a 18.** Hoy verifica solo
  el `manifest.toml` y el `anchors.toml` de GOLIATH. **Después de la Fase 2 los
  manifests de los 8 enemigos son load-bearing en runtime**: el runtime los lee
  cada frame para dibujar los enemigos. Si el bundle no los trae, el enemigo cae al
  fallback en silencio. La función pasa a verificar los **9 sets × 2 archivos**.
- El texto de la fila "Build .exe" menciona los 9 sets, no solo GOLIATH.

**El build:** `pyinstaller build.spec` (onefile, `name="void-hunter"`) →
`dist/void-hunter.exe` → copia a `dist/void-hunter-v1.9.0.exe`.

**El bundle ya los lleva:** `build.spec:44` mete `Assets/sprites` entero, así que
los 18 `.toml` entran. Pero **nada lo pinaba**: `tests/test_build_spec_assets.py`
solo cubre la exclusión de los WAV. Se **extiende ese mismo archivo** con un test
que fije el contrato —"el `datas` cubre el árbol donde viven los 9 manifests
(`Assets/sprites`), y los 9 `manifest.toml` + los 9 `anchors.toml` existen en
disco"—, para que un cambio futuro del `datas` no los deje fuera en silencio. El
test no necesita el `.exe`: fija el contrato del spec, no el contenido del bundle.

**El zip y el release:**

```powershell
git tag -a v1.9.0 -m "BLOQUE 75: el pipeline de sprites y el motor de capas del frame"
gh release create v1.9.0 VoidHunter-v1.9.0-win64.zip --latest `
  --title "VOID HUNTER v1.9.0 (BLOQUE 75) - el pipeline de sprites y el motor de capas del frame" `
  --notes-file release-notes-v1.9.0.md
```

El `--notes-file` es un archivo con la entrada del changelog de la release (sin
títulos de markdown, que `gh` no los renderiza): un párrafo de qué es, otro de
qué cambia para quien juega (nada visual) y otro de cómo se verifica.

El precedente exacto de v1.8.1: un asset `VoidHunter-v1.8.1-win64.zip` de 229 MB,
tag anotado, `--latest`.

**El orden importa:** el build va **después** del bump de `VERSION`, porque el
generador lee el `.exe` por `BINARY_REL` y escribe su hash en el bloque. Un build
previo dejaría el bloque apuntando a un archivo que no existe.

### 3.3 Los documentos

| documento | qué | quién lo escribe |
|---|---|---|
| `docs/changelog/CHANGELOG_v1.x.md` | una entrada de BLOQUE 75 que cubre Fase 1 + Fase 2, con la **plantilla de la entrada existente** (`## BLOQUE 75 — El cache del lowpass sobrevive, el binario baja a 220 MB, y el repo tiene presupuesto (2026-11-02)`, línea 2396): mismas secciones, mismo tono | este trabajo |
| `docs/handoffs/HANDOFF-BLOQUE-75-RELEASE-2026-11-04.md` | el cierre corto de la release: qué se publicó, cómo se verifica, qué NO se hizo | este trabajo |
| `CLAUDE.md` (bloque STATUS) | **regenerado** con `python tools/regen_status.py` — no editado a mano (H3) | el generador |
| `.synapse` | el puntero a la release y el estado del repo | este trabajo |
| `tools/capture/probe_layer_stack.py` | **NO**: el probe es un comando del juego (`main.py --check-pipeline`), porque tiene que correr DENTRO del `.exe` (ver §4) | — |

**El changelog es la parte delicate**: la entrada tiene que decir **qué cambia
para quien juega** (nada visual) y **qué cambia para quien desarrolla** (todo el
render pasa por el stack, los enemies son datos). Una entrada de changelog que sólo
canta créditos internos no sirve.

### 3.4 La limpieza

- Borrar el worktree `.worktrees/bloquec-75-phase2-layers` y la rama
  `bloquec-75-phase2-layers` (ya mergeada; sus 42 artefactos del SDD están
  copiados en la línea de release).
- El `git worktree prune` después.

## 4. Cómo se verifica cada paso

| paso | verificación |
|---|---|
| El job `gates` está bien | `workflow_dispatch` sobre `bloquec-75-ci-gates` → el job sale verde. **Antes** de mergear a la línea de release. |
| El gate sirve en CI | el log del job dice `PHASE 1 GATE OK` y `PHASE 2 GATE OK` |
| Los gates se saltan donde no aplican | `workflow_dispatch` sobre una rama sin las bases → el log dice el motivo del salto |
| El bundle lleva los 9 sets | `tools/regen_status.py` lo verifica leyendo el `.exe` con `CArchiveReader`; la fila del bloque lo dice |
| El `.exe` es el nuevo | `Get-Item dist/void-hunter-v1.9.0.exe` + SHA256 en el bloque |
| El juego arranca con el motor | `main.py --check` → `VOID HUNTER check OK`; y **el probe de capas** (ver abajo) → **30 capas por frame** en el `.exe` real, no solo en el source |
| La suite sigue verde | `python -m pytest tests\ --tb=no` → 0 fallos |
| El CI no se rompió | el job `pytest` de Linux sigue verde en el mismo push |

**El probe es un comando del juego**, `main.py --check-pipeline`: reporta si los
ocho sets de enemigos cargan (con su pivote y su escala) y si la tabla de 30
capas tiene los métodos que el runtime ofrece. **Tiene que vivir en el juego
porque un script aparte no puede observar al `.exe`**: el espía vive en el
proceso padre y el binario congelado corre en otro. La pregunta que hay que
responder es *"¿este build puede dibujar los enemigos por el compositor?"*, y
la única forma de responderla **dentro** del binario es que el binario lo
reporte.

**Un detalle que el comando tiene que resolver:** el juego normal **no llega al
gameplay en headless** — el menú post-cinematica (BLOQUE 73.7) espera input. Un
smoke que no salte al boss (`--boss goliath`) reporta cero frames y parece que
el motor no funciona.

**El comando tiene que correr contra el `.exe`**, no contra el source: es la
única prueba de que el bundle frozen encuentra los manifests y dibuja los enemigos
por el compositor. Si el `.exe` no los tiene, el juego no se rompe — dibuja los
enemigos por el camino viejo — y eso no se ve en ningún test.

## 5. Los riesgos, y qué se hace con cada uno

| riesgo | qué pasa | qué hacemos |
|---|---|---|
| El job `gates` sale rojo en `windows-latest` por algo de Windows (permisos, `tar`, rutas) | el CI de la línea de release queda rojo | se valida con `workflow_dispatch` sobre una rama de prueba **antes** de mergear |
| El `.exe` tarda mucho en construirse | la sesión se alarga | el build corre en segundo plano y se mide; si tarda más de lo razonable, se corta y se reporta |
| `gh release create` falla a mitad (tag creado, asset no subido) | queda un tag sin release | se verifica el estado con `gh release view` antes de borrar el zip; el tag se puede borrar y rehacer si es un tag local sin publicar |
| El `.exe` no encuentra los manifests en el bundle | **el juego degrada en silencio**: los enemigos se dibujan por el camino viejo, sin error visible | la fila del bloque lo verifica leyendo el bundle, y el probe de capas corre contra el `.exe` |
| El changelog miente | el repo documenta mal lo que cambió | la entrada se escribe DESPUÉS de medir el binario y el SHA, con los números reales |

## 6. Lo que este trabajo NO hace

- **No cambia un pixel del juego.** No se toca el HUD, ni la fuente, ni los goldens.
  La fuente se queda como está; por eso los gates corren en Windows.
- **No toca `master`.** La línea vieja queda como está.
- **No merges la Fase 3.** El motor por capas crece después, en su propio BLOQUE.
- **No rebuilda el `.exe` para cada fase.** Esta es la release que publica la Fase 2.

## 7. El orden

1. **CI**: el workflow, el test que pinan los manifests en el bundle, y el `regen_status.py` extendido. Se sube a `bloquec-75-ci-gates` y se valida con `workflow_dispatch`.
2. **Merge del CI** a la línea de release (solo si el job salió verde).
3. **Bump + build**: `VERSION`/`BINARY_REL`, `pyinstaller`, el `.exe` nuevo, el zip.
4. **Verificación del `.exe`**: el bloque regenerado (con el hash y los 9 sets), el probe de capas contra el binario, `main.py --check`.
5. **Changelog + handoff + `.synapse`**.
6. **Tag + `gh release create --latest`**.
7. **Limpieza**: worktree y rama de la Fase 2.

Si algo falla, se para en ese punto y se reporta: los pasos siguientes dependen del
anterior.
