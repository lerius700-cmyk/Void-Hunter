# HANDOFF — BLOQUE 74: pipeline de sprites (el runtime deja de medir el arte)

> Fecha: 2026-10-27
> Rama: `bloquec-74-sprite-pipeline` · Worktree: `.worktrees/bloquec-74-sprite-pipeline`
> Base: la línea v1.7.2 (BLOQUE 67) · **No bumpea la versión** (sigue v1.7.2)
> `master` es **otra línea** (v1.6.3) y **no** fue mergeada ni tocada.

Este documento es autocontenido: un agente sin contexto previo debería poder
seguir trabajando desde acá.

---

## 1. Qué es el pipeline (y por qué existe)

Antes de BLOQUE 74, el **runtime medía el arte**: la primera vez que veía un
frame de GOLIATH escaneaba sus píxeles para encontrar el **ojo** y la **placa
del escudo** (3.9 ms por frame × 60 frames). Eso es trabajo de **build time**,
no de runtime: el juego arrancaba midiendo, y el resultado cambiaba según el
frame.

BLOQUE 74 separa las dos cosas y las deja explícitas:

| Archivo | Qué es | Quién lo escribe |
|---------|--------|------------------|
| `Assets/sprites/bosses/goliath/manifest.toml` | La **spec** del set: canvas, anchor, clips (id ↔ dir), fps, tolerancias, reglas de detección | **A mano.** Es la spec del set |
| `Assets/sprites/bosses/goliath/anchors.toml` | La **medición** de los 60 frames (ojo, placa, silueta, origen) | **Generado** por `run.py --fix` |

El juego **solo lee** `anchors.toml`. El `manifest.toml` lo lee el runtime para
los datos declarativos (canvas, fps, cantidad de frames) y el auditor para las
reglas.

### Los dos subsistemas

```
src/anim/                 ← el runtime (L (LOAD))
├── manifest.py           ← carga y valida el manifiesto; resuelve la raíz del repo (perezoso)
├── measure.py            ← medición por píxel: silueta, centroide, elipse creíble
├── parts.py              ← las reglas de detección declaradas
├── anchors.py            ← lector de la tabla horneada (anchors.toml)
└── clip.py               ← compositor: manifiesto + anclas + caché de frames

tools/sprite_pipeline/    ← el tool (R (REFERENCE), dev-only)
├── audit.py              ← clasifica cada frame en uno de 7 estados
├── repair.py             ← reparaciones deterministas e idempotentes
└── run.py                ← validate → audit → repair → re-audit → anchors → report
```

**Regla de capas:** `src/anim/` **no** importa `tools/`. `tools/sprite_pipeline/`
**sí** importa `src/anim/`. Si alguna vez hay que medir algo en runtime, la
función de medición va a `src/anim/measure.py` y el tool la usa — nunca al revés.

---

## 2. Cómo se corre

```powershell
# Auditar (exit 1 si queda algún FAIL; exit 0 si sólo hay WARN)
python tools/sprite_pipeline/audit.py goliath

# Dry run: NO escribe NADA. Audita y reporta.
python tools/sprite_pipeline/run.py goliath

# Reparar, re-auditar y re-hornear anchors.toml (el único comando que escribe)
python tools/sprite_pipeline/run.py goliath --fix

# Trabajar sobre una COPIA del set (lo que hacen los tests)
python tools/sprite_pipeline/audit.py goliath --root <dir>
python tools/sprite_pipeline/run.py   goliath --root <dir> --fix
```

`--json` imprime el reporte en JSON (stdout **puro**: el banner de pygame está
suprimido a propósito).

**Orden importante:** las anclas se escriben **después** de la re-auditoría,
así que siempre llevan la medición **post-reparación**. Un dry run no puede
regresionar el archivo generado.

### Estado actual del set de GOLIATH

```
$ python tools/sprite_pipeline/audit.py goliath
summary: 10/60 frames with findings (0 FAIL, 10 WARN)     → exit 0

$ python tools/sprite_pipeline/run.py goliath --fix
GOLIATH: 10/60 frames with findings (0 FAIL, 10 WARN), 10 findings   → exit 0
```

