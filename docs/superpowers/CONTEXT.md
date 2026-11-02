# Silo: superpowers (Feature Plans + Specs)

**Propósito:** Planes y specs de features grandes. Antes de implementar una feature importante, primero se escribe un plan y un spec aquí. Después se commitea el código siguiendo el plan.

---

## Contenido del silo

| Archivo | Tipo | Descripción |
|---------|------|-------------|
| `plans/2026-08-15-bezier-choreography.md` | Plan | Plan de implementación de bezier choreography (BLOQUE 58.13) |
| `specs/2026-08-15-bezier-choreography-design.md` | Spec | Spec de diseño de la feature (qué hace, cómo se ve, contratos) |
| `prompts/2026-10-29-bloque-75-migration-spec-prompt.md` | Prompt | Prompt de 8 dimensiones que produce el spec de BLOQUE 75 (migración del pipeline de sprites, 2 fases con gate) |
| `specs/2026-10-29-agent-context-handoff-design.md` | Spec | Diseño del handoff de contexto entre agentes: el repo como único canal (un worktree y una rama por agente, commits → handoff → `.synapse`) |
| `specs/2026-10-30-bloque-75-migration-spec.md` | Spec | Spec de BLOQUE 75: migración del pipeline de sprites en 2 fases con gate — Fase 1 los 8 sets de enemigos al pipeline (manifest + anchors, 0 FAIL, PNG intocables), Fase 2 el frame de gameplay como `LayerStack` + `DrawContext` con verificación pixel a pixel |

> **Convención:** los archivos tienen prefijo de fecha `YYYY-MM-DD-<feature>.md` para que sea fácil navegar cronológicamente.

---

## Token Budget

| Archivo/Pattern | Clasificación | Razón |
|-----------------|---------------|-------|
| `CONTEXT.md` | L (LOAD) | Misión del silo |
| `prompts/**` | L (LOAD) | El prompt que produce el spec |
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
