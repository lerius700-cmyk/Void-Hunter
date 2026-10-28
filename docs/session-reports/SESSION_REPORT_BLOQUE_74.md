# SESSION REPORT — BLOQUE 74 (2026-10-27)

> Rama: `bloquec-74-sprite-pipeline` · Worktree: `.worktrees/bloquec-74-sprite-pipeline`
> Base: la línea v1.7.2 (BLOQUE 67) · **No bumpea la versión** · **No se reconstruyó el `.exe`**
> `master` (**v1.6.3**, `a40fdaf`) quedó **limpio y sin tocar**: no se mergeó, no se pusheó,
> no se creó ningún tag.

---

## 1. Qué se hizo

BLOQUE 74 saca la medición del arte del runtime y la pone en build time.

**El subsistema nuevo** — `src/anim/` (6 archivos): `manifest.py` (manifiesto
declarativo + validación), `measure.py` (medición por píxel), `parts.py`
(reglas de detección), `anchors.py` (lector de la tabla horneada), `clip.py`
(compositor: manifiesto + anclas + caché de frames), `__init__.py`.

**El tool nuevo** — `tools/sprite_pipeline/`: `audit.py` (7 estados),
`repair.py` (reparaciones deterministas e idempotentes), `run.py`
(validate → audit → repair → re-audit → anchors → report).

**Los dos archivos del set**:
`Assets/sprites/bosses/goliath/manifest.toml` (la spec, editada a mano) y
`anchors.toml` (la medición de los 60 frames, generada).

**El runtime** dejó de escanear píxeles: el ojo, la placa del escudo y el
centroide son lookups en la tabla horneada (`src/ui/scenes.py`).

---

## 2. Tres cosas que nadie iba a ver, y se arreglaron

### 2.1 Dos umbrales distintos para el mismo problema

El auditor marcaba `CORTADO` cuando el margen de la silueta era **menor de 2
px**, y el re-pad perseguía un margen de **3 px**. Los dos números vivían en
archivos distintos y nadie los comparó.

La consecuencia era un **wedge**: un frame con 4 px de margen total (marcado
por el auditor) no puede alcanzar el objetivo del re-pad, porque no le queda
margen para los dos lados. Ese frame quedaba marcado **para siempre** y
`run.py --fix` salía 1 sobre un set que ya no se podía arreglar.

Ahora los dos lados usan `CORTADO_MARGIN` (`src/anim/measure.py`), un solo
constante. El test que lo cubre arma un frame con márgenes (0, 1) — el más
apretado que una traslación todavía puede arreglar — y verifica el ciclo
completo: el auditor lo marca, el re-pad lo mueve, y el auditor **ya no** lo
marca.

### 2.2 El test del sprite se saltaba a sí mismo

`tests/test_goliath_sprite.py` y `tools/capture/capture_goliath_phase1.py`
apuntaban al clip `"idle"`. **GOLIATH no tiene un clip `"idle"`**: los clips
son `phase1_idle`, `phase2_idle`, `javelin`, `laser`, `purple_bullet` y
`death`. El directorio no existía, así que el test se saltaba (con un
`pytest.skip`) en vez de probar nada, y la captura generaba una frame sin
boss.

Es un bug **pre-existente** (ya estaba antes de este BLOQUE), pero el branch
era el momento correcto: ahora apuntan a `phase1_idle` y el test corre de
verdad.

### 2.3 Un test que podía reescribir el arte commiteado

`tests/test_sprite_pipeline_run.py` corría `run.py --fix` contra el **árbol
real**: el comando reescribe `anchors.toml` y puede **espejar los frames
publicados**. Si una aserción fallaba en el medio, la suite dejaba el
repositorio con el arte modificado.

Ahora el test corre contra una **copia** del set en `tmp_path` (por eso el
tool acepta `--root`), y hay un test que verifica que los anchors
**publicados** siguen intactos después del run.

---

## 3. Reglas que quedan escritas (para la próxima sesión)

1. **`anchors.toml` es generado.** NUNCA se edita a mano: se regenera con
   `python tools/sprite_pipeline/run.py <set> --fix`.
