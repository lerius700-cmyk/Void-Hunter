# Silo: bloques (Bloque History)

**Propósito:** Checklists de tracking de los BLOQUEs del producto. Cada BLOQUE agrupa N tareas (T1, T2, ...) que se commitean juntas.

---

## Contenido del silo

| Archivo | Tipo | Descripción |
|---------|------|-------------|
| `MEGA_BLOQUE_58.8_CHECKLIST.md` | Tracking | Checklist del BLOQUE 58.8 con todas las tareas (T1, T2, ...) marcadas |
| `USER_PROMPTS_CHECKLIST.md` | Tracking | Histórico de pedidos del usuario (qué pidió, qué se entregó) |

---

## Token Budget

| Archivo/Pattern | Clasificación | Razón |
|-----------------|---------------|-------|
| `CONTEXT.md` | L (LOAD) | Misión del silo |
| `MEGA_BLOQUE_58.8_CHECKLIST.md` | R (REFERENCE) | Tracking de un BLOQUE específico (consultar al estimar) |
| `USER_PROMPTS_CHECKLIST.md` | R (REFERENCE) | Histórico (consultar "¿el usuario ya pidió esto?") |

> Las tres marcas `L (LOAD)`, `S (SKIP)`, `R (REFERENCE)` aparecen literalmente.

---

## Bridges

| Bridge | Recurso | Truth Anchor |
|--------|---------|-------------|
| CHECKLIST ↔ git commits | Cada item del checklist tiene un commit | `git log --grep='BLOQUE 58.8' --oneline` |
| USER_PROMPTS ↔ CHANGELOG | Cada pedido tiene un BLOQUE asignado | `grep -l 'BLOQUE 58.14' docs/changelog/CHANGELOG_v1.x.md` |

---

## Cuándo entrar a este silo

- Planificar un BLOQUE nuevo.
- Verificar qué tareas de un BLOQUE están pendientes.
- "¿El usuario ya pidió X?" antes de implementar.
- Reportar estado de un BLOQUE al usuario.

## Cuándo NO entrar

- Implementar → ir a `src/`.
- Decisiones de diseño → ir a `docs/arch/` o `docs/design/`.

---

## Lock Status

**Estado:** Sin lock
