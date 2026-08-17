# 🏛️ VOID HUNTER — Project Identity

**Perfil SF/SM:** Lite
**Schema target:** `.synapse` 2.2.0 (acepta 2.1.0 legacy)
**Versión actual:** v1.2.4 (BLOQUE 58.14.4)
**Tipo:** CODE (Python + pygame 2.6, stdlib only + numpy para lowpass audio)
**Test count:** 1,171 / 1,171 pass

---

## ¿Qué ES / Qué NO ES

**ES:** un shmup vertical 8-bit pixelart portrait 320×480 a 120 FPS, con 4 bosses (GOLIATH / HYDRA / PHANTOM / NEMESIS), modo roguelike con seed/RNG, formación Star Fox 64 + bezier paths, 24 SFX procedurales, 2 BGMs streaming, pausa con lowpass, selector de 5 naves × 5 animaciones × 8 frames, y ~28K LOC en 118 archivos Python.

**NO ES:** un MMO, un roguelike 2D con vista top-down, un juego online, un servicio con backend, un proyecto que requiere Truth Anchors de runtime (puertos localhost, ss, pgrep). Es una app standalone pygame que se compila con PyInstaller.

---

## 🏢 Mapa del Edificio

```
L1  CLAUDE.md            ← identidad + reglas globales (ESTE ARCHIVO)
L1.5 CONTEXT.md          ← Switch de contexto (ADUANA + silos + Token Budget)

L2  src/                 ← código fuente (28K LOC, 13 sistemas)
L2  tests/               ← 1,171 tests pytest
L2  Assets/              ← binarios (sprites, audio, galaxy panels, BGM)
L2  tools/               ← scripts de captura / debug / generación
L2  build.spec           ← PyInstaller onedir
L2  main.py              ← entry point

L3  docs/arch/           ← arquitectura + roadmap + GDD
L3  docs/changelog/      ← changelog v1.x + raíz
L3  docs/bloques/        ← checklists de BLOQUE (mega + user prompts)
L3  docs/session-reports/← reportes de sesión
L3  docs/superpowers/    ← planes y specs de features grandes
L3  docs/design/         ← game design (GDD, etc.)
L3  docs/references/     ← assets de referencia (sprites, paneles)
```

**Regla:** Entrar por L1 (`CLAUDE.md`) → L1.5 (`CONTEXT.md`) → identificar silo → leer `CONTEXT.md` del silo → trabajar.

---

## 📜 Sovereignty Matrix

| Capa | Archivos | Regla | Token Budget |
|------|----------|-------|--------------|
| Código | `src/**/*.py` | ES el producto | L (LOAD) |
| Tests | `tests/**/*.py` | Cubren BLOQUEs documentados | L (LOAD) |
| Assets binarios | `Assets/**/*.{png,wav,mp4}` | No editar a mano — regenerar con `tools/` | R (REFERENCE) |
| Audio dev | `tools/*.{py,ps1,bat}` | Captura / debug / generación, no productiva | R (REFERENCE) |
| Builds | `dist/`, `build/` | Output PyInstaller, gitignored | S (SKIP) |
| Caché | `.mypy_cache/`, `.ruff_cache/`, `.pytest_cache/`, `__pycache__/` | Gitignored | S (SKIP) |

**Decisiones arquitectónicas no negociables:**

1. **No numpy/scipy en runtime del juego** (GDD §0). Excepción única documentada: `apply_lowpass_to_wav` para el lowpass del pause (user-explicit, BLOQUE 58.14).
2. **Coordenadas internas 320×480** portrait; el escalado a display lo hace `Game._present()`. No hardcodear tamaños de ventana.
3. **Default mode = `--roguelike`** (BLOQUE 58); testing = `--patterns 1`. Mantener consistencia.
4. **Commits con prefijo de BLOQUE**: `feat: BLOQUE N` / `fix: BLOQUE N` / `chore: BLOQUE N`.
5. **Sub-boss (BLOQUE 50) = "Wolfen" dart**, NO un boss real. Los 4 bosses reales son GOLIATH/HYDRA/PHANTOM/NEMESIS.
6. **"minijefe" = sub-boss** en el español del usuario. "canción" = BGM de 5:30. GOLIATH aparece al menos a los 3:40 (220s).

---

## 🤖 Identidad del Agente

**Rol esperado:** Asistente de desarrollo del juego. Conoce el dominio (shmup / Star Fox 64 / bezier paths / audio continuo), mantiene continuity entre BLOQUEs, sabe navegar la base de código.

