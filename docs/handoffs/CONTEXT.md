# 🏛️ docs/handoffs — Cross-session Handoffs

**Versión:** 1.0.0 (creado 2026-09-14, remediación sf-sm-doctor)
**Perfil SF/SM:** Lite — passive hub (sin `.synapse`)
**Misión:** Almacenar documentos de handoff entre sesiones — notas estructuradas para que el siguiente agente que tome un subsistema (asteroides, audio, etc.) sepa exactamente dónde quedó el trabajo.

---

## 🎯 Cuándo ir a este silo

- Antes de empezar a trabajar en un subsistema que tuvo un BLOQUE cerrado recientemente (ver `.synapse` `last_successful_action`).
- Cuando el usuario dice "voy a volver a X" / "pasame el estado de Y" / "qué quedó pendiente".
- Para escribir un nuevo handoff al cerrar una sesión grande (lanzar el handoff como cierre formal, no solo `.synapse`).
- **NO** para reportes generales de sesión → eso va en `docs/session-reports/`.

---

## 📂 Contenido actual

| Archivo | Subsistema | BLOQUE | Última actualización |
|---------|-----------|--------|----------------------|
| `HANDOFF-ASTEROIDES-2026-09-09.md` | Asteroides / MINE-ASTEROID | BLOQUE 70 (cierre v1.3.0) | 2026-09-09 |
| `HANDOFF-BLOQUE-71-72-2026-09-12.md` | Asteroid hit feedback + 4-weapon powerup system | BLOQUE 71 (release v1.4.0) + BLOQUE 72 (en curso, T5 done) | 2026-09-12 |

---

## 📐 Convención de naming

`HANDOFF-<SUBSISTEMA>-YYYY-MM-DD.md`

- `<SUBSISTEMA>` en MAYÚSCULAS, sin espacios (usar `_` si compuesto).
- Fecha = día de cierre del BLOQUE que origina el handoff.
- Primera línea = `# HANDOFF — Trabajo futuro en <subsistema> (<proyecto>)`.
- Estructura sugerida:
  1. TL;DR (qué se cerró, qué quedó pendiente).
  2. Estado actual del proyecto (versión, commit, build).
  3. Feature — qué hace / qué NO hace.
  4. Gotchas / bugs abiertos / decisiones pendientes.
  5. Cómo retomar (archivos clave, tests específicos, comandos).
  6. Si vas a hacer OTRA cosa (no este subsistema) → "Other BLOQUE work" al final.

---

## 🔗 Bridges

Este silo **NO** tiene bridges runtime (perfil Lite). Es un silo de documentación que conecta con:

- `docs/session-reports/` → los reportes detallados de la sesión que originó el handoff.
- `docs/changelog/` → el BLOQUE específico que cerró el handoff.
- `.synapse` raíz → `short_term_memory.active_context_pointers` debe apuntar al handoff activo.