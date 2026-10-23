# 🏛️ Switch de Contexto — VOID HUNTER

**Versión:** 1.4.0
**Propósito:** Navegación entre silos del proyecto VOID HUNTER.
**Perfil SF/SM:** Lite
**Schema target:** `.synapse` 2.2.0 (acepta 2.1.0 legacy)
**Última actualización:** 2026-10-23 (synapse-deep post BLOQUE 73.7 — paths reales, handoff GOLIATH/menú)

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
| **L2** | `src/` | Código fuente (24.7K LOC, 79 archivos, 14 sistemas) | Implementar features |
| **L2** | `tests/` | 1,630 tests pytest (~24K LOC, 38 archivos) | TDD / regression |
| **L2** | `Assets/` | Binarios (sprites, audio, galaxy panels, video) | Solo lectura, regenerar con `tools/` |
| **L2** | `tools/` | Dev-only (captura, debug, generación, video_gen) | Verificar visuales, generar assets |
| **L3** | `docs/arch/CONTEXT.md` | Arquitectura + roadmap + GDD | Decisiones de diseño |
| **L3** | `docs/changelog/CONTEXT.md` | Changelog histórico | "¿qué se intentó antes?" |
| **L3** | `docs/bloques/CONTEXT.md` | Checklists de BLOQUE (mega + user) | Tracking de features |
| **L3** | `docs/session-reports/CONTEXT.md` | Reportes de sesión | Continuity cross-session |
| **L3** | `docs/handoffs/CONTEXT.md` | Handoffs cross-session (cierre formal de BLOQUE grande) | Antes de retomar un subsistema cerrado |
| **L3** | `docs/superpowers/CONTEXT.md` | Planes + specs de features grandes | Diseño de features nuevas |
| **L3** | `docs/design/CONTEXT.md` | Game design (GDD) | Game design questions |
| **L3** | `docs/movement/CONTEXT.md` | Coreografía de naves (FROZEN subsystem) | ANTES de tocar `src/movement/` o `src/systems/wave_patterns/` |
| **L3** | `docs/references/CONTEXT.md` | Assets de referencia (sprites, paneles) | Visual references |

> **Regla:** los silos `docs/*/CONTEXT.md` son **passive hubs** (sin `.synapse`).
> Solo el root tiene `.synapse` (Fase 4 del protocolo sf-sm-doctor).
> **Silos L3 actuales (9):** arch, changelog, bloques, session-reports, handoffs, superpowers, design, references, movement (`docs/movement/` es sub-silo FROZEN — ver Switch).

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
| `docs/arch/ROADMAP.md` / `docs/bloques/MEGA_BLOQUE_58.8_CHECKLIST.md` | R (REFERENCE) | Roadmap + tracking |
| `Assets/**/*.png` | R (REFERENCE) | Binarios (no editar a mano) |
| `Assets/**/*.wav` | R (REFERENCE) | Audio assets |
| `Assets/video/**/*.png` | R (REFERENCE) | Video frames cinemáticos (no editar) |
| `Assets/sprites/player_ships/*_spritesheet.png` | R (REFERENCE) | Sprite sheets de naves |
| `release/videos/*.mp4` | R (REFERENCE) | Videos standalone (share externos) |
| `tools/**/*.py` | R (REFERENCE) | Dev tools (no productiva) |
| `tools/playtest_out/**/*.png` | R (REFERENCE) | Visual proofs |
| `tools/video_gen/**` | R (REFERENCE) | Pipeline de generación de video |
| `*.log` | S (SKIP) | Logs de ejecución |
| `dist/` / `build/` | S (SKIP) | Output PyInstaller |
| `release/` (general) | S (SKIP) | Output deliverables (gitignored) |
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
| Generate cinematic V1 (title) | `python tools/video_gen/gen_v1_title.py` | Generar 360 frames V1-G in-game + base para V1-S mp4 |
| Generate cinematic V2 (zoom) | `python tools/video_gen/gen_v2_zoom.py` | Generar 300 frames V2-G in-game + base para V2-S mp4 |
| Encode mp4 from frames | `python tools/video_gen/encode_mp4.py <frames_dir> <out.mp4> <w> <h> <fps>` | Generar mp4 standalone desde PNGs |
| Build ship sprite sheets | `python tools/build_sprite_sheet.py [ship_id]` | Generar ship_NN_spritesheet.png (5 anims × 8 frames en un PNG) |
| Video integration smoke test | `python tools/test_video_integration.py` | Headless smoke test del VideoPlayer + scenes |

---

## 🧪 Auditoría SF+SM

Comando canónico para auditar el estado del proyecto:

```powershell
$env:PYTHONIOENCODING = "utf-8"
python "C:\Users\Lerius\.minimax\skills\sf-sm-doctor\scripts\audit_sf_sm.py" "F:\AI\MM\void-hunter" --perfil=lite
```

Target: `7/7` compliance Lite (9 silos L3). Si baja, correr remediación.

