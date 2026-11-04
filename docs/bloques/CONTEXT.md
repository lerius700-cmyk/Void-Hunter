# Silo: bloques (Bloque History)

**Propósito:** Checklists de tracking de los BLOQUEs del producto. Cada BLOQUE agrupa N tareas (T1, T2, ...) que se commitean juntas.

---

## Contenido del silo

| Archivo | Tipo | Descripción |
|---------|------|-------------|
| `MEGA_BLOQUE_58.8_CHECKLIST.md` | Tracking | Checklist del BLOQUE 58.8 con todas las tareas (T1, T2, ...) marcadas |
| `BLOQUE_75_CHECKLIST.md` | Tracking | Checklist del BLOQUE 75 (Fase 1: pipeline de enemigos · Fase 2: motor de capas del frame). Marca las 10 tareas, las 6 rondas de fix, las 5 garantías con su mutación, y **lo que falta**: el CI sin el gate, el `.exe` sin la Fase 2 y el changelog sin BLOQUE 75 |
| `USER_PROMPTS_CHECKLIST.md` | Tracking | Histórico de pedidos del usuario (qué pidió, qué se entregó) |

---

## Token Budget

| Archivo/Pattern | Clasificación | Razón |
|-----------------|---------------|-------|
| `CONTEXT.md` | L (LOAD) | Misión del silo |
| `BLOQUE_75_CHECKLIST.md` | R (REFERENCE) | Estado de BLOQUE 75: qué se hizo y qué falta (consultar al retomar) |
| `MEGA_BLOQUE_58.8_CHECKLIST.md` | R (REFERENCE) | Tracking de un BLOQUE específico (consultar al estimar) |
| `USER_PROMPTS_CHECKLIST.md` | R (REFERENCE) | Histórico (consultar "¿el usuario ya pidió esto?") |

> Las tres marcas `L (LOAD)`, `S (SKIP)`, `R (REFERENCE)` aparecen literalmente.

---

## Bridges

| Bridge | Recurso | Truth Anchor |
|--------|---------|-------------|
| CHECKLIST ↔ git commits | Cada item del checklist tiene un commit | `git log --grep='BLOQUE 58.8' --oneline` |
| CHECKLIST ↔ git commits | Cada item de BLOQUE 75 tiene su commit | `git log --oneline e619527..HEAD` (37 commits de la Fase 2) y `git log --grep='BLOQUE 75' --oneline` |
| CHECKLIST ↔ suite | Los números que el checklist declara | `python -m pytest tests/ --tb=no` (NO agregar `-q`: pyproject ya lo pone) y leer el XML de junit |
| CHECKLIST ↔ gates | Las dos puertas de la fase | `python tools/sprite_pipeline/gate.py --phase 1` y `--phase 2` |
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