Los 10 WARN son los **5 clips con frames de placa mal medida**
(`FUERA_DE_RANGO`) y los **2 frames con detectores en desacuerdo**
(`FIRMA_AMBIGUA`). No se reparan: la placa se resuelve por **interpolación**
desde los frames vecinos (que es lo que el runtime ya hacía) y el pixel art no
se reescala. **0 FAIL** es el gate.

---

## 3. Qué significa cada estado

| Estado | Gate | Qué lo detecta | Qué se hace |
|--------|------|----------------|-------------|
| `COLAPSADO` | **FAIL** | Dos frames del mismo clip comparten MD5: la animación es una imagen fija | No reparable (el arte se fue). Se regenera el frame |
| `CORTADO` | **FAIL** | La silueta está a menos de `CORTADO_MARGIN` (2 px) de un borde del canvas | `repair.py` la **mueve** dentro del canvas (nunca la escala) |
| `LADO_EQUIVOCADO` | **FAIL** | La placa del escudo aparece del lado equivocado: el frame está espejado | `repair.py` lo **espeja** horizontalmente dentro de su canvas |
| `FIRMA_AMBIGUA` | WARN | Los dos detectores independientes (sonda de color y forma) discrepan más que la tolerancia | Se acepta: los dos casos reales son del arte original |
| `AUSENTE` | WARN | La placa no se pudo medir en ese frame | Se **interpola** desde los frames vecinos |
| `FUERA_DE_RANGO` | WARN | La elipse medida no es plausible como escudo (rx/ry fuera del rango declarado) | Se **interpola** desde los frames vecinos |
| `ESCALADO` | WARN | La altura de la silueta se aparta de la mediana del clip | Se **reporta**: el pixel art no se reescala |

`FAIL` bloquea el pipeline (`run.py` sale 1). `WARN` se resuelve o se acepta
**sin tocar el arte**.

### `CORTADO_MARGIN`: UN solo umbral

`src/anim/measure.py` define `CORTADO_MARGIN = 2`. **El auditor marca por debajo
de ese valor y el re-pad persigue exactamente ese valor.** No son dos números
distintos: con dos umbrales, un frame marcado podía no ser reparable nunca
(si no le queda margen para dos lados) y `run.py --fix` salía 1 para siempre
sobre un set irreparable. Si se toca el umbral, se toca **el constante**, no
uno de los dos lados.

---

## 4. Truth anchors

Un truth anchor es un hecho que se puede volver a medir. Los de este BLOQUE:

| Ancla | Cómo se verifica | Dónde vive |
|-------|-------------------|------------|
| El **manifiesto** declara el canvas, los clips y las reglas | `python -c "from src.anim.manifest import load_set; s=load_set('goliath'); print(s.canvas, s.clips.keys())"` | `Assets/sprites/bosses/goliath/manifest.toml` |
| Las **anclas horneadas** son la medición | `Get-Content Assets/sprites/bosses/goliath/anchors.toml` (60 entradas) | `Assets/sprites/bosses/goliath/anchors.toml` |
| El set **pasa** el gate | `python tools/sprite_pipeline/audit.py goliath` → `0 FAIL` | `tools/sprite_pipeline/audit.py` |
| El pipeline **no repara nada** sobre el arte commiteado | `python tools/sprite_pipeline/run.py goliath --fix` + `git status --short` limpio | `tools/sprite_pipeline/run.py` |
| El **runtime** usa las anclas horneadas | `tests/test_goliath_runtime_uses_baked_anchors.py` | `src/ui/scenes.py` |
| La suite no regresiona | `python -m pytest tests/ --tb=no` | `tests/` |

### Constantes que NO se tocan

- **Escudo de GOLIATH** (BLOQUE 67, valores aprobados por el usuario):
  `GOLIATH_SHIELD_DX = 0`, `GOLIATH_SHIELD_DY = 3`, `GOLIATH_SHIELD_RX = 11`,
  `GOLIATH_SHIELD_RY = 17`, `GOLIATH_SHIELD_R = 11`, `GOLIATH_SHIELD_RX_SCALE = 0.78`.
- **El óvalo del escudo es INVISIBLE**: la geometría se expone, el pintado
  queda detrás de `DRAW_SHIELD_OVAL = False`. Sólo se ven la capa de calor y
  el parpadeo de impacto.
