# BLOQUE 75 — El pipeline de sprites y el motor de capas del frame

**Status:** ✅ Fase 1 y Fase 2 COMPLETAS y mergeadas en la línea de release.
**Started:** 2026-10-29
**Fase 1 merged:** 2026-11-02 (`070ad76`, sobre `bloquec-67-goliath-port`)
**Fase 2 merged:** 2026-11-04 (`ca813a5` + `5f58679`, 37 commits)
**Released as:** **sin bump de versión** — el `.exe` publicado sigue siendo v1.8.1 y **NO contiene la Fase 2**
**BLOQUE ID:** 75 (Fase 1: pipeline de enemigos · Fase 2: motor de capas)
**Scope:** dos fases, 10 tareas + 6 rondas de fix, 9 reviews por tarea + 1 review final
**User directives:**
- La motor gráfico por capas se decidió con **brainstorming**: `src/render/` separado, `SceneManager` intacto, dos checkpoints (2A stack / 2B pipeline).
- La ejecución con **subagent-driven-development**: implementadores y revisores separados, **reviews en paralelo** cuando se puede, un implementador a la vez.
- El pipeline de sprites debe ser **reproducible**: el runtime usa `random` global en 31 lugares y solo siembra `_asteroid_rng`.
- **R1: ni un byte del arte cambia.**

---

## Fase 1 — Los 8 sets de enemigos al pipeline (merged `070ad76`) — ✅ DONE

- [x] `src/anim/` (6 archivos): `manifest.py`, `measure.py`, `parts.py`, `anchors.py`, `clip.py`, `__init__.py`
- [x] `tools/sprite_pipeline/`: `audit.py` (7 estados), `repair.py`, `run.py`, `verify_contract.py`, `sets.py`, `gate.py`
- [x] Los 8 manifests de enemigos + los 9 `anchors.toml` (GOLIATH + 8)
- [x] 3 campos nuevos en el manifest (`distinct`, `cut_margin`, `clip.canvas`) + `part_or_none()` + `effective_cut_margin()`
- [x] Gate de Fase 1 (G1..G13) con `PHASE_1_BASE` y `--base`
- [x] 11 archivos de guardas
- [x] 9 revisiones · 15 defectos · **todos míos** (el código de los implementadores no dio ni uno)
- [x] Verificado en el árbol mergeado: suite sin fallos, `PHASE 1 GATE OK`, R1/R2 con diff vacío, 1.768 PNGs con digest idéntico

## Fase 2 — El motor de capas del frame (merged `ca813a5`) — ✅ DONE

### Las 10 tareas

- [x] **T1 — Arnés de golden frames** (`c3643f6`, `9660188`, `9807e41`, `673e8de`): captura reproducible + 6 goldens
- [x] **T2 — El motor** (`39f5113`, `7e10964`): `src/render/` con `Layer`, `LayerStack`, `DrawContext`
- [x] **T3 — Las 30 capas** (`c61a969`, `6a5b2fb`): extracción *verbatim* a wrappers `*_pass`
- [x] **T4 — Checkpoint 2A** (`4c2e5c5`): el frame se compone con el `LayerStack`, **0 píxeles movidos**
- [x] **T5 — Pivote `fixed`** (`82c85c9`, `9d9742d`): el pivote centrado lo declara el manifest
- [x] **T6 — Escala 1.05** (`d693af6`): el compositor escala la parte
- [x] **T7 — Los manifests declaran la escala** (`3fd4384`): `scale = [1.05, 1.05]` + los anchors regenerados
- [x] **T8 — Checkpoint 2B** (`85baeb8`, `19a5fad`, `30a8e41`, `f1ea331`): los enemigos por el pipeline, **0 píxeles movidos**
- [x] **T9 — `mode`/`on_end` con vocabulario** (`099f864`, `e6e19c7`): exigido, y las CLI resuelven por `sets.py`
- [x] **T10 — El gate de Fase 2** (`42a01ff`): `gate.py --phase 2` → `PHASE 2 GATE OK`

### Las 6 rondas de fix

- [x] `42d252e` — el range de G5 excluye la medición **generada** de GOLIATH
- [x] `9d9742d` — el pivote `fixed` pineado por la **ruta pública**
- [x] `30a8e41` — el flash dibuja el **cuerpo** cuando el pipeline no pudo dibujarlo
- [x] `f1ea331` — la raíz de los enemigos se resuelve **una vez**, no por enemigo y frame (114 µs → 17 µs)
- [x] `e6e19c7` — los probes de la Fase 1 learn el vocabulario y el fixture aísla el set enviado
- [x] `2a947fb` — el guard del hot path ve **cualquier** trabajo de disco, no solo una llamada
- [x] `673e8de` — el guard del bare-capture discrimina con el mtime y **falla contra el harness previo**

### Verificado por el controlador, en el árbol mergeado

