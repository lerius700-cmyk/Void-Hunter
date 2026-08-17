# Silo: superpowers (Feature Plans + Specs)

**Propósito:** Planes y specs de features grandes. Antes de implementar una feature importante, primero se escribe un plan y un spec aquí. Después se commitea el código siguiendo el plan.

---

## Contenido del silo

| Archivo | Tipo | Descripción |
|---------|------|-------------|
| `plans/2026-08-15-bezier-choreography.md` | Plan | Plan de implementación de bezier choreography (BLOQUE 58.13) |
| `specs/2026-08-15-bezier-choreography-design.md` | Spec | Spec de diseño de la feature (qué hace, cómo se ve, contratos) |

> **Convención:** los archivos tienen prefijo de fecha `YYYY-MM-DD-<feature>.md` para que sea fácil navegar cronológicamente.

---

## Token Budget

| Archivo/Pattern | Clasificación | Razón |
|-----------------|---------------|-------|
| `CONTEXT.md` | L (LOAD) | Misión del silo |
| `plans/*.md` | L (LOAD) | Plan de implementación — leer ANTES de codear |
| `specs/*.md` | L (LOAD) | Spec de diseño — leer ANTES de codear |

> Las tres marcas `L (LOAD)`, `S (SKIP)`, `R (REFERENCE)` aparecen literalmente.

---

## Bridges

| Bridge | Recurso | Truth Anchor |
|--------|---------|-------------|
| plan ↔ spec | Cada plan tiene un spec correspondiente | `ls plans/ specs/ \| xargs -I{} basename {} .md \| sort -u` |
| plan ↔ git | Cada plan tiene commit de implementación | `git log --grep='$(basename plan .md)' --oneline` |

---

## Cuándo entrar a este silo

- ANTES de implementar una feature grande (BLOQUE nuevo).
- "¿Cómo se planeó esta feature originalmente?"
- Para features que tocan múltiples sistemas.

## Cuándo NO entrar

- Bug fix pequeño → ir directo a `src/`.
- Cambio visual iterativo → `tools/` con captura.

---

## Lock Status

**Estado:** Sin lock
