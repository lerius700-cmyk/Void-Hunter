# 🏛️ VOID HUNTER — Project Identity

**Perfil SF/SM:** Lite
**Schema target:** `.synapse` 2.2.0 (acepta 2.1.0 legacy)
**Versión actual:** v1.8.0 (BLOQUE 74 — pipeline de sprites; línea v1.4.0 + GOLIATH + menú post-cinematica)
**Tipo:** CODE (Python + pygame 2.6, stdlib only + numpy para lowpass audio)
**Test count:** 2,886 pass + 1 fail pre-existente + 6 skipped (2,893 total)

---

## ¿Qué ES / Qué NO ES

**ES:** un shmup vertical 8-bit pixelart portrait 320×480 a 120 FPS, con 4 bosses (GOLIATH / HYDRA / PHANTOM / NEMESIS), modo roguelike con seed/RNG, formación Star Fox 64 + bezier paths, 24 SFX procedurales, 2 BGMs streaming, pausa con lowpass, selector de 5 naves × 5 animaciones × 8 frames, 4 videos cinemáticos (2 standalone 9:16 + 2 in-game), galería in-game de spritesheets + videos, **menú post-cinematica** (NEW GAME / BOSS TIME / BACKGROUND), **GOLIATH con el escudo medido sobre su placa** (brazo derecho, óvalo invisible, capa de calor + parpadeo, láser naranja grueso), **el fondo morado del "Asteroid Approach" de v1.4.0** (6 tiles en `Assets/background/tiles/act1/`) y un **pipeline de sprites** (BLOQUE 74) que hornea las anclas de GOLIATH en build time: `src/anim/` (manifiesto + medición + compositor) y `tools/sprite_pipeline/` (auditor + reparación). ~28.9K LOC en 92 archivos Python + ~25.3K LOC de tests en 104 archivos de test.

**NO ES:** un MMO, un roguelike 2D con vista top-down, un juego online, un servicio con backend, un proyecto que requiere Truth Anchors de runtime (puertos localhost, ss, pgrep). Es una app standalone pygame que se compila con PyInstaller.

**LÍNEA DE TRABAJO (importante):** esta rama es la **línea v1.4.0** (BLOQUE 71) + el trabajo de GOLIATH y el menú. **v1.4.0 NO tiene sistema de armas**: ni 4 tipos de arma, ni los 4 cuadros de slots en el HUD, ni remap de input de armas. `master` es otra línea (v1.6.3) con features que esta línea **no** tiene.

---

## 🏢 Mapa del Edificio