2. **`manifest.toml` es la spec** y se edita a mano. Antes de mover una
   tolerancia, medir contra los frames reales (los valores actuales están
   medidos sobre los 60 frames de GOLIATH).
3. **`src/anim/` no importa `tools/`; `tools/sprite_pipeline/` sí importa
   `src/anim/`.** Si falta una función de medición, va a
   `src/anim/measure.py`.
4. **Un solo umbral para el re-pad**: `CORTADO_MARGIN`. No hay dos números
   para la misma regla.
5. **El canvas no es una constante del juego**: es `meta.canvas` del
   manifiesto. Igual el directorio del clip: es `clip.dir`, no el `clip.id`.
6. **El `.exe` no se reconstruyó** y **la versión no se bumpea**. La release
   es de otra ola.

---

## 4. Números

| Métrica | Valor | Fuente |
|----------|-------|--------|
| LOC `src/` | 28,929 | `python -c "import pathlib; print(sum(len(p.read_text(encoding='utf-8',errors='ignore').splitlines()) for p in pathlib.Path('src').rglob('*.py')))"` |
| Archivos Python en `src/` | 92 | `Get-ChildItem -Recurse -Filter *.py src/ \| Measure-Object` |
| LOC `tests/` | 25,340 | mismo comando sobre `tests/` |
| Suite | **2.880 pass + 1 fail pre-existente + 6 skipped (2.887 total)** | `python -m pytest tests/ --tb=no` |
| mypy `src/anim/` | **0 errores** | `python -m mypy src/anim/` |
| Auditoría del set | **10/60 frames con findings (0 FAIL, 10 WARN)** | `python tools/sprite_pipeline/audit.py goliath` |
| Pipeline `--fix` | no repara nada, exit 0, árbol limpio | `python tools/sprite_pipeline/run.py goliath --fix` |
| Compliance SF+SM | **7/7** (Lite) | `audit_sf_sm.py --perfil=lite` |

El único test que falla es
`tests/test_paths.py::test_paths_no_star_shapes` — **pre-existente**, una
aserción real de geometría del LissajousPath. Los 8 tests que fallaban en la
línea v1.7.2 eran contaminación de estado entre tests y ya no fallan.

---

## 5. Verificación

```powershell
python -m pytest tests/ --tb=no
# → 1 failed, 2880 passed, 6 skipped in 55.80s
#   FAILED tests/test_paths.py::test_paths_no_star_shapes (pre-existente)

python -m mypy src/anim/
# → Success: no issues found in 6 source files

python tools/sprite_pipeline/audit.py goliath
# → summary: 10/60 frames with findings (0 FAIL, 10 WARN)   exit 0

python tools/sprite_pipeline/run.py goliath --fix
# → GOLIATH: 10/60 frames with findings (0 FAIL, 10 WARN), 10 findings   exit 0
# → git status --short: sin cambios en el árbol

python main.py --check
# → 15 scenes, 18 waves, 4 bosses

python main.py --boss goliath --easy --duration 60
# → 60 s de pelea, exit 0
```

---

## 6. Dónde quedó

| Qué | Dónde |
|-----|-------|
| Spec | `docs/superpowers/specs/2026-10-26-sprite-pipeline-design.md` |
| Plan | `docs/superpowers/plans/2026-10-26-sprite-pipeline.md` |
| Handoff | `docs/handoffs/HANDOFF-SPRITE-PIPELINE-2026-10-27.md` |
| Changelog | `docs/changelog/CHANGELOG_v1.x.md` (sección BLOQUE 74) |
| Ledger del BLOQUE | `.superpowers/sdd/2026-10-26-sprite-pipeline/progress.md` |
| Reporte de la ola final | `.superpowers/sdd/2026-10-26-sprite-pipeline/final-fix-report.md` |
| Subsistema runtime | `src/anim/` |
| Tool | `tools/sprite_pipeline/` |
| Spec del set | `Assets/sprites/bosses/goliath/manifest.toml` |
| Anclas horneadas | `Assets/sprites/bosses/goliath/anchors.toml` |

**Pendiente para otra ola:** rebuild del `.exe` (con el manifiesto y las
anclas adentro) y la release con bump de versión. Nada de eso se hizo acá.