> **Nota:** el path del script y el del repo se movieron cuando las skills
> se instalaron en `C:\Users\Lerius\.minimax\skills` y el repo en
> `F:\AI\MM\`. Antes apuntaba a `D:\AI\Hermes SKills\...` y `D:\AI\void-hunter`.

---

## Historial de Breaches

| Fecha | Motivo | Silos | Archivos | Resultado |
|-------|--------|-------|----------|-----------|
| 2026-10-22 | Cierre BLOQUE 73.1→73.7 (GOLIATH animado + escudo visible + menú principal) | src/ui, src/core, src/systems, Assets, tools, tests, docs | ~40 archivos | v1.5.0 → v1.6.3 publicadas; 5 releases en GitHub |

---

## Historial de cambios estructurales

- **2026-08-17** — sf-sm-doctor primera pasada. Compliance `1/7 → 7/7`:
  - Tree Integrity: `CHANGELOG.md` movido de raíz a `docs/changelog/`.
  - `CLAUDE.md` creado con 8 essentials + marcador `**Perfil SF/SM:** Lite` + bloque `STATUS:GENERATED`.
  - `CONTEXT.md` raíz creado con ADUANA + silos + Token Budget L/S/R.
  - 7 silos en `docs/` con `CONTEXT.md` (passive hubs, sin `.synapse`).
  - `.synapse` schema 2.2.0 en root.
- **2026-09-14** — sf-sm-doctor remediación manual (script no disponible en `D:\AI\Hermes SKills`). Compliance `7/7 → 8/8`:
  - Tree Integrity: 9 logs L1 movidos a `logs/` (4 directos) o renombrados a `logs/_root_*` (5 preservados para inspección). `smoke.py` movido a `tools/smoke.py`. `MANIFEST.md` archivado en `_trash_2026-09-10/MANIFEST.md` (gitignored via nueva regla `_trash_*/` en `.gitignore`).
  - Nuevo silo L3 `docs/handoffs/` con `CONTEXT.md` (passive hub). Switch CONTEXT.md +1 silo (handoffs).
  - CLAUDE.md Mapa del Edificio +1 L3 (handoffs). STATUS:GENERATED regenerado a valores reales (26,760 LOC / 87 files src/ / 2,700 tests pass / v1.4.0+).
  - Historial estructural actualizado con BLOQUE 70 (v1.3.0), BLOQUE 71 (v1.4.0), BLOQUE 72 Task 5.
- **2026-10-23 (synapse-deep post BLOQUE 73.7)** — Actualización documental de la sesión GOLIATH + menú principal:
  - Switch v1.3.0 → v1.4.0. Rutas corregidas: `docs/ROADMAP.md` → `docs/arch/ROADMAP.md`, `docs/MEGA_BLOQUE_58.8_CHECKLIST.md` → `docs/bloques/MEGA_BLOQUE_58.8_CHECKLIST.md`.
  - Comando de auditoría actualizado al path real: `C:\Users\Lerius\.minimax\skills\sf-sm-doctor\scripts\audit_sf_sm.py` sobre `F:\AI\MM\void-hunter` (antes apuntaba a `D:\AI\Hermes SKills\...` y `D:\AI\void-hunter`, paths que ya no existen).
  - Tabla "Bridges Externos": 6 filas duplicadas eliminadas (Build .exe, Tests, Galaxy extraction, Player ship sheets, Audio lowpass test, Nebula render test estaban repetidas).
  - Historial de Breaches: primera fila registrada (cierre BLOQUE 73.1→73.7, cross-silo, 5 releases v1.5.0→v1.6.3).
  - Silo `docs/handoffs/` +1 doc: `HANDOFF-GOLIATH-MENU-2026-10-23.md` (mapa autoritativo de GOLIATH + menú principal; supersede `docs/GOLIATH_HANDOFF.md`, congelado en v1.6.2).
- **2026-10-23 (2ª pasada — sf-sm-doctor + gstack-review)** — Auditoría formal de la sesión GOLIATH + menú:
  - `sf-sm-doctor` 4/7 → **7/7** (exit 0, 0 findings). El gap era `docs/handoffs/CONTEXT.md` sin sección Token Budget → agregada con formato L/S/R y Truth Anchors.
  - `gstack-review`: gate scan `listed=4 eligible=4 tagged={}` (sin relajaciones RH-*), shell injection limpio, `.gitignore` verificado (ningún archivo ya commiteado queda ignorado).
  - **Defecto funcional corregido:** el selector de fondo del menú era inerte en gameplay (`GameplayRuntime` sin back-ref `_game` → `bg_mode` clavado en 1) y el modo 1 perdía la capa de parallax. Fix en `src/ui/scenes.py` + `src/ui/gameplay_runtime.py`; nuevo `tests/test_bg_mode_render.py` (5 tests de píxeles).
  - `src/audio/music.py`: `SyntaxError` de escape `\A` corregido (docstring con path obsoleto `D:\AI\void-hunter`).
  - Suite final: **2,791 pass + 8 fail + 6 skipped (2,805 total)**.
