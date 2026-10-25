# 🏛️ Switch de Contexto — VOID HUNTER

**Versión:** 1.3.0 (línea v1.7.2 / BLOQUE 67)
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
| **L2** | `src/` | Código fuente (27.7K LOC, 86 archivos, 14 sistemas) | Implementar features |
| **L2** | `tests/` | 2,781 tests pytest (~22.7K LOC, 83 archivos) | TDD / regression |
| **L2** | `Assets/` | Binarios (sprites, audio, galaxy panels, tiles, video) | Solo lectura, regenerar con `tools/` |
| **L2** | `tools/` | Dev-only (captura, debug, generación, video_gen) | Verificar visuales, generar assets |
| **L3** | `docs/arch/CONTEXT.md` | Arquitectura + roadmap + GDD | Decisiones de diseño |
| **L3** | `docs/changelog/CONTEXT.md` | Changelog histórico | "¿qué se intentó antes?" |
| **L3** | `docs/bloques/CONTEXT.md` | Checklists de BLOQUE (mega + user) | Tracking de features |
| **L3** | `docs/session-reports/CONTEXT.md` | Reportes de sesión | Continuity cross-session |
| **L3** | `docs/handoffs/CONTEXT.md` | Handoffs cross-session (cierre formal de BLOQUE) | Retomar un BLOQUE a medio hacer |
| **L3** | `docs/superpowers/CONTEXT.md` | Planes + specs de features grandes | Diseño de features nuevas |
| **L3** | `docs/design/CONTEXT.md` | Game design (GDD) | Game design questions |
| **L3** | `docs/movement/CONTEXT.md` | Coreografía de naves (FROZEN subsystem) | ANTES de tocar `src/movement/` o `src/systems/wave_patterns/` |
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
| `Assets/video/**/*.png` | R (REFERENCE) | Video frames cinemáticos (no editar) |
| `Assets/sprites/player_ships/*_spritesheet.png` | R (REFERENCE) | Sprite sheets de naves |
| `Assets/background/tiles/act1/*.png` | R (REFERENCE) | 6 tiles del fondo Asteroid Approach (no editar a mano) |
| `release/videos/*.mp4` | R (REFERENCE) | Videos standalone (share externos) |
| `tools/**/*.py` | R (REFERENCE) | Dev tools (no productiva) |
| `tools/playtest_out/**/*.png` | R (REFERENCE) | Visual proofs |
| `tools/video_gen/**` | R (REFERENCE) | Pipeline de generación de video |
| `tools/tiles/**` | R (REFERENCE) | Pipeline del fondo Asteroid Approach (`generate_tiles.py` + `ai_gen/`) |
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
| Build .exe (onefile) | `python -m PyInstaller build.spec --clean --noconfirm` | Generar `dist/void-hunter.exe` (~278 MB) |
| Tests | `python -m pytest tests/ --tb=no` | Validar regresiones (NO agregar `-q`: pyproject ya lo pone) |
| Self-test del juego | `python main.py --check` | Verificar imports + settings sin abrir ventana |
| Pelea directa | `python main.py --boss goliath --easy --duration 60` | Saltar al boss fight (TITLE→ACT_INTRO→GAMEPLAY→BOSS_INTRO→BOSS_FIGHT) |
| Smoke del flujo completo | `python tools/capture/capture_full_flow_v140.py` | Recorrer TITLE→CINEMATIC→MENU→…→BOSS_FIGHT headless |
| Captura del escudo | `python tools/capture/capture_goliath_shield_bloque67.py` | Rampa de carga + láser del escudo |
| Captura del menú | `python tools/capture/capture_main_menu.py` | Los 5 estados del menú |
| Tiles del fondo | `python tools/tiles/generate_tiles.py` | Regenerar los tiles del "Asteroid Approach" |
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

```bash
$env:PYTHONIOENCODING = "utf-8"
python "C:\Users\Lerius\.minimax\skills\sf-sm-doctor\scripts\audit_sf_sm.py" "F:\AI\MM\void-hunter" --perfil=lite
```

Target: `7/7` compliance Lite. Si baja, correr remediación.

> La ruta vieja `D:\AI\Hermes SKills\...` ya no existe (skills migradas a
> `C:\Users\Lerius\.minimax\skills\`).

---

## Historial de Breaches

| Fecha | Motivo | Silos | Archivos | Resultado |
|-------|--------|-------|----------|-----------|
| — | — | — | — | — |

---

## Historial de cambios estructurales

- **2026-10-25 (BLOQUE 67)** — Línea v1.4.0 + GOLIATH + menú post-cinematica (v1.7.2):
  - Silo nuevo `docs/handoffs/` (handoffs cross-session) con su `CONTEXT.md`.
  - `docs/arch/` gana el silo de handoffs en la tabla de silos.
  - Tokens: `Assets/background/tiles/act1/*.png` y `tools/tiles/**` pasan a R (REFERENCE).
  - Bridges externos: comando de build corregido a `python -m PyInstaller build.spec
    --clean --noconfirm` (el spec es **onefile**, no onedir) y se deduplican las
    6 filas repetidas.
  - Ruta de la auditoría corregida a `C:\Users\Lerius\.minimax\skills\...`.
- **2026-08-17** — sf-sm-doctor primera pasada. Compliance `1/7 → 7/7`:
  - Tree Integrity: `CHANGELOG.md` movido de raíz a `docs/changelog/`.
  - `CLAUDE.md` creado con 8 essentials + marcador `**Perfil SF/SM:** Lite` + bloque `STATUS:GENERATED`.
  - `CONTEXT.md` raíz creado con ADUANA + silos + Token Budget L/S/R.
  - 7 silos en `docs/` con `CONTEXT.md` (passive hubs, sin `.synapse`).
  - `.synapse` schema 2.2.0 en root.
