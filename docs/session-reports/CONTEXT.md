# Silo: session-reports

**Propósito:** Reportes consolidados de sesiones de desarrollo. Continuity cross-session para que un agente (humano o AI) pueda retomar trabajo donde otro lo dejó.

---

## Contenido del silo

| Archivo | Tipo | Descripción |
|---------|------|-------------|
| `SESSION_REPORT_BLOQUES_18-53.txt` | Reporte | Resumen consolidado de BLOQUEs 18 al 53 (~35 BLOQUEs de feature) |

> **Nota:** este archivo es `.txt` (no `.md`) porque es un dump consolidado. El check de Tree Integrity cuenta solo `.md`, pero el contenido sigue siendo documentación válida.

---

## Token Budget

| Archivo/Pattern | Clasificación | Razón |
|-----------------|---------------|-------|
| `CONTEXT.md` | L (LOAD) | Misión del silo |
| `SESSION_REPORT_*.txt` | R (REFERENCE) | Reportes históricos (consultar al retomar) |

> Las tres marcas `L (LOAD)`, `S (SKIP)`, `R (REFERENCE)` aparecen literalmente.

---

## Bridges

| Bridge | Recurso | Truth Anchor |
|--------|---------|-------------|
| SESSION_REPORT ↔ Mavis memory | Resúmenes de sesión | `~/.minimax/agents/mavis/memory/MEMORY.md` |

---

## Cuándo entrar a este silo

- Retomar trabajo después de un gap largo.
- "¿Qué se hizo en la última sesión?" antes de planear.
- Continuity cuando un agente AI distinto agarra el proyecto.

## Cuándo NO entrar

- Implementar → ir a `src/`.
- Decisiones de diseño → ir a `docs/arch/`.

---

## Lock Status

**Estado:** Sin lock