- **El `+1` de inflación del hitbox** del escudo.
- **La capa de calor con forma cuadrada** del escudo cargado.
- **Los umbrales `LADO_EQUIVOCADO` / `FUERA_DE_RANGO`** declarados en el
  manifiesto.
- **`CORTADO_MARGIN`** (2 px) — si cambia, cambia en el constante compartido.

---

## 5. Lo que NO está hecho

Esto es lo más importante de este handoff: **BLOQUE 74 no está terminado de
release**.

1. **El `.exe` NO se reconstruyó.** El `build.spec` sí bundlea `Assets/sprites`
   (con el `manifest.toml` y el `anchors.toml` adentro), pero el binario que
   existe hoy es el de v1.7.2 y vive en
   `.worktrees/bloquec-67-goliath-port/dist/`. **El rebuild es decisión del
   controlador**, no de este BLOQUE.
2. **La versión NO se bumpea.** Sigue siendo v1.7.2. La release va después.
3. **El camino congelado está implementado pero NO ejercitado.**
   `src/anim/manifest.py` resuelve `<_MEIPASS>/Assets/sprites/bosses` y el
   `build.spec` empaqueta el árbol de sprites, pero eso sólo se prueba
   rebuildeando el `.exe` y arrancándolo. **Nadie lo ha hecho todavía.**
4. **La rama no está mergeada.** `master` sigue en `a40fdaf` (v1.6.3), con sus
   8 commits sin pushear, **limpio**. No se hizo merge, no se hizo push, no se
   creó ningún tag.
5. **Diferidos por el review, decididos como *ship-as-is*:** el crash de
   `hud.py` bajo un plugin de fault-injection; la incapacidad del re-pad de
   trasladar una silueta a canvas completo; el wording dry-run vs applied; la
   cobertura de `CORTADO` sólo sintética; la diferencia entre radios canónicos
   y radios mediana; `test_paths_no_star_shapes`; y ruff.

---

## 6. La ola final de fixes (qué se cambió al final)

El review del branch completo devolvió **"Ready to merge: With fixes"** (0
Critical, 3 Important, 8 Minor). Todo está cerrado; el detalle con
`archivo:línea` está en
`.superpowers/sdd/2026-10-26-sprite-pipeline/final-fix-report.md`.

Resumen: umbral `CORTADO_MARGIN` compartido; documentación del BLOQUE ausente
en todos los documentos del proyecto; el clip inexistente `"idle"` corregido a
`phase1_idle` (el test del sprite **se saltaba a sí mismo** por eso);
`_clip_id_for_dir` memoizado; directorio del clip y canvas tomados del
manifiesto; docstring obsoleto de `_goliath_eye_position`; el test del pipeline
corriendo contra una **copia** en `tmp_path` en vez del árbol real; y `ROOT`
del manifiesto perezoso.

---

## 7. Cómo continuar

```powershell
# 1. Estado
cd F:\AI\MM\void-hunter\.worktrees\bloquec-74-sprite-pipeline
git status --short          # debe estar limpio
git log --oneline -5

# 2. Validar
python -m pytest tests/ --tb=no
python -m mypy src/anim/
python tools/sprite_pipeline/audit.py goliath
python tools/sprite_pipeline/run.py goliath --fix
python main.py --check
python main.py --boss goliath --easy --duration 60

# 3. Si hay que tocar el arte de un set:
#    - se edita el PNG a mano (o se regenera) y se corre `run.py <set> --fix`
#    - NUNCA se edita anchors.toml a mano
#    - el manifiesto se edita a mano, pero es la SPEC: antes de cambiar una
#      tolerancia, medir contra los 60 frames reales
```

Los documentos que accompany a este handoff:

- Spec: `docs/superpowers/specs/2026-10-26-sprite-pipeline-design.md`
- Plan: `docs/superpowers/plans/2026-10-26-sprite-pipeline.md`
- Changelog: `docs/changelog/CHANGELOG_v1.x.md` (sección BLOQUE 74)
- Session report: `docs/session-reports/SESSION_REPORT_BLOQUE_74.md`
- Ledger del BLOQUE: `.superpowers/sdd/2026-10-26-sprite-pipeline/progress.md`
  (su sección **"Minors diferidos y su triaje"** es el triage del controlador
  y es **autoritativo**)