**Expertise clave:** pygame internals (Sound/Channel, mixer.music.set_pos = no-op para WAV), render 8-bit, profile-aware de SF+SM, memoria cross-session.

**Patrón de decisión:** Antes de cambiar algo, leer el BLOQUE relacionado en `docs/CHANGELOG_v1.x.md` para saber qué se intentó antes. Si un usuario muestra una imagen de referencia, **usar esa imagen** (no regenerar con AI/otra técnica) — el usuario ya invirtió en que esa imagen sea la correcta.

---

## 🧠 Reglas de Inferencia

**PUEDE asumir automáticamente:**

- Tests en `tests/` siguen convención `test_*.py` y usan pytest.
- Código en `src/` sigue convenciones PEP 8 + type hints (verificado por ruff).
- Background scroll = top→bottom, HUD = bottom.
- Audio usa `Sound + Channel` (no `mixer.music` para pause/resume posicional).
- User-facing language = español; código / commits / docs técnicas = inglés.

**DEBE preguntar:**

- "¿Querés que commitee?" antes de cualquier commit (BLOQUE 58.14 user feedback explícito).
- Cambios visuales antes de "listo" (user confirms con frame PNG explícito).
- Cambios al `.exe` (PyInstaller) — preguntar antes de rebuildear.
- Cualquier cambio que toque audio / music — preguntar antes de tocar la implementación.

---

## 📁 Estructura del Proyecto

```
void-hunter/
├── CLAUDE.md                   ← L1 (este archivo)
├── CONTEXT.md                  ← L1.5 Switch
├── README.md                   ← R (REFERENCE) — public doc
├── main.py                     ← entry point
├── build.spec                  ← PyInstaller spec
├── requirements.txt            ← runtime deps
├── requirements-dev.txt        ← dev/test deps
├── pyproject.toml              ← tool config (ruff, mypy, pytest)
│
├── src/                        ← L2 código (118 archivos, 28K LOC)
│   ├── core/                   ← game loop, settings, scene_manager
│   ├── audio/                  ← synth + music (BLOQUE 58.14)
│   ├── systems/                ← parallax, wave_manager, bezier, etc.
│   ├── entities/               ← player, enemy, boss, projectile
│   ├── ui/                     ← scenes, gameplay_runtime, HUD
│   ├── movement/               ← formation, paths
│   ├── roguelike/              ← seed, level_gen, form_gen, replay
│   └── utils/                  ← palette, easing
│
├── tests/                      ← L2 (1,171 tests, BLOQUE 1-58.14)
│
├── Assets/                     ← L2 binarios
│   ├── background/             ← galaxy_panel_*.png, galaxy_sprite_*.png
│   ├── sprites/                ← ship sprites, enemy sprites, VFX
│   ├── *.wav                   ← BGM + voice clips
│   └── keep kept - Lerius - soundtrack gameplay_lp600.wav
│
├── tools/                      ← L2 dev-only (no productiva)
│   ├── capture/                ← scripts de screenshot
│   ├── debug_*.py              ← debug tools
│   ├── test_*.py               ← ad-hoc tests
│   ├── process_galaxy_sprites_v2.py
│   ├── generate_player_ship_sheets.py
│   └── playtest_out/           ← screenshots de verificación
│
├── docs/                       ← L3 silos de documentación
│   ├── arch/                   ← arquitectura + roadmap
│   ├── changelog/              ← changelog
│   ├── bloques/                ← checklists
│   ├── session-reports/        ← reportes
│   ├── superpowers/            ← planes + specs
│   ├── design/                 ← GDD
│   └── references/             ← assets de referencia
│
├── dist/                       ← S (SKIP) — output PyInstaller
├── build/                      ← S (SKIP) — output PyInstaller
└── logs/                       ← S (SKIP) — _audio_status.log, etc.
```

---

## 🛡️ Patrones y Protocolos