- [x] Suite: **3.101 pass + 0 fail** (+6 skipped + 1 xfailed = 3.108)
- [x] `PHASE 1 GATE OK` y `PHASE 2 GATE OK` (exit 0)
- [x] `verify_contract.py goliath` → `CONTRACT OK`
- [x] **R1**: 0 PNGs modificados o borrados; digest **idéntico** de los 1.768 PNGs de `Assets/` (los 6 PNGs agregados son los goldens)
- [x] `mypy src\anim\ src\render\` → 0 errores en 8 archivos
- [x] `main.py --check` → `VOID HUNTER check OK`; `--boss goliath --duration 12` → exit 0
- [x] `sf-sm-doctor --perfil=lite` → **SF COMPLIANCE 7/7**, exit 0
- [x] Merge **sin conflictos**, árbol mergeado byte-idéntico a la punta de la rama
- [x] El build de PyInstaller empaqueta los **18 `.toml`** y una simulación de `_MEIPASS` carga los 8 sets
- [x] `src/render/` importa 0 módulos del juego; `src/core/` sin tocar

---

## Lo que falta por hacer

### P1 — Bloquea la entrega del artefacto

- [ ] **Cablear los DOS gates en el CI de la línea de release.** `.github/workflows/test.yml` corre
      **solo** `pytest`, y solo en `master` y `bloquec-67-goliath-port`. Hay que añadir
      `gate.py --phase 1` y `gate.py --phase 2`.
- [ ] **Subir el `timeout-minutes` del job de 15 a 25.** El presupuesto peor caso del gate de
      Fase 2 es **1380 s** (3 llamadas git de 60 s + 4 presupuestos de 300 s) y el job mata la
      tarea a los **900 s** — sin diagnóstico. El gate de Fase 1 se dimensionó a propósito para
      caber (840 s) y nadie rehizo la aritmetica para la Fase 2.
- [ ] **Reconstruir el `.exe`.** El binario publicado es v1.8.1 (2 nov) y **no contiene la Fase 2**:
      los enemigos siguen dibujándose por el camino viejo. Si querés el artefacto con el motor
      de capas, hay que bumpear versión, reconstruir y publicar.
- [ ] **Entrada de changelog para BLOQUE 75** (Fase 1 + Fase 2). El changelog termina en
      BLOQUE 74.

### P2 — Limpieza

- [ ] **Borrar el worktree y la rama de la Fase 2** (`.worktrees/bloquec-75-phase2-layers`,
      `bloquec-75-phase2-layers`): ya está mergeada. Los 42 artefactos del SDD están copiados a
      la línea de release.
- [ ] **`PHASE_1_BASE = "773cf08"`** es una constante dura. Sirve hoy, pero es lo que hay que
      mover cuando empiece una tercera fase.

### P3 — Limitaciones conocidas (documentadas, pueden salir así)

- [ ] El clip `death` de la mina (10 frames) **nunca se juega** — ni el runtime ni el pipeline.
      Quiere una decisión, no un arreglo.
- [ ] `EnemyKind.CARRIER` **no tiene set**: paga una búsqueda desperdiciada por frame (0,24 µs).
- [ ] `Assets/sprites/enemy_<kind>.png` **ya no existen** → la rama legacy de `_get_enemy_sprite`
      es código muerto.
- [ ] `loaded_set` (degrada a `None`) vs `load_set` (levanta) **no está escrito** en el contrato
      público de `clip.py`: un cambio futuro que los intercambie convertiría un manifest faltante
      en un crash dentro de un draw.
- [ ] El camino de dibujo de enemigos quedó **~2,3× más caro** que antes de la fase
      (5,99 → 13,96 µs por enemigo y frame). Aceptable; ningún test lo pinea a propósito.
- [ ] `build.spec` empaqueta `Assets/sprites` **dos veces** (línea 44 entera y línea 65) → ~200
      entradas duplicadas.

### P4 — Decisiones de la Fase 3 (no son tareas, son preguntas)

- [ ] ¿El motor por capas sigue creciendo en `src/render/`, o la Fase 3 abre los capas del HUD?
- [ ] ¿La mina gana el clip `death` (y se dibuja), o se declara muerto y se borra el arte?
- [ ] ¿El `.exe` se reconstruye en cada fase, o solo cuando hay un bump de versión?

---

## Las cinco garantías de la Fase 2, y cómo se prueban

| # | Garantía | El test que la exige | La mutación que la pone en rojo |
|---|---|---|---|
| a | Los 6 goldens son pixel-exactos | `test_layer_stack_renders_identical_frames.py` (6 casos) | mover el origen del enemigo +1 px → 5 de 6 en rojo |
| b | Los enemigos pasan por el compositor | 3 spies en el mismo archivo | `_draw_enemy_body_via_pipeline` devuelve `None` → 3 spies en rojo **y los 6 goldens siguen verdes** |
| c | El pivote `fixed` por la ruta pública | `test_fixed_pivot.py::test_the_public_path_draws_a_fixed_part_centred` | `draw_part` con la aritmética pre-Task-5 → solo el test público en rojo |
| d | El flash dibuja el cuerpo | `test_flash_fallback_draws_the_body.py` (3 casos) | el blit de fallback inalcanzable → 2 en rojo |
| e | El hot path no hace disco por frame | `test_enemies_root_is_resolved_once.py` | reparsear el manifest por enemigo y frame → el guard nuevo en rojo |

> **La regla de la fase:** *una garantía que el check no puede ver no es una garantía, es una
> hipótesis*. Cada una de las cinco tiene su mutación nombrada, y cada mutación se ejecutó y se
> pegó su rojo en el reporte.

---

## Documentos

| Documento | Qué es |
|---|---|
| `docs/handoffs/HANDOFF-BLOQUE-75-PHASE2-2026-11-04.md` | El cierre de la Fase 2: qué es, qué cambió, cómo verificar, y lo que NO se hizo |
| `docs/superpowers/plans/2026-11-03-bloque-75-phase2-layers.md` | El plan de 10 tareas **con el log de correcciones** (33 defectos: de los briefs, de la implementación y de las reviews) |
| `docs/superpowers/specs/2026-11-03-bloque-75-phase2-layers-design.md` | El diseño del motor por capas |
| `docs/superpowers/specs/2026-10-30-bloque-75-migration-spec.md` | El spec de la migración (Fase 1 + Fase 2) |
| `docs/handoffs/HANDOFF-BLOQUE-75-2026-11-02.md` | El cierre de la Fase 1 y del cache del lowpass |
