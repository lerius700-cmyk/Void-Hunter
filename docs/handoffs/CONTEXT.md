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