| Protocolo | Cuándo usar | Dónde vive |
|-----------|-------------|------------|
| **sf-sm-doctor** (System Folder + Synapse Method) | Auditar / remediar estructura del proyecto | `D:\AI\Hermes SKills\skills\devops\sf-sm-doctor\` |
| **synapse-compact** (Consolidación de sesión) | Fin de sesión, capturar objetivo + última acción | Mavis skill |
| **synapse-deep** (Actualización documental) | Cuando hubo cambios de arquitectura / reglas / conceptos | Mavis skill |
| **sre-protocol** (SRE Protocol / Puente Roto) | Diagnosticar y reparar bridges runtime caídos (5 pasos: Symptom → Map Bridge → Execution → Verify → Document). Soporta HTTP, DB, GPU, Storage. | Mavis skill |
| **breach_autorizado** (Breach Autorizado) | Acceso cross-silo explícito (5 pasos: Declaration → Min Action → Closure → Validation → Registration) | Mavis skill |
| **test-driven-development** (TDD) | Antes de implementar feature nueva | Mavis skill |
| **systematic-debugging** (Debugging) | Ante bug, test failure, o comportamiento inesperado | Mavis skill |
| **verification-before-completion** (Verify) | Antes de decir "listo" o crear PR | Mavis skill |
| **brainstorming** | Antes de trabajo creativo (features, componentes, comportamiento nuevo) | Mavis skill |

---

## 🚀 Quickstart para Nuevos Agentes

Pasos del **P.N.D. (Protocolo de Navegación Determinista)**:

1. **BOOT** — Leer este `CLAUDE.md` completo (es corto, ~250 líneas).
2. **ADUANA** — Leer `CONTEXT.md` (Switch) para saber qué silos existen.
3. **ROUTE** — Identificar el silo relevante al task.
4. **SYNC** — Leer el `CONTEXT.md` del silo destino + su `.synapse` si existe.
5. **ISOLATE** — Trabajar SOLO dentro del silo (no tocar otros sin `breach_autorizado`).
6. **ACT** — Hacer el cambio, con TDD si es código / con `verification-before-completion` siempre.
7. **VALIDATE** — Correr tests (Lite: `pytest tests/ -q`), verificar visual (PNG), committear.

---

## 📊 Métricas del Proyecto

<!-- STATUS:GENERATED — auto-block. Do not edit by hand. Re-generated by sf-sm-doctor. -->

| Métrica | Valor | Fuente (Truth Anchor) |
|---------|-------|------------------------|
| Líneas de código (src/) | 22,981 | `python -c "import pathlib; print(sum(len(p.read_text(encoding='utf-8',errors='ignore').splitlines()) for p in pathlib.Path('src').rglob('*.py')))"` |
| Archivos Python (src/) | 75 | `Get-ChildItem -Recurse -Filter *.py src/ \| Measure-Object` |
| Tests (tests/) | 1,171 / 1,171 pass | `python -m pytest tests/ -q` (exit 0) |
| LOC tests/ (helper) | 14,485 | `pytest --collect-only -q` (test count) |
| Silos SF+SM | 7 (Lite) | `audit_sf_sm.py` |
| Compliance SF | 7/7 (Lite perfil) | `audit_sf_sm.py --perfil=lite` (exit 0) |
| Versión | v1.2.4 (BLOQUE 58.14.4) | `git log --oneline -1` |
| Rama | master | `git branch --show-current` |
| Remote | github.com/lerius700-cmyk/Void-Hunter | `git remote -v` |
| Build .exe | `dist/void-hunter/void-hunter.exe` ~4.85 MB | `Get-Item dist/void-hunter/void-hunter.exe` |

> **Nota:** los valores 22,981 LOC y 75 files en `src/` son el conteo actual
> (regenerados 2026-08-17). El valor histórico 28,066 LOC / 118 files que
> estaba en `docs/arch/ARCHITECTURE.md` (updated 2026-08-15) ya no aplica
> tras el BLOQUE SF+SM (consolidación de archivos sueltos a silos).

> **Regla:** si una métrica cambia, regenerar este bloque con el comando de la columna "Fuente". NUNCA editar a mano.

---

## Historial de cambios estructurales (post-SF+SM)

- **2026-08-17 (remediación inicial)** — sf-sm-doctor primera pasada: 1/7 → 7/7. Tree Integrity fixed (CHANGELOG.md movido a `docs/changelog/`), 7 silos creados, Token Budget L/S/R presente, `.synapse` schema 2.2.0 en root.
- **2026-08-17 (deep audit + fix)** — sf-sm-doctor deep audit reveló drift entre documentos y realidad. Fixes aplicados:
  - C-1: 6 archivos físicos movidos de `docs/` raíz a subcarpetas silo (`docs/arch/`, `docs/bloques/`, `docs/session-reports/`, `docs/changelog/`).
  - C-2: STATUS:GENERATED regenerado con métricas reales (22,981 LOC, 75 files en `src/`, 14,485 LOC en `tests/`).
  - C-3: `sre-protocol` + `synapse-deep` agregados a la tabla de protocolos en L1.
