# 🏛️ Switch de Contexto — VOID HUNTER

**Versión:** 1.0.0
**Propósito:** Navegación entre silos del proyecto VOID HUNTER.
**Perfil SF/SM:** Lite
**Schema target:** `.synapse` 2.2.0 (acepta 2.1.0 legacy)

---

## ⚠️ ADUANA — Inducción Obligatoria

Antes de trabajar en este proyecto, leer en este orden:

1. `CLAUDE.md` — Identidad del proyecto, reglas globales, soberanía.
2. Este archivo (`CONTEXT.md`) — Switch de contexto + Token Budget global.
3. `docs/<silo>/CONTEXT.md` — Misión y Token Budget del silo destino.

Regla: entrar por L1 → L1.5 → identificar silo → leer CONTEXT.md del silo → trabajar.

---

## 🏢 Mapa del Edificio — Silos

| Piso | Silo | Propósito | Cuándo ir |
|------|------|-----------|-----------|
| **L1** | `CLAUDE.md` | Identidad + reglas globales | Siempre (inducción) |
| **L1.5** | `CONTEXT.md` | Switch de contexto | Antes de cualquier tarea |
| **L2** | `src/` | Código fuente (28K LOC, 13 sistemas) | Implementar features |
| **L2** | `tests/` | 1,171 tests pytest | TDD / regression |
| **L2** | `Assets/` | Binarios (sprites, audio, galaxy panels) | Solo lectura, regenerar con `tools/` |
| **L2** | `tools/` | Dev-only (captura, debug, generación) | Verificar visuales, generar assets |
| **L3** | `docs/arch/CONTEXT.md` | Arquitectura + roadmap + GDD | Decisiones de diseño |
| **L3** | `docs/changelog/CONTEXT.md` | Changelog histórico | "¿qué se intentó antes?" |
| **L3** | `docs/bloques/CONTEXT.md` | Checklists de BLOQUE (mega + user) | Tracking de features |
| **L3** | `docs/session-reports/CONTEXT.md` | Reportes de sesión | Continuity cross-session |
| **L3** | `docs/superpowers/CONTEXT.md` | Planes + specs de features grandes | Diseño de features nuevas |
| **L3** | `docs/design/CONTEXT.md` | Game design (GDD) | Game design questions |
| **L3** | `docs/references/CONTEXT.md` | Assets de referencia (sprites, paneles) | Visual references |

> **Regla:** los silos `docs/*/CONTEXT.md` son **passive hubs** (sin `.synapse`).
> Solo el root tiene `.synapse` (Fase 4 del protocolo sf-sm-doctor).

---

## 📋 Token Budget Global

| Archivo / Pattern | Clasificación | Razón |
|-------------------|---------------|-------|
| `CLAUDE.md` | L (LOAD) | Identidad del proyecto |
| `CONTEXT.md` | L (LOAD) | Switch de contexto |
| `.synapse` | L (LOAD) | Estado del root |
| `docs/*/CONTEXT.md` | L (LOAD) | Misión del silo |
| `src/**/*.py` | L (LOAD) | Código del producto |
| `tests/**/*.py` | L (LOAD) | Tests del producto |
| `docs/arch/ARCHITECTURE.md` | L (LOAD) | Mapa del sistema |
| `docs/changelog/CHANGELOG_v1.x.md` | L (LOAD) | Historia de cambios |
| `main.py` / `build.spec` | L (LOAD) | Entry point + build |
| `README.md` | R (REFERENCE) | Doc pública |
| `requirements.txt` / `pyproject.toml` | R (REFERENCE) | Configuración |
| `docs/ROADMAP.md` / `docs/MEGA_BLOQUE_58.8_CHECKLIST.md` | R (REFERENCE) | Roadmap + tracking |
| `Assets/**/*.png` | R (REFERENCE) | Binarios (no editar a mano) |
| `Assets/**/*.wav` | R (REFERENCE) | Audio assets |
| `tools/**/*.py` | R (REFERENCE) | Dev tools (no productiva) |
| `tools/playtest_out/**/*.png` | R (REFERENCE) | Visual proofs |
| `*.log` | S (SKIP) | Logs de ejecución |
| `dist/` / `build/` | S (SKIP) | Output PyInstaller |
| `.git/` | S (SKIP) | Control de versiones |
| `.mypy_cache/` / `.ruff_cache/` / `.pytest_cache/` | S (SKIP) | Caché de tools |
| `__pycache__/` / `*.pyc` | S (SKIP) | Python bytecode |
| `venv/` | S (SKIP) | Entorno virtual |

> Las tres marcas `L (LOAD)`, `S (SKIP)`, `R (REFERENCE)` deben aparecer
> literalmente para que la auditoría sf-sm-doctor reconozca el formato.

---

## 🔗 Bridges Iniciales

VOID HUNTER es una **app standalone pygame** — no tiene servicios runtime propios, puertos localhost, ni procesos UP/DOWN que cambien decisiones del agente. Por eso este proyecto está en perfil **Lite** (los Truth Anchors de 3 capas no aplican).

| Bridge | Recurso | Truth Anchor |
|--------|---------|-------------|
| *(ninguno — perfil Lite)* | — | — |

Si en el futuro Void-Hunter pasa a tener un servicio (servidor de replays, leaderboard, etc.), cambiar a perfil **Full** y declarar los bridges aquí con `curl -s -m 3 -o /dev/null -w "%{http_code}" http://localhost:PORT/` o equivalente.

---

## 🔄 Bridges Externos (no-runtime)

Estos no son runtime bridges, son referencias a recursos externos que el agente puede invocar:

| Recurso | Comando | Uso |
|---------|---------|-----|
| Build .exe | `pyinstaller build.spec --clean -y` | Generar `dist/void-hunter/void-hunter.exe` |
| Tests | `python -m pytest tests/ -q` | Validar regresiones |
| Galaxy extraction | `python tools/process_galaxy_sprites_v2.py` | Regenerar sprites de nebula desde paneles |
| Player ship sheets | `python tools/generate_player_ship_sheets.py` | Regenerar 5 naves × 5 anims × 8 frames |
| Audio lowpass test | `python tools/test_music_continuous_lowpass.py` | Verificar pause/resume posicional |
| Nebula render test | `python tools/test_nebula_render.py` | Verificar render de nebula headless |

---

## 🧪 Auditoría SF+SM

Comando canónico para auditar el estado del proyecto:

```bash
$env:PYTHONIOENCODING = "utf-8"
python "D:\AI\Hermes SKills\skills\devops\sf-sm-doctor\scripts\audit_sf_sm.py" "D:\AI\void-hunter" --perfil=lite
```

Target: `7/7` compliance Lite. Si baja, correr remediación.

---

## Historial de Breaches

| Fecha | Motivo | Silos | Archivos | Resultado |
|-------|--------|-------|----------|-----------|
| — | — | — | — | — |

---

## Historial de cambios estructurales

- **2026-08-17** — sf-sm-doctor primera pasada. Compliance `1/7 → 7/7`:
  - Tree Integrity: `CHANGELOG.md` movido de raíz a `docs/changelog/`.
  - `CLAUDE.md` creado con 8 essentials + marcador `**Perfil SF/SM:** Lite` + bloque `STATUS:GENERATED`.
  - `CONTEXT.md` raíz creado con ADUANA + silos + Token Budget L/S/R.
  - 7 silos en `docs/` con `CONTEXT.md` (passive hubs, sin `.synapse`).
  - `.synapse` schema 2.2.0 en root.