```
L1  CLAUDE.md            ← identidad + reglas globales (ESTE ARCHIVO)
L1.5 CONTEXT.md          ← Switch de contexto (ADUANA + silos + Token Budget)

L2  src/                 ← código fuente (28.9K LOC, 92 archivos, 15 sistemas)
L2  tests/               ← 2,887 tests pytest (104 archivos de test)
L2  Assets/              ← binarios (sprites, audio, galaxy panels, tiles, BGM, video)
L2  tools/               ← scripts de captura / debug / generación (incl. video_gen/, tiles/, sprite_pipeline/)
L2  build.spec           ← PyInstaller onefile
L2  main.py              ← entry point

L3  docs/arch/           ← arquitectura + roadmap + GDD
L3  docs/changelog/      ← changelog v1.x + raíz
L3  docs/bloques/        ← checklists de BLOQUE (mega + user prompts)
L3  docs/session-reports/← reportes de sesión
L3  docs/handoffs/       ← handoffs cross-session (cierre formal de BLOQUE)
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
| Videos cinemáticos | `Assets/video/{title,zoom}/frames/*.png` | No editar a mano — regenerar con `tools/video_gen/` | R (REFERENCE) |
| Sprite sheets | `Assets/sprites/player_ships/ship_*_spritesheet.png` | No editar a mano — regenerar con `tools/build_sprite_sheet.py` | R (REFERENCE) |
| Audio dev | `tools/*.{py,ps1,bat}` | Captura / debug / generación, no productiva | R (REFERENCE) |
| Video gen | `tools/video_gen/**` | Genera assets de video. No es productiva del juego | R (REFERENCE) |
| Manifiesto de animación | `Assets/sprites/bosses/*/manifest.toml` | Se edita **a mano**: es la spec del set (canvas, clips, tolerancias, reglas de detección). Lo valida `src/anim/manifest.py` | R (REFERENCE) |
| Anclas horneadas | `Assets/sprites/bosses/*/anchors.toml` | **Generado** por `python tools/sprite_pipeline/run.py <set> --fix`. NUNCA editar a mano | R (REFERENCE) |
| Pipeline de sprites | `tools/sprite_pipeline/**` | Auditor + reparación + generación de `anchors.toml`. Dev-only, no es productiva del juego | R (REFERENCE) |
| Builds | `dist/`, `build/` | Output PyInstaller, gitignored | S (SKIP) |
| Release artifacts | `release/` | Output deliverables (videos standalone, etc.), gitignored | S (SKIP) |
| Caché | `.mypy_cache/`, `.ruff_cache/`, `.pytest_cache/`, `__pycache__/` | Gitignored | S (SKIP) |

**Decisiones arquitectónicas no negociables:**

1. **No numpy/scipy en runtime del juego** (GDD §0). Excepción única documentada: `apply_lowpass_to_wav` para el lowpass del pause (user-explicit, BLOQUE 58.14).
2. **Coordenadas internas 320×480** portrait; el escalado a display lo hace `Game._present()`. No hardcodear tamaños de ventana.
3. **Default mode = `--roguelike`** (BLOQUE 58); testing = `--patterns 1`. Mantener consistencia.
4. **Commits con prefijo de BLOQUE**: `feat: BLOQUE N` / `fix: BLOQUE N` / `chore: BLOQUE N`.
5. **Sub-boss (BLOQUE 50) = "Wolfen" dart**, NO un boss real. Los 4 bosses reales son GOLIATH/HYDRA/PHANTOM/NEMESIS.
6. **"minijefe" = sub-boss** en el español del usuario. "canción" = BGM de 5:30. GOLIATH aparece al menos a los 3:40 (220s).
7. **La base de esta línea es v1.4.0 (BLOQUE 71).** Una feature de BLOQUE 72+ entra **sólo por pedido explícito del usuario**, nunca porque "master la tenía". `master` es otra línea con otras features: portarlas "para no perder nada" mete features que la base no tiene (y puede **borrar** features de la base — BLOQUE 73 Fase A eliminaba el láser de carga del LMB de v1.4.0). Referencia: el commit `1c9170d` (sistema de 4 armas) se revirtió en `8634b17`.
8. **El escudo de GOLIATH se MIDE, no se posiciona a ojo.** `scenes.get_sprite_shield_ellipse()` lee la silueta real de la placa del brazo derecho por frame. Visual, hitbox y origen del láser leen **la misma** medición (`_goliath_shield_ellipse`): no pueden desincronizarse. Constantes: `GOLIATH_SHIELD_DX/DY` = ajuste del centro medido (0/3), `RX/RY/R` = half-size de fallback (11/17/11).
9. **El óvalo del escudo es INVISIBLE**: no se dibujan el cuerpo, el borde ni el remache. Solo la **capa de calor** (roja al primer impacto, se calienta al cargar) y la **capa de impacto** (parpadeo de 0.30 s por disparo). `GOLIATH_SHIELD_HIT_FLASH_S = 0.30`.
10. **`build.spec` bundlea la raíz de `Assets/` con un glob**, no con una lista a mano. Un asset suelto en la raíz (ej. `imagen fondo del juego.jpg`, el fondo pintado del boss fight) se quedaba afuera del `.exe` y hacía que la pelea se viera **negra con estrellas**. Cubierto por `tests/test_build_spec_assets.py`.
11. **Los tiles del "Asteroid Approach"** (`Assets/background/tiles/act1/`, 6 PNG, 78 KB) están commiteados: nunca se commitearon y por eso v1.4.0 crasheaba al arrancar. No regenerar con AI — son los originales, pintados a mano.
12. **El runtime NO mide el arte (BLOQUE 74).** La medición de las features de cada frame (ojo, placa del escudo, silueta) se hace **en build time** y se hornea en `Assets/sprites/bosses/<set>/anchors.toml`; el juego solo lee esa tabla. El manifiesto (`manifest.toml`) es la **spec** del set y se edita a mano: canvas, clips (id ↔ dir), fps, tolerancias y reglas de detección. `src/anim/` no importa `tools/`; `tools/sprite_pipeline/` sí importa `src/anim/`.
13. **Un solo umbral para el re-pad.** `CORTADO_MARGIN` (`src/anim/measure.py`) es el margen que el auditor marca por debajo y el que la reparación persigue: dos umbrales distintos dejaban frames que el auditor marcaba y la reparación no podía arreglar (para siempre).

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
- El título de la ventana dice `VOID HUNTER v1.4.0 (BLOQUE 71)` (`src/core/settings.py:WINDOW_TITLE`). Es el rótulo de la base; la release va por tag de git, no por ese string.

**DEBE preguntar:**

- "¿Querés que commitee?" antes de cualquier commit (BLOQUE 58.14 user feedback explícito).
- Cambios visuales antes de "listo" (user confirms con frame PNG explícito).
- Cambios al `.exe` (PyInstaller) — preguntar antes de rebuildear.
- Cualquier cambio que toque audio / music — preguntar antes de tocar la implementación.
- **Antes de portar una feature que existe en `master` pero no en la base v1.4.0** — preguntar si entra. (El usuario corrigió esto el 2026-10-25: "la version 1.4 no tenia armas extra... nada de armas nuevas").

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
├── src/                        ← L2 código (92 archivos, 28.9K LOC)
│   ├── core/                   ← game loop, settings, scene_manager
│   ├── audio/                  ← synth + music (BLOQUE 58.14)
│   ├── systems/                ← parallax, wave_manager, bezier, tile_manager, etc.
│   ├── entities/               ← player, enemy, boss, projectile
│   ├── ui/                     ← scenes, gameplay_runtime, HUD, video_player
│   ├── anim/                   ← manifiesto + medición + compositor de animaciones (BLOQUE 74)
│   ├── movement/               ← formation, paths
│   ├── roguelike/              ← seed, level_gen, form_gen, replay
│   └── utils/                  ← palette, easing
│
├── tests/                      ← L2 (2,887 tests, BLOQUE 1-74)
│
├── Assets/                     ← L2 binarios
│   ├── background/             ← galaxy_panel_*.png, galaxy_sprite_*.png
│   │   └── tiles/act1/         ← 6 tiles del "Asteroid Approach" (BLOQUE 64)
│   ├── sprites/                ← ship sprites, enemy sprites, GOLIATH frames, VFX
│   │   └── bosses/goliath/     ← 60 frames + manifest.toml (spec) + anchors.toml (horneado)
│   ├── *.wav                   ← BGM + voice clips
│   └── keep kept - Lerius - soundtrack gameplay_lp600.wav
│
├── tools/                      ← L2 dev-only (no productiva)
│   ├── capture/                ← scripts de screenshot
│   ├── sprite_pipeline/        ← pipeline de sprites: audit.py, run.py, repair.py (BLOQUE 74)
│   ├── tiles/                  ← pipeline del fondo Asteroid Approach (generate_tiles.py + ai_gen/)
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
│   ├── handoffs/               ← handoffs cross-session
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
| **sf-sm-doctor** (System Folder + Synapse Method) | Auditar / remediar estructura del proyecto | `C:\Users\Lerius\.minimax\skills\sf-sm-doctor\` |
| **sf-sm-audit** (alias de sf-sm-doctor) | Auditar compliance sin remediar | `C:\Users\Lerius\.minimax\skills\sf-sm-audit\` |
| **gstack-review** | Review pre-landing del diff contra la base | `C:\Users\Lerius\.minimax\skills\gstack-review\` |
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
| Líneas de código (src/) | 28953 | `python -c "import pathlib; print(sum(len(p.read_text(encoding='utf-8',errors='ignore').splitlines()) for p in pathlib.Path('src').rglob('*.py')))"` |
| Archivos Python (src/) | 92 | `Get-ChildItem -Recurse -Filter *.py src/ \| Measure-Object` |
| Tests (tests/) | 2.886 pass + 1 fail pre-existente + 6 skipped (2.893 total) | `python -m pytest tests/ --tb=no` |
| LOC tests/ | 25552 | `python -c "import pathlib; print(sum(len(p.read_text(encoding='utf-8',errors='ignore').splitlines()) for p in pathlib.Path('tests').rglob('*.py')))"` |
| Silos SF+SM | 9 (Lite) | `Get-ChildItem docs -Directory \| Measure-Object` |
| Compliance SF | 7/7 (Lite perfil) | `audit_sf_sm.py --perfil=lite` (exit 0) |
| Versión | v1.8.0 (BLOQUE 74 — pipeline de sprites) | `git log --oneline -1` |
| Rama | bloquec-67-goliath-port | `git branch --show-current` |
| Remote | github.com/lerius700-cmyk/Void-Hunter | `git remote -v` |
| Build .exe | **reconstruido** para v1.8.0 (278.0 MB) en `dist/void-hunter.exe` — el path congelado (`<_MEIPASS>/Assets/sprites/bosses`) verificado con el manifest y los anchors dentro del bundle | `Get-Item ../bloquec-67-goliath-port/dist/void-hunter.exe` |
| Tiles Asteroid Approach | 6 PNG (320×480) en `Assets/background/tiles/act1/` | `Get-ChildItem Assets/background/tiles/act1/*.png` |
| Frames GOLIATH | 60 PNG (6 anim × 10) en `Assets/sprites/bosses/goliath/` | `Get-ChildItem Assets/sprites/bosses/goliath/*/frame_*.png` |
| Manifiesto + anclas de GOLIATH | 1 `manifest.toml` (spec) + 1 `anchors.toml` (horneado) | `Get-ChildItem Assets/sprites/bosses/goliath/*.toml` |
| Videos cinemáticos (standalone) | 4 mp4 (1080×1920 + 540×960) en `release/videos/` | `Get-ChildItem release/videos/*.mp4` |
| Videos cinemáticos (in-game) | 660 PNG frames en `Assets/video/{title,zoom}/frames/` | `Get-ChildItem Assets/video/*/frames/frame_*.png` |
| Sprite sheets (in-game) | 5 PNGs en `Assets/sprites/player_ships/ship_*_spritesheet.png` | `Get-ChildItem Assets/sprites/player_ships/*_spritesheet.png` |

> **Nota:** el único test que falla es **pre-existente**:
> `tests/test_paths.py::test_paths_no_star_shapes`, una aserción real de
> geometría del LissajousPath. No es una regresión de BLOQUE 74.
>
> Los 8 tests que fallaban en la línea v1.7.2 (5 de `test_sub_boss_*` + 2
> de `test_asteroid_sprites.py`) eran contaminación de estado entre tests:
> el fixture `tests/conftest.py` los arregló, así que hoy fallan 0 de 8.
>
> Esta rama es la **línea v1.4.0** (BLOQUE 71) + BLOQUE 67 + BLOQUE 74.
> `master` es otra línea (v1.6.3) y tiene features que esta línea no tiene
> — ver la decisión 7 en "Decisiones arquitectónicas no negociables".
>
> **Regla:** si una métrica cambia, regenerar este bloque con el comando de la columna "Fuente". NUNCA editar a mano.


---

## Historial de cambios estructurales (post-SF+SM)

- **2026-08-17 (remediación inicial)** — sf-sm-doctor primera pasada: 1/7 → 7/7. Tree Integrity fixed (CHANGELOG.md movido a `docs/changelog/`), 7 silos creados, Token Budget L/S/R presente, `.synapse` schema 2.2.0 en root.
- **2026-08-17 (deep audit + fix)** — sf-sm-doctor deep audit reveló drift entre documentos y realidad. Fixes aplicados:
  - C-1: 6 archivos físicos movidos de `docs/` raíz a subcarpetas silo (`docs/arch/`, `docs/bloques/`, `docs/session-reports/`, `docs/changelog/`).
  - C-2: STATUS:GENERATED regenerado con métricas reales (22,981 LOC, 75 files en `src/`, 14,485 LOC en `tests/`).
  - C-3: `sre-protocol` + `synapse-deep` agregados a la tabla de protocolos en L1.
- **2026-08-25 (BLOQUE 58.59 + 58.60 — videos + gallery)** — Cinemáticos pixel-art integrados:
  - 4 videos: V1-S/V2-S standalone 9:16 mp4 (`release/videos/`) + V1-G/V2-G in-game 240×360 PNG (`Assets/video/`)
  - `src/ui/video_player.py` (sprite-sheet player, 80 LOC)
  - `src/ui/cinematic_scene.py` (nuevo GameState.CINEMATIC entre TITLE y ACT_INTRO)
  - `src/ui/gallery_scene.py` (2 nuevas scenes: GALLERY_SPRITE + GALLERY_VIDEO, hotkeys S/V en title)
  - `tools/video_gen/` (pipeline procedural con PIL: paleta, pixel_grid, effects, ship_overlay, composition, pixel_font)
  - `tools/build_sprite_sheet.py` (genera 5 spritesheets desde `ship_NN_base.png`)
  - 14 ships_NN_spritesheet.png (5 ships × animaciones)
  - 45 nuevos tests pytest (test_video_player, test_video_assets, test_cinematic_scene, test_video_mp4_export, test_gallery_scene)
  - 660 frames PNG bundleados en `Assets/video/`
  - STATUS:GENERATED regenerado: 24,757 LOC / 79 files en `src/`, 1,630 tests pass
  - `docs/superpowers/specs/2026-08-25-void-hunter-videos-design.md` (spec de la feature)
- **2026-10-25 (BLOQUE 67 — línea v1.4.0 + GOLIATH + menú post-cinematica, v1.7.0 → v1.7.2)** — Partiendo de `d70b8da` (v1.4.0, BLOQUE 71) en el worktree `.worktrees/bloquec-67-goliath-port`:
  - **GOLIATH (BLOQUE 66)**: 60 frames restaurados de `ac53596` + el re-padding de `6c71e1b`; el escudo se **mide** sobre la silueta de la placa del brazo derecho (`scenes.get_sprite_shield_ellipse()`), el **óvalo es invisible** y solo se ven la capa de calor (roja al primer impacto) y el parpadeo de impacto; láser del escudo **naranja y grueso**; el **láser del ojo sale del ojo** (y lo sigue cuando GOLIATH se mueve).
  - **Menú post-cinematica (BLOQUE 73.7)**: `GameState.MENU` + `MainMenuScene` (NEW GAME / BOSS TIME / BACKGROUND) + `Game.bg_mode`.
  - **Fondo ASTEROID NEBULA real de v1.4.0**: los 6 tiles del "Asteroid Approach" (BLOQUE 64) **recuperados** de dos copias locales del repo (MD5 idéntico) y commiteados (78 KB). Nunca se commitearon, por eso v1.4.0 crasheaba al arrancar.
  - **BLOQUE 73.1**: `TileManager` degrada graceful sin los tiles (v1.4.0 crasheaba al arrancar: `FileNotFoundError`).
  - **`--boss` deja de ser stub**: camina `TITLE → ACT_INTRO → GAMEPLAY → BOSS_INTRO → BOSS_FIGHT`.
  - **`build.spec`**: la raíz de `Assets/` se bundlea con un **glob**. `imagen fondo del juego.jpg` (el fondo pintado del boss fight) no entraba al `.exe` y la pelea se veía **negra con estrellas**. Cubierto por `tests/test_build_spec_assets.py`.
  - **Revertido**: el sistema de 4 armas (BLOQUE 72 + 73 Fase A/B/C) — la base v1.4.0 **no tiene armas** (ni 4 tipos, ni los 4 cuadros de slots, ni el remap de input) y el port además arrastraba `d43f7be`, que **borraba** el láser de carga del LMB de v1.4.0.
  - **Releases**: v1.7.0 (`.exe` sin el fondo del boss fight) → v1.7.1 (con el sistema de armas de más) → **v1.7.2 (la correcta)**.
  - **Handoff**: `docs/handoffs/HANDOFF-GOLIATH-PORT-V140-2026-10-23.md`.
  - STATUS:GENERATED regenerado: 27,694 LOC / 86 files en `src/`, 22,773 LOC en `tests/`, 2,787 tests, 9 silos.
- **2026-10-27 (BLOQUE 74 — pipeline de sprites, sin bump de versión)** — Worktree `.worktrees/bloquec-74-sprite-pipeline`, sobre la línea v1.7.2. El runtime **deja de medir el arte**: la medición se hace en build time y se hornea.
  - **Nuevo subsistema `src/anim/`** (6 archivos): `manifest.py` (manifiesto declarativo + validación), `measure.py` (medición por píxel: silueta, centroide, elipse creíble), `parts.py` (reglas de detección declaradas), `anchors.py` (lector de la tabla horneada), `clip.py` (compositor: manifiesto + anclas + caché de frames), `__init__.py`.
  - **Nuevo tool `tools/sprite_pipeline/`**: `audit.py` (7 estados: COLAPSADO / CORTADO / LADO_EQUIVOCADO / FIRMA_AMBIGUA / AUSENTE / FUERA_DE_RANGO / ESCALADO), `repair.py` (reparaciones deterministas e idempotentes), `run.py` (validate → audit → repair → re-audit → anchors → report).
  - **`Assets/sprites/bosses/goliath/manifest.toml`** (spec, editada a mano) + **`anchors.toml`** (generado): el canvas, los 6 clips (id ↔ dir), los fps, las tolerancias y las reglas de detección viven en el manifiesto; la medición de los 60 frames vive en la tabla horneada.
  - **El runtime lee las anclas horneadas** (`src/ui/scenes.py`): el ojo, la placa del escudo y el centroide son lookups, no escaneos de píxeles (3.9 ms por frame → un lookup).
  - **Umbral único `CORTADO_MARGIN`** (`src/anim/measure.py`): el auditor marca por debajo y la reparación persigue exactamente el mismo valor. Con dos umbrales, un frame marcado podía no ser reparable nunca y `run.py --fix` exiting 1 para siempre.
  - **El camino congelado se resuelve perezoso**: `src/anim/manifest.py` no calcula la raíz del repo al importar, y el set se parsea una sola vez (`loaded_set`).
  - **La ruta del sprite y el canvas salen del manifiesto**: `Boss.animation_path` usa `clip.dir` y el runtime usa `meta.canvas` — el canvas es una propiedad del set, no una constante del juego.
  - **Auditoría del branch completo**: "Ready to merge: With fixes" (0 Critical, 3 Important, 8 Minor). Los Important y los Minor de esta ola están cerrados: umbral único, documentación del BLOQUE ausente, clip `"idle"` inexistente en `tools/capture/capture_goliath_phase1.py` y `tests/test_goliath_sprite.py`, memoización de `_clip_id_for_dir`, directorio del clip desde el manifiesto, canvas desde el manifiesto, docstring obsoleto, test del pipeline contra el árbol real y `ROOT` calculado al importar.
  - **Release v1.8.0**: el `.exe` se reconstruyó sobre el tag `v1.8.0` (278 MB) y el path congelado (`<_MEIPASS>/Assets/sprites/bosses`) quedó verificado con el `manifest.toml` y el `anchors.toml` dentro del bundle. La versión SÍ se bumpea a v1.8.0 en esta release.
  - **Handoff**: `docs/handoffs/HANDOFF-SPRITE-PIPELINE-2026-10-27.md`. **Session report**: `docs/session-reports/SESSION_REPORT_BLOQUE_74.md`.
  - STATUS:GENERATED regenerado: 28,953 LOC / 92 files en `src/`, 25,552 LOC en `tests/`, 2,893 tests, 9 silos.
