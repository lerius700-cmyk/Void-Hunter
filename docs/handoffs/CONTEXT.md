# Silo: handoffs (Handoffs Cross-Session)

**Propósito:** Cierre formal de un BLOQUE. Un handoff es el documento que
deja una sesión para que otra (humana o de un agente) pueda retomar el
trabajo sin reconstruir el contexto: qué se cambió, qué NO se portó, y
los números reales de la suite.

---

## Contenido del silo

| Archivo | Tipo | Descripción |
|---------|------|-------------|
| `HANDOFF-ASTEROIDES-2026-09-09.md` | Handoff | Cierre del rework de asteroides (BLOQUE 70 → v1.3.0) |
| `HANDOFF-GOLIATH-PORT-V140-2026-10-23.md` | Handoff | Port de GOLIATH + menú post-cinematica a la línea v1.4.0 (BLOQUE 67 → v1.7.2). Incluye los 3 bugs de packaging y el revert del sistema de armas |
| `HANDOFF-SPRITE-PIPELINE-2026-10-27.md` | Handoff | BLOQUE 74: pipeline de sprites (manifiesto + auditor + anclas horneadas). Incluye qué es el pipeline, los 7 estados, los truth anchors y lo que NO está hecho (el `.exe` no se reconstruyó, el camino congelado no se ejercitó) |
| `HANDOFF-BLOQUE-75-2026-11-02.md` | Handoff | BLOQUE 75: el cache del lowpass de pausa que sobrevive a la sesión, el WAV generado fuera del bundle (278 → 220 MB), el presupuesto de disco con test, y el handoff entre agentes con su spec y su plan de Fase 1 |
| `HANDOFF-BLOQUE-75-PHASE2-2026-11-04.md` | Handoff | BLOQUE 75 Fase 2: el motor de capas del frame (`src/render/`, 30 capas, dos checkpoints) y los enemigos dibujados por el compositor del pipeline, con 0 píxeles movidos. Incluye las 5 garantías y cómo se prueban, la regla de los briefs congelados, y el **pendiente de CI**: el gate de Fase 2 no está cableado y el `timeout-minutes` del job es menor que su presupuesto |
| `HANDOFF-BLOQUE-75-RELEASE-2026-11-04.md` | Handoff | BLOQUE 75: la release **v1.9.0** (publicada). Qué se publica (binario, SHA256, CI en verde) y cómo se verifica (los comandos con su salida esperada). **Cierra el pendiente de CI** de la Fase 2: el job `gates` ya corre los dos gates en `windows-latest`. Incluye **qué NO se hizo**: el motor de capas cubre una escena de quince, el clip `death` de la mina nunca se reproduce, `CARRIER` no tiene set, la rama legacy de `_get_enemy_sprite` **no se puede borrar** (es la red de seguridad de la paridad de píxeles), y la salida de build se mide contra un techo de 1200 MB (la cifra vive en la fila `Salida de build (dist/)` del STATUS, que produce `python tools/repo_budget.py`). Incluye los **13 follow-ups** de la revisión final |
| `HANDOFF-BLOQUE-75-GSTACK-REVIEW-2026-11-07.md` | Handoff | La revisión `gstack-review` de la línea de release (diff `d70b8da..61c08d9`): los **3 CRITICAL** que encontró y corrigió (el gate pasaba en verde con un rango vacío; `--boss phantom` anunciaba PHANTOM y spawneaba NEMESIS; `--act N` se perdía en silencio), los 18 fixes mecánicos con sus contraposiciones, y las **3 decisiones que le pertenecen al usuario** (branch protection, los 6,1 s del lowpass, la rotación del AccessKey de Aliyun) |

---

## Token Budget

| Archivo/Pattern | Clasificación | Razón |
|-----------------|---------------|-------|
| `CONTEXT.md` | L (LOAD) | Misión del silo |
| `HANDOFF-*.md` | R (REFERENCE) | Cierre de un BLOQUE — leer al retomar ese BLOQUE, no de entrada |

> Las tres marcas `L (LOAD)`, `S (SKIP)`, `R (REFERENCE)` aparecen literalmente.

---

## Bridges

| Bridge | Recurso | Truth Anchor |
|--------|---------|-------------|
| `HANDOFF-*.md` → `src/` | Lo que el handoff dice haber tocado | `git log --oneline --grep='BLOQUE N'` + `git show --stat` |
| `HANDOFF-*.md` → suite | Los números que el handoff declara | `python -m pytest tests/ --tb=no` (NO agregar `-q`: pyproject ya lo pone) |
| `HANDOFF-*.md` → release | El tag que el handoff dice haber publicado | `git tag --list 'v*' \| sort -V` |

> Cada bridge necesita un Truth Anchor verificable: comando shell real, no la frase suelta.

---

## Cuándo entrar a este silo

- Retomar un BLOQUE a medio hacer.
- "¿Qué quedó sin portar?" antes de dar por cerrado un trabajo.
- Antes de mergear una línea de release: leer el handoff del BLOQUE que lajordan.
- Verificar los números de suite que un handoff declara.

## Cuándo NO entrar

- Implementar features → ir a `src/`.
- Decisiones de diseño → ir a `docs/arch/`.
- Historia completa de versiones → ir a `docs/changelog/`.

---

## Regla de oro: un handoff declara lo que NO se hizo

La parte más valuable de un handoff es la lista de **lo que quedó sin
portar** y **por qué**. Un handoff que solo dice "listo" es ruido; uno que
documenta "esto NO se portó porque X, y el costo de portarlo es Y" es lo
que evita que la próxima sesión repita el mismo error.

Referencia: `HANDOFF-GOLIATH-PORT-V140-2026-10-23.md` §4 documenta por qué no
se portaron 3 tests de la rama BLOQUE 66 (necesitaban APIs que no existen
ni en v1.4.0 ni en master) y §7 deja escrita la regla que evitó el
error de la v1.7.1: *la línea de este trabajo es v1.4.0; una feature de
BLOQUE 72+ entra sólo por pedido explícito*.
