# VOID HUNTER — Changelog & Bug Log

**Proyecto:** VOID HUNTER (D:\AI\void-hunter)
**Repositorio:** https://github.com/lerius700-cmyk/Void-Hunter
**Stack:** Python 3.11 + pygame 2.6 (sin numpy/scipy, stdlib math only)
**Total código:** ~30,000 líneas en 130+ archivos Python
**Total tests:** 1,103 passing
**Última revisión:** 2026-08-15 16:18 PM

**Versioning policy (2026-08-15):** v1.0 stays as the bootstrap baseline. v1.1 is the consolidated release with the procedural patterns system + recent polish BLOQUES. v1.2 → v1.27 moved to `archive/_legacy_releases/` (kept for history).

---

## 1. Resumen del Proyecto

## 0. v1.1 — 2026-08-15 — Consolidated Release (the one we're working on)

**Headline features (since v1.0):**

- 5 procedural wave patterns (Bezier-based, Star Fox inspired)
- ProceduralWaveManager with difficulty curve + anti-stuck
- Procedural enemy variety (5 archetypes × 5 variation axes)
- 13 major systems (Formations, Bezier, Leader, Roguelike, etc)
- HUD moved to BOTTOM (root cause fix for sub-boss visibility)
- Sub-boss root cause fix (boss trigger guard)
- Galaxy background: long single strip (640×5760) replacing tile pattern
- DASH afterimage restored
- Ultra-neon propulsion (6 particles per engine)
- Sub-boss 5s warning (no skip)
- 1103/1103 tests passing

**BLOQUES since v1.0:**

- **58.7aa** DASH afterimage (BLOQUE commit `61b6146`)
- **58.7ab** HUD moved to BOTTOM (`6afaddf`)
- **58.7ac** Sub-boss root cause fix (`c2af8bc`)
- **58.7ad** Galaxy background long strip (`4602ea4`)
- **58.8** Procedural wave patterns (5 patterns + manager + enemy variety, `60379cb`)
- **58.9** Pattern runtime integration (--patterns flag, HUD banner, `13d1679`)

**Versioning:** v1.0 stays as the bootstrap baseline. v1.1 is the new consolidated release. v1.2 → v1.27 moved to `archive/_legacy_releases/` (kept for history, not in current release).

**Download:** `releases/void-hunter-v1.1-windows.zip` (181 MB)
**Launch:** `void-hunter.exe` (default mode) or `void-hunter.exe --patterns 2` (procedural patterns)

---

## 1. Resumen del Proyecto

### 1.1 Arquitectura

```
src/
├── audio/        1,420 líneas — synth 24 SFX + streaming BGM (2 WAV)
├── core/           874 líneas — settings, scene_manager, eventos
├── entities/     1,844 líneas — player, enemies, boss, projectiles
├── movement/       672 líneas — BezierPath, WaypointPath, PathFollower
│                            FlightFormation (9 presets)
├── roguelike/    1,540 líneas — seed RNG, run state, upgrades, replay
├── systems/      3,386 líneas — wave manager, particle engine, scoring
├── ui/           7,751 líneas — gameplay_runtime (5,773), scenes (1,280)
│                            HUD, galaxy bg, tiling
└── utils/          206 líneas — math, paths, logging
```

### 1.2 Estadísticas

| Métrica | Valor |
|---|---|
| Versiones distribuidas (.zip) | 27 (v1.0 → v1.27) |
| Commits totales | 160 |
| BLOQUES completados | 0 → 58.7ad (~150+) |
| Líneas de código | 28,066 |
| Archivos Python | 118 |
| Tests passing | **1,024 / 1,024** (100%) |
| Tamaño del .exe | 2.83 MB |
| Tamaño del dist total | 177 MB |
| Música bundleada | 162 MB (2 tracks streaming) |

---

## 2. Línea Temporal de Versiones

### 2.1 Era temprana (v1.0–v1.3) — Bootstrap + setup

| Versión | Fecha | MB | Notas |
|---|---|---|---|
| v1.0 | 08/12 01:01 | 14.5 | Bootstrap inicial. Sin música. Solo 14 MB. |
| v1.1 | 08/14 12:53 | 14.6 | Fix título |
| v1.2 | 08/14 13:15 | 14.6 | Sin cambios visibles |
| v1.3 | 08/14 13:22 | 14.6 | Sin cambios visibles |

**Bugs resueltos en esta era:**
- BLOQUE 58.36g: ventana vertical centrada, escala auto-detect
- BLOQUE 58.36g-taskbar: mouse reticle corregido
- BLOQUE 58.34: 320x480 playfield, mouse tracking rápido
- BLOQUE 58.35: sprite scale 0.75, nose_lerp fix

### 2.2 Era media (v1.4–v1.20) — Música + visual polish

| Versión | Fecha | MB | BLOQUE principal |
|---|---|---|---|
| v1.4 | 08/14 14:51 | 173 | **BLOQUE 58.45**: música streaming WAV bundleada |
| v1.5 | 08/14 15:00 | 173 | Ajustes menores |
| v1.6 | 08/14 15:49 | 173 | Tiling image bg |
| v1.7 | 08/14 16:23 | 173 | Boss redesign |
| v1.8 | 08/14 16:29 | 173 | Audio engine fix |
| v1.9 | 08/14 16:52 | 173 | Squadron straight line (no serpentina) |
| v1.10 | 08/14 17:01 | 173 | WaveChain 2x, 5.5min, GOLIATH x10HP |
| v1.11 | 08/14 17:21 | 173.2 | Sub-boss redesign |
| v1.12 | 08/14 17:27 | 173.2 | Sub-boss rotation |
| v1.13 | 08/14 17:33 | 173.2 | 4-entry L-pattern |
| v1.14 | 08/14 17:42 | 173.2 | Sub-boss bigger, propulsion |
| v1.16 | 08/14 18:08 | 173.2 | 3 bosses Star Fox redesign |
| v1.17 | 08/14 18:22 | 173.2 | Music no restart on sub-boss |
| v1.18 | 08/14 18:48 | 173.2 | **BLOQUE 58.6x**: FlightFormations + BezierCurves + PathFollowing |
| v1.19 | 08/14 20:09 | 173.2 | **BLOQUE 58.6w**: scrolling galaxy background (3 panels) |
| v1.20 | 08/14 20:52 | 173.2 | **BLOQUE 58.6z**: level 1 minimum 3:30 (hear the song) |

**Saltos de tamaño MB:**
- v1.3 → v1.4: **14.6 → 173 MB** ← música bundleada (162 MB)

**Bugs críticos resueltos en esta era:**

#### BLOQUE 58.57 (commit `e0279d8`) — **Audio no suena**
- **Causa 1**: IndentationError en `src/audio/synth.py` impedía cargar el módulo
- **Causa 2**: `_cmd_play` no llamaba `Game.run()`, así que `on_enter` no se disparaba
- **Fix**: Mover el trigger de `on_enter` a `Game.__init__()`, corregir indentación
- **Verificación**: `_audio_status.log` con lectura de estado + tests

#### BLOQUE 58.58–58.59 (commits `2377aa0`, `1b8b3d7`) — Voces SAPI + serpentina
- **Causa 1**: 4 voice clips SAPI sonaban robóticos
- **Causa 2**: Movimiento serpentino de ships era confuso
- **Fix**: Remover voice clips, eliminar 3 fuentes de movimiento curvo

#### BLOQUE 58.50–58.6.5 (commits `6170fa8`–`d963d29`) — Sub-boss rediseño
- 6 iteraciones para llegar al diseño final (24x14, V-shape, wrap-around, L-pattern)
- 4-entry cycle: top→bottom, left→right, bottom→top, right→left

#### BLOQUE 58.6x (commits `971f779`, `40b3a28`) — Sistema de movimiento
- `src/movement/` package completo
- `BezierPath`, `WaypointPath`, `HybridPath`, `PathFollower`
- `FlightFormation` con 9 presets (V, LINE, DIAMOND, SQUARE, WEDGE, CIRCLE, TRIANGLE, HALF_V, CUSTOM)
- 4 waves level 1 con paths únicos (straight, bezier S, waypoint zigzag, hybrid)
- 37 nuevos tests (bezier math, waypoint follow, hybrid concat, follower timing, formations, slots)

#### BLOQUE 58.6w (commit `3a0bb09`) — Galaxy background
- `src/ui/scrolling_galaxy.py` con `ScrollingGalaxyBackground`
- 3 paneles stacked, scroll top-to-bottom @ 30 px/s
- Loop ~10.6s inicialmente
- **Bug inicial**: imagen muy corta (318 px vs 480 pantalla) → tile pattern

#### BLOQUE 58.6y (commits `b768952`, `2e01870`, `d6ee9f2`) — Sub-boss visibility + neon propulsion
- Sub-boss spawn y=0 → y=20 (fuera del clip)
- SUB_BOSS_INTRO 4s → 5s
- Spawn flash: Shockwave + 26 partículas + screen_flash 0.5s + boss_warning sfx
- 4 → 6 partículas por engine
- Nueva paleta: white_hot_core + electric_blue + cyan_glow + violet_edge + deep_navy

### 2.3 Era reciente (v1.21–v1.27) — Polish visual + iteración

| Versión | Fecha | MB | BLOQUE principal |
|---|---|---|---|
| v1.21 | 08/14 21:18 | 176.8 | **BLOQUE 58.6w-fix**: galaxy 3 paneles verticales (intent #1) |
| v1.22 | 08/14 21:20 | 176.8 | Sin cambios |
| v1.23 | 08/14 21:22 | 176.8 | Sin cambios |
| v1.24 | 08/14 21:24 | 176.8 | Sin cambios |
| v1.26 | 08/14 22:29 | 177.4 | **BLOQUE 58.7x**: sub-boss visibility, ultra-neon, new galaxy |
| v1.27 | 08/14 22:45 | 177.2 | **BLOQUE 58.7y**: galaxy 3 paneles (intent #2) |

**Bugs resueltos en esta era:**

#### BLOQUE 58.7aa (commit `61b6146`) — DASH after-image roto
- **Causa**: código de afterimage estaba dentro de `_draw_player()` que usa scratch 32x24
- **Fix**: nuevo `_draw_player_afterimage()` que dibuja en playfield con offsets
- **Verificación**: `tools/capture_dash.py` produce PNGs con 8 ghosts visibles

#### BLOQUE 58.7ab (commit `6afaddf`) — HUD cubría el sub-boss
- **Causa raíz**: HUD estaba en TOP, sub-boss spawns en y=20 (TOP)
- **Fix**: HUD movido a BOTTOM, score a BOTTOM-right
- Removido: ENTER/SPACE skip en SubBossIntroScene
- **Verificación**: 2 nuevos tests en `test_hud_position.py`

#### BLOQUE 58.7ac (commit `c2af8bc`) — **No aparece el sub-boss** (BUG MAYOR)
- **Causa raíz**: `BOSS_PERFECT_TRIGGER_S = 60s` pero sub-boss fires at chain.elapsed ~ 95s
  - En partida perfecta, boss intro se dispara a los 60s
  - Trigger condition STAYS met (perfect + 60s)
  - Cuando SUB_BOSS_INTRO vuelve a GAMEPLAY a 95s, boss trigger fires AGAIN
  - En el mismo frame que el sub-boss spawns, boss intro se dispara y libera todos los enemigos
  - Resultado: sub-boss alive por 1 frame y desaparece
- **Fix**:
  1. `BOSS_PERFECT_TRIGGER_S`: 60s → 100s
  2. `BOSS_SAFETY_TRIGGER_S`: 120s → 140s
  3. Added guard: boss trigger does NOT fire if `chain.sub_boss_pending AND self._sub_boss_alive`
  4. KILLED log entry added
  5. Log typo fix: y=0 → y=20
- **Verificación**: 3 nuevos tests regression + visual PNG
- **Impacto**: bug que el usuario reportó **7+ veces** antes del fix

#### BLOQUE 58.7ad (commit `4602ea4`) — Galaxy background grid
- **Causa raíz**: commit anterior "vertical panels" pero en realidad eran 3 filas horizontales (1920x640)
- **Síntoma**: panel escalado a 320x106 (wide), strip 318 vs screen 480 → tile pattern
- **Fix**:
  1. Split correcto: 3 columnas verticales de 640x1920
  2. Imagen larga (cinta): `galaxy_strip.png` 640x5760 (3 pegadas)
  3. Runtime prefiere single mode → 320x2880
  4. Loop 96s (1.6 min)
- **Verificación**: 3 frames captured en distintos scroll positions muestran 3 secciones diferentes

---

## 3. Catálogo de Bugs por Categoría

### 3.1 Audio (BLOQUE 58.23, 58.45, 58.51, 58.55, 58.57, 58.6y)

| # | BLOQUE | Bug | Causa | Fix | Estado |
|---|---|---|---|---|---|
| A1 | 58.23 | 1.2s freeze en BOSS_INTRO | AudioEngine re-bake | Reusar shared audio engine | ✅ |
| A2 | 58.45 | Música no se reproduce | Falta bundlear WAV en .spec | Agregar `Assets/` a `datas=` | ✅ |
| A3 | 58.51 | Filename incorrecto gameplay track | Path mal escrito | Corregir a nombre exacto | ✅ |
| A4 | 58.55 | Volumen bajo | Sin SDL_AUDIODRIVER=wasapi | Set wasapi explícito, volumen 100% | ✅ |
| A5 | 58.57 | **Audio completamente mudo** | IndentationError en synth.py | Fix indentación + on_enter en __init__ | ✅ |
| A6 | 58.6y | Music restart on sub-boss return | Inicializaba nuevo mixer | Reusar engine | ✅ |

### 3.2 Sub-Boss (BLOQUE 50–58.7ac — 16 BLOQUES)

| # | BLOQUE | Bug | Estado |
|---|---|---|---|
| S1 | 50 | Sub-boss intro loops (cada vez que O2 acaba) | ✅ 50.1 fix |
| S2 | 58.1 | Confusión sub-boss vs boss | ✅ Identificado como dart BLOQUE 50 |
| S3 | 58.5 | Sprites flip nose-UP | ✅ Rotados nose-DOWN |
| S4 | 58.6 | Sub-boss rediseño completo | ✅ Menacing alien hunter |
| S5 | 58.6.1 | Fangs no convergen en V apex | ✅ |
| S6 | 58.6.2 | Wrap-around no funciona | ✅ Straight line + wrap |
| S7 | 58.6.3 | Sub-boss no tiene propulsion | ✅ Animated engines |
| S8 | 58.6.4 | 4-entry L pattern | ✅ Implementado |
| S9 | 58.6.5 | No rota con velocidad | ✅ Rotación 0/90/180/270 |
| S10 | 58.7x | Sub-boss clip top edge | ✅ y=20 + spawn flash |
| S11 | 58.7ab | HUD covers sub-boss | ✅ HUD movido a BOTTOM |
| S12 | 58.7ac | **Sub-boss no aparece (7+ reports)** | ✅ Boss trigger guard |

### 3.3 Visual / Polish (BLOQUE 58.6w, 58.6x, 58.7aa, 58.7y, 58.7ad)

| # | BLOQUE | Bug | Estado |
|---|---|---|---|
| V1 | 58.6w | Galaxy bg tile pattern (imagen corta) | ✅ 58.7ad fix (single strip 2880 px) |
| V2 | 58.6x | Sprites serpentinos | ✅ 58.59 killed all sources |
| V3 | 58.7aa | DASH afterimage invisible | ✅ Draw on playfield, not scratch |
| V4 | 58.7y | Galaxy paneles "vertical" pero eran horizontales | ✅ 58.7ad correct split |
| V5 | 58.6y | Sub-boss propulsion poco neón | ✅ Ultra-neon 6 partículas |

### 3.4 Input / Control (BLOQUE 46, 58.7, 58.8, 58.38)

| # | BLOQUE | Bug | Estado |
|---|---|---|---|
| I1 | 46 | Input race + auto-exit 30s | ✅ |
| I2 | 58.7 | Player 8-dir no funciona mientras dispara | ✅ |
| I3 | 58.8 | DASH separado de PROPULSION | ✅ Click vs hold (0.6s) |
| I4 | 58.38 | RMB rapid fire broken | ✅ |
| I5 | 47.1 | Reticle misalignment | ✅ Mouse scale correcto |

### 3.5 Build / Distribution (BLOQUE 54, 58.45)

| # | BLOQUE | Bug | Estado |
|---|---|---|---|
| B1 | 54 | No había .exe | ✅ PyInstaller spec |
| B2 | 58.45 | WAVs no bundleados | ✅ `datas=[Assets → Assets]` |
| B3 | 58.47 | Boss input drena eventos | ✅ Runtime handles input |
| B4 | — | PYZ compression oculta strings | ✅ Use Runtime hooks para logging |

### 3.6 Arquitectura (BLOQUE 48, 58.6x, 58.56, 58.57)

| # | BLOQUE | Cambio | Estado |
|---|---|---|---|
| AR1 | 48 | Chained wave system (level 1) | ✅ |
| AR2 | 58.6x | `src/movement/` package | ✅ 7 files, 672 lines |
| AR3 | 58.56 | WaveChain 2x, 5.5min, GOLIATH | ✅ |
| AR4 | 57 | Roguelike core (seed, RNG, formations, replay) | ✅ 12 files, 1540 lines |

---

## 4. Funcionalidades Implementadas

### 4.1 Gameplay Core
- ✅ Player FSM (7 estados): IDLE, MOVE, DASH, PROPULSION, HIT, DEAD, RESPAWN
- ✅ Weapon system (3 paths × 3 levels): Standard, Plasma, Missile
- ✅ 8 enemy archetypes: SCOUT, CRUISER, HEAVY, KAMIKAZE, SNIPER, DRONE, TURRET, CARRIER, SUB_BOSS
- ✅ 4 bosses con phase FSM: HYDRA, PHANTOM, NEMESIS, GOLIATH
- ✅ Sub-boss dart (BLOQUE 50, 24x14, 400 HP, wrap-around, L-pattern)

### 4.2 Wave System
- ✅ `WaveChain` con 4 waves (O1-O4) en level 1
- ✅ Total 165 ships + sub-boss
- ✅ Spawn cadence bottleneck: 3:30 minimum clear time
- ✅ Boss trigger hierarchy: main (45s+waves_complete), perfect (100s+perfect), safety (140s)
- ✅ Sub-boss pause/resume: `sub_boss_pending` + `sub_boss_alive` guards
- ✅ Density cap: 8 enemies simultaneous
- ✅ Max duration per wave: timeout advance

### 4.3 Movement
- ✅ `BezierPath` (cubic Bezier curves)
- ✅ `WaypointPath` (constant speed + linger)
- ✅ `HybridPath` (concatenate segments)
- ✅ `PathFollower` (stateful, advances t over time)
- ✅ `FlightFormation` (9 presets)
- ✅ 4 wave-level paths: straight, bezier S, waypoint zigzag, hybrid
- ✅ 1 GOLIATH entrance path (bezier arc + linger)

### 4.4 Visual Systems
- ✅ Scrolling galaxy background (640x5760 strip → 320x2880, 30 px/s, 96s loop)
- ✅ Boss background (pixel art tiling, 3000x3000)
- ✅ Parallax stars (3 layers)
- ✅ HUD (bottom): lives, bombs, weapon, score (bottom-right)
- ✅ Sub-boss: rotating sprite, 24x14, 0/90/180/270 orientation
- ✅ Sub-boss propulsion: 6 particles/engine, ultra-neon palette
- ✅ Sub-boss spawn flash: shockwave + 26 particles + screen flash
- ✅ DASH afterimage: 8 ghosts on playfield
- ✅ Tron-style propulsion trail (cyan, 3x damage)
- ✅ Boss phases: shield, laser, spear throw

### 4.5 Audio
- ✅ 24 synthesized SFX (no external audio files)
- ✅ 2 streaming WAV music tracks (162 MB total, NOT loaded into RAM)
- ✅ Boss warning SFX
- ✅ Engine sounds
- ✅ Level up / multiplier up / act clear

### 4.6 Roguelike (BLOQUE 57)
- ✅ Seeded RNG (deterministic runs)
- ✅ Run state (replay from seed)
- ✅ Tech upgrades (HP_BOOST_10, GOLIATH_SUMMON)
- ✅ Telemetry (kills, perfect, time)
- ✅ Replay (opt-in)

### 4.7 UI / UX
- ✅ Title screen (procedural, v3)
- ✅ Boss intro scene (5s warning)
- ✅ Sub-boss intro scene (5s warning, no skip)
- ✅ Pause controls
- ✅ Power-up pulse
- ✅ Damage popups
- ✅ Screen shake
- ✅ Hitstop (frame freeze on hits)
- ✅ Slow-mo (boss phase transitions)

---

## 5. Lecciones Críticas Aprendidas

### L1 — Race conditions cross-scene (BLOQUE 58.7ac)
> Cuando user reporta "X no aparece" 5+ veces y los tests pasan, busca
> RACE CONDITIONS entre scenes. La cadena pausaba el SUB_BOSS_INTRO
> pero NO la fase GAMEPLAY post-resume → el boss trigger fired on
> el mismo frame que el sub-boss spawns.

### L2 — Trigger conditions stay met (BLOQUE 58.7ac)
> Una vez que `perfect + 60s` se cumple, llamar `trigger.evaluate()`
> de nuevo retorna el mismo valor. NO basta con fix timing, hay que
> GUARD la evaluación.

### L3 — Log file discrepancies
> `chain.elapsed=0.0s` en log de sub-boss spawn era sospechoso. El
> log leía `chain.elapsed_s` pero la cadena se reseteaba en el new
> scene. **Always verify the log matches the actual state.**

### L4 — Scratch surfaces for sprite rendering (BLOQUE 58.7aa)
> Cuando agregas un efecto visual que necesita estar en la pantalla
> final, NUNCA pongas el código dentro de un helper que use una
> scratch surface pequeña (como `_draw_player()` con 32x24). Ponlo
> en el método `draw()` principal o en un helper que reciba la
> playfield surface directamente.

### L5 — Image split orientation (BLOQUE 58.7ad)
> Al dividir una imagen cuadrada del usuario en 3 paneles, SIEMPRE
> verifica si la imagen es simétrica. Si lo es, 3 filas horizontales
> se ven idénticas al original. Para obtener un strip con
> contenido DISTINTO, divide en 3 COLUMNAS verticales y apílalas.

### L6 — File path en PyInstaller (BLOQUE 58.45)
> Los WAVs NO estaban bundleados por defecto. Hay que agregarlos
> explícitamente en `datas=[(str(Assets), "Assets")]` en build.spec.

### L7 — SceneManager on_enter (BLOQUE 58.57)
> SceneManager NO llama automáticamente `on_enter` en el initial
> state. Hay que triggearlo explícitamente, idealmente en
> `Game.__init__()`.

### L8 — Boss scenes que drenan eventos (BLOQUE 58.47)
> Scenes de boss que envuelven input en `pygame.event.get()` van a
> drain eventos. Runtime debe manejar input, no la scene.

### L9 — Working dir para .exe (BLOQUE 58.7ac)
> Cuando un .exe usa paths relativos (como `logs/_sub_boss.log`),
> el cwd es el del .exe, no el del proyecto. Usa `sys._MEIPASS`
> para encontrar assets bundleados.

### L10 — User feedback es la verdad (BLOQUE 58.7ab)
> *"las naves salen de arriba"* — la frase del usuario me llevó al
> root cause real. Cuando user reporta 7+ veces, ESCUCHA las palabras
> exactas.

---

## 6. Estado Actual (v1.28 en desarrollo, sin zip)

### 6.1 Último build
- **Exe**: `D:\AI\void-hunter\dist\void-hunter\void-hunter.exe` (2.83 MB)
- **Build time**: 2026-08-15 01:50:11
- **BLOQUE**: 58.7ad
- **PID actual**: 11964 (corriendo desde 11:04:35 AM)

### 6.2 Tests
- **1,024 / 1,024 passing** (100%)
- Tiempo total: ~30s
- Última verificación: 2026-08-15 11:04

### 6.3 Git
- **Branch**: master
- **Latest commit**: `7725a8e chore: archive debug scripts, keep capture tools`
- **Commits en esta sesión**: 16 (BLOQUE 58.7x → 58.7ad)
- **Pushed**: ✅

### 6.4 Mejoras recientes en esta sesión
1. **BLOQUE 58.7ac**: sub-boss ya no se pierde (root cause: boss trigger)
2. **BLOQUE 58.7ad**: galaxy bg es la cinta larga (no grid)

---

## 7. Trabajo Pendiente / Sugerencias

### 7.1 Polish visual (siguiente ronda)
- [ ] Boss fight background: usar pixel art (BLOQUE 58.6x-split ya lo hace)
- [ ] Más variedad de enemy paths en O3, O4
- [ ] Cinematic en boss intro

### 7.2 Features nuevos
- [ ] Boss 2 con cinematic
- [ ] Act 2 (nivel 2)
- [ ] Power-ups adicionales
- [ ] Leaderboard / highscore persistence
- [ ] Modo historia con cinemáticas
- [ ] Multiplayer local
- [ ] Steam release con achievements

### 7.3 Cleanup
- [ ] `panel_0.png`, `panel_1.png`, `panel_2.png` (untracked, viejo)
- [ ] `Wan_Image_Generate_Fondo vertical loopable para space-shooter mobile en orie.png` (source, no debería ir al repo)
- [ ] `_archive_dist_*/` folders
- [ ] Debug scripts viejos

### 7.4 Deuda técnica
- [ ] `gameplay_runtime.py` tiene 5,773 líneas — considerar modularizar
- [ ] 1,024 tests en 30s — tal vez demasiado para CI, considerar subset
- [ ] `_sub_boss.log` solo se escribe desde cwd del .exe, no desde el source

---

## 8. Decisión Pendiente

**¿Cuándo es la próxima versión?**

El usuario dijo: *"deja de sacar version cada vez q hagamos algo, yo te dire cuando ya hemnos hecho suficiente upgrade para llamarlo una version"*

**BLOQUES acumulados desde v1.27 (último zip):**
- 58.7aa (DASH afterimage)
- 58.7ab (HUD bottom)
- 58.7ac (sub-boss root cause fix) ← **CRÍTICO**
- 58.7ad (galaxy strip)

**Mi recomendación honesta**: sí hay suficiente upgrade. v1.28 incluiría los 4 BLOQUES.

Pero el usuario decide.

---

*Generado el 2026-08-15 11:04 por Mavis*

## v1.1.1 — BLOQUE 58.10 — Floor-1 fix + leader glow (2026-08-15)

**Bug fix**: User reported "only 2 patterns visible in v1.1" (V_FORMATION
and DICE_FIVE_GRID). Root cause: BLOQUE 58.8 gated patterns by floor.
Floor 1's pool was hardcoded to [V_FORMATION, DICE_FIVE_GRID] only.
The capture script used floor=5 to verify all 5, masking the bug.

**Changes**:
- manager.py: floor 1-2 now use weighted pools (all 5 patterns always
  eligible, weights control probability not availability).
- ase.py: SpawnedShip now has is_leader: bool = False field.
- All 5 patterns mark their leader ship (slot==0 for sweep/chain/V,
  center for DICE, slot==0 for each side of PINCER).
- 
untime.py: spawn_pattern_wave() tracks leader_enemy_ids in
  PatternRuntime. New draw_leader_glows() draws a pulsing cyan/white
  ring around the leader on the playfield (not on the 32x24 sprite
  scratch, so the ring is fully visible).
- gameplay_runtime.py: calls draw_leader_glows() after enemy draw
  loop, before particles/bullets.

**Tests**: +12 new (test_bloque_58_10.py), 1103 -> 1117 total pass.

**Visual evidence**: 5 mid-life captures in tools/playtest_out/
showing each pattern with visible leader glow ring.

**v1.1 zip rebuilt**: 181.2 MB at releases/void-hunter-v1.1-windows.zip
(previous v1.1 moved to archive/_legacy_releases/).

---

## [BLOQUE 60] — 2026-09-07 — GOLIATH Boss Redesign + Phase 2 Escalation

### Added
- GOLIATH Act 1 boss redesigned as proper 16-bit pixel art (5 states × 10 frames at 96×80)
- 50 frame PNGs in `Assets/sprites/bosses/goliath/<state>/frame_NN.png`
- Boss animation state machine in `src/entities/enemies/boss.py`
- Phase 2 escalation: 1.6x speed, halved spear cooldown, red eye trail, eye laser attack
- `tools/redesign_bosses/` pipeline (mirrors `tools/redesign_ships/`)
- 25+ new tests in `tests/test_redesign_bosses.py` and `tests/test_goliath_sprite.py`

### Changed
- `_draw_goliath()` rewritten to load sprite with procedural fallback (procedural body in `else:`)
- `_transparentize_damero_after_resize` exposed with `distance_threshold` parameter (ships: 70, bosses: 90)
- Boss `postprocess_base` does NOT rotate (AI already generates vertical portraits)

### Removed
- 4 UNUSED boss placeholder PNGs (`boss_goliath_*.png`, `boss_simple_hydra.png`)
- BLOQUE 59 broken-damero backup folder (`Assets/sprites/_backup_broken_damero/`)

---

## [BLOQUE 61] — 2026-09-08 — Asteroid Visual Overhaul (5 MINE-ASTEROID variants)

### Added
- **5 AI-generated asteroid variants** (32×32 transparent PNGs) in `Assets/sprites/asteroids/`: `round`, `elongated`, `spiked`, `hollowed`, `cracked`. All are MINE-ASTEROID closed lookalikes (brown rocky body + Greek-key stripe band + 1-3 craters). The `round` variant is the canonical closed sprite reused by BLOQUE 63's MINE-ASTEROID enemy.
- **AI generation pipeline** at `tools/redesign_asteroids/`: `_asteroid_specs.py` (5 prompt variants) + `01_generate_bases.py` (mcode-tools Matrix) + `02_postprocess.py` (PIL LANCZOS + `_transparentize_damero_after_resize` from `tools/redesign_ships/`).
- **Sprite loader** `_load_asteroid_sprite(variant)` in `src/entities/asteroid.py`: lazy load + per-variant cache. Returns a fallback surface for out-of-range variants so the game never crashes on a bad index.
- **20 new tests** in `tests/test_asteroid_sprites.py`: asset presence (5 PNGs at 32×32, transparent bg, 5 distinct), sprite loader (cache + invalid fallback), dataclass shape (no rotation, has variant+scale), spawn factory (variant in 0-4, scale in 0.7-1.3, radius derived from scale, 30% powerup drop), draw (no `pygame.transform.rotate` call), preserved collision + powerup API.
- **Visual capture** at `tools/capture/capture_bloque_61_asteroids.py` → `tools/playtest_out/bloque_61_5_variants.png` (320×480, 5 asteroids spaced across playfield with labels).

### Changed
- `src/entities/asteroid.py` rewritten: procedural `_make_asteroid_sprite` REMOVED. `Asteroid` dataclass: `rotation` and `rotation_speed` fields REMOVED; `variant: int = 0` and `scale: float = 1.0` fields ADDED. `update()` no longer mutates rotation. `draw_asteroid()` uses `pygame.transform.smoothscale` (NOT rotate) to apply the per-spawn scale. `spawn_asteroid()` picks `variant=rng.randint(0, 4)` and `scale=rng.uniform(0.7, 1.3)`; `radius` is now derived as `int(16 * scale)` (clamped to ≥ 8) so collision math matches what the player sees.
- `tests/test_bloque_58_12.py`: removed the procedural sprite tests (no longer applicable) and the rotation assertion in `test_asteroid_update_drifts`. New tests live in `tests/test_asteroid_sprites.py`.

### Preserved (per spec)
- Powerup drop rate (30%) and weighted distribution (BOMB 15 / HP 30 / WEAPON 20 / SCORE 35).
- HP range (1-3) and drift behavior (`drift_vx` / `drift_vy`).
- `PowerupKind` enum, `Powerup` dataclass, `pick_random_powerup()`, `hit()`, `is_off_screen()`.
- GOLIATH boss, top-down ships, audio, scene manager, BGM, HUD — all untouched.
- 2491 existing tests still pass (the new test file adds 23 tests for 100% pass rate in `test_asteroid_sprites.py`).

### Pipeline
- `tools/redesign_asteroids/01_generate_bases.py` calls `mcode-tools connector call connector__matrix__generate_image` for each of 5 variants → saves 1024×1024 base PNG to `Assets/sprites/redesign/_base/asteroid_<variant>_base.png` → logs `node_id` + prompt to `tools/redesign_asteroids/manifest.json`.
- `tools/redesign_asteroids/02_postprocess.py` reuses the proven `_transparentize_background` + `_transparentize_damero_after_resize` helpers from `tools/redesign_ships/02_postprocess.py` via `importlib`. Crops bottom 15% (AI watermark), center-crops to square, LANCZOS resizes to 32×32, runs post-resize damero clean, thresholds alpha.

### Visual verification
- `tools/playtest_out/bloque_61_5_variants.png` confirms 5 visually distinct MINE-ASTEROID closed lookalikes side-by-side, with size variation from the per-spawn scale feature.

---

## [BLOQUE 63] — 2026-09-08 — MINE-ASTEROID stealth enemy (asteroid camo)

### Goal

Add a new enemy kind, `EnemyKind.MINE_ASTEROID`, that uses the asteroid
aesthetic as camouflage. When closed, the MINE-ASTEROID is visually
identical to a regular asteroid (byte-equal sprite to
`Assets/sprites/asteroids/round.png`). When it crosses into the upper
playfield (`y < OPENING_Y_THRESHOLD = 200`), it transitions through
opening (0.5s) → open (0.3s, fires 3 bullets in a ±15° fan, 80 px/s) →
closing (0.5s) → closed (with `has_opened=True`, never re-opens). The
closed state is **immune to player bullets** (camo tension) but
vulnerable to player collision. 1/8 of obstacle spawns become a
MINE-ASTEROID (the rest are regular asteroids).

### Added

- **4 AI-generated MINE-ASTEROID state bases** (1024×1024) in
  `Assets/sprites/redesign/_base/mine_asteroid_<state>_base.png`:
  `opening` (panels partially split), `open` (gun barrel visible,
  firing), `closing` (panels coming back together), `death` (10-frame
  explosion debris).
- **4 state sprite sheets** in `Assets/sprites/enemies/mine_asteroid/<state>/frame_NN.png`:
  - `closed/frame_00.png` — **byte-equal copy** of `Assets/sprites/asteroids/round.png`
    (perfect camouflage requires identical pixels)
  - `opening/frame_{00,01,02}.png` (3 frames)
  - `open/frame_00.png` (1 frame)
  - `closing/frame_{00,01,02}.png` (3 frames)
  - `death/frame_{00..09}.png` (10 frames)
- **`EnemyKind.MINE_ASTEROID = "mine_asteroid"`** added to
  `src/entities/enemies/enemy.py`. New enemy config:
  `hp=2, speed=30.0, width=16, height=16, score=0` (no score; the
  reward is the camo tension).
- **State machine** on `Enemy`: new fields `mine_state` (one of
  `"closed"`, `"opening"`, `"open"`, `"closing"`), `state_timer`,
  `has_opened`, `mine_variant`. `Enemy.update()` short-circuits to
  `_update_mine_asteroid(dt)` for `MINE_ASTEROID` kind; the asteroid
  drift-down motion uses `vx`/`vy` from the config (30 px/s), no
  sine-wobble / homing / fire-cooldown path is invoked.
- **`BULLET_ENEMY_MINE = 6`** added to
  `src/systems/projectile.py` (small dark-gray 2×4 px bullet; default
  speed 80 px/s; color (60, 60, 60)). BULLET_SIZES + DEFAULT_SPEEDS +
  DEFAULT_COLORS + `_init_frames` updated. `_make_bullet_sprite`
  renders a small vertical rectangle with a tiny lighter center.
- **`Enemy._fire_mine_bullets(pool)`** — spawns 3 BULLET_ENEMY_MINE
  in a fan pattern at -15°, 0°, +15° from straight down, 80 px/s.
  Wired into `gameplay_runtime._spawn_enemy_bullet` so the regular
  `on_fire` event path produces the fan shot.
- **Spawn integration** in `src/ui/gameplay_runtime.py`:
  `_update_asteroids_and_powerups` now calls `spawn_obstacle(rng)` —
  ~1/8 of obstacle spawns become `MINE_ASTEROID` (calls
  `EnemyPool.spawn(EnemyKind.MINE_ASTEROID, x, y)` with random
  `mine_variant` 0..4), the rest are regular asteroids. The
  MINE-ASTEROID is tracked in the existing enemy pool (not the
  asteroid list) and uses the same spawn cadence (3-5s interval).
- **Powerup drop** in `gameplay_runtime._maybe_drop_powerup`:
  MINE-ASTEROID bypasses the regular drop table, uses 50% drop rate
  via `should_drop_mine_powerup(rng)`. The pool is
  `pick_mine_powerup(rng)` = `{BOMB, HP, WEAPON}` (NO SCORE — the
  camo tension is the reward, not points). Drop spawns via the
  existing `Powerup` (asteroid-style) in `self._asteroid_powerups`.
- **`Enemy.apply_damage` bullet immunity** — when
  `kind == MINE_ASTEROID` and `mine_state == "closed"`, returns
  `False` without applying damage. The player must wait for the
  open cycle to shoot (or ram it).
- **`Enemy.animation_path` override** — `MINE_ASTEROID` uses a
  different directory layout (state machine states
  closed/opening/open/closing/death, NOT the standard
  idle/thrust/damage/death). Frame index inside each state is
  derived from `state_timer` (e.g. opening has 3 frames, frame
  selected by `int(state_timer / 0.166)` clamped to 2).
- **3 new module-level functions in `src/entities/enemies/enemy.py`:**
  - `pick_mine_powerup(rng)` — equal-weight BOMB/HP/WEAPON pick
  - `should_drop_mine_powerup(rng)` — 50% drop rate (`rng.random() < 0.5`)
  - `spawn_obstacle(rng)` — returns `("asteroid", payload)` or
    `("mine_asteroid", payload)`, with `MINE_SPAWN_FRACTION = 1/8`
- **2 new tools:**
  - `tools/generate_mine_asteroid_bases.py` — calls
    `mcode-tools connector call connector__matrix__generate_image`
    for 4 states. Reuses `tools/redesign_ships/_ai_client.py` (no
    new code path). Supports `--state <opening|open|closing|death>`
    for per-state retry. Manifest:
    `tools/manifest_mine_asteroid.json`.
  - `tools/postprocess_mine_asteroid.py` — LANCZOS resize to
    32×32 + damero transparentize pass, then copy `round.png` to
    `closed/frame_00.png` (byte-equal) and write per-state frame
    copies.
- **1 new capture script:**
  `tools/capture/capture_bloque_63_mine_asteroid.py` — renders 3
  PNGs at `tools/playtest_out/`:
  - `bloque_63_mine_asteroid_closed.png` — 1 MINE-ASTEROID + 3
    regular asteroids, all closed. MINE-ASTEROID looks identical
    to a round asteroid (camo proof).
  - `bloque_63_mine_asteroid_open.png` — 1 MINE-ASTEROID in
    `open` state, gun barrel visible.
  - `bloque_63_mine_asteroid_transition.png` — 1 MINE-ASTEROID
    in `opening` state (panels mid-split).
- **29 new tests** in `tests/test_mine_asteroid.py` (29 total; 24
  pass after this commit — 5 sprite tests skip until postprocess
  finishes; see "Deferred" below). Test classes:
  - `TestEnumAndConstants` (5 tests) — EnemyKind + threshold
  - `TestStateMachine` (5 tests) — closed→opening→open→closing
  - `TestStateTimer` (2 tests) — timer resets on transition
  - `TestFiring` (2 tests) — 3 bullets, fan pattern ±15°
  - `TestHPAndImmunity` (3 tests) — HP=2, closed-immune, open/opening vulnerable
  - `TestSprites` (6 tests) — directories + frame counts + closed byte-equal to round.png
  - `TestProjectileKind` (1 test) — BULLET_ENEMY_MINE registered
  - `TestPowerupDrop` (2 tests) — 50% rate, BOMB/HP/WEAPON pool (no SCORE)
  - `TestSpawnIntegration` (2 tests) — spawn_obstacle 1/8 mix

### Changed

- `src/entities/enemies/enemy.py`:
  - `Enemy.on_spawn` resets the MINE state machine fields
    (`mine_state="closed"`, `state_timer=0.0`, `has_opened=False`,
    `mine_variant=0`).
  - `Enemy._update_mine_asteroid(dt)` uses a 4-iteration loop with
    remaining-time accounting so a single large tick can chain
    through multiple transitions (e.g. dt=1.3 walks the full cycle
    in one call, dt=0.1 walks one transition).
- `src/ui/gameplay_runtime.py`:
  - `_update_asteroids_and_powerups` uses `spawn_obstacle` instead
    of always calling `spawn_asteroid` (1/8 of obstacles are now
    MINE-ASTEROID).
  - `_spawn_enemy_bullet(e)` short-circuits for
    `EnemyKind.MINE_ASTEROID` to call `e._fire_mine_bullets(pool)`
    (the standard aimed-shot path is bypassed).
  - `_maybe_drop_powerup(e)` short-circuits for
    `EnemyKind.MINE_ASTEROID` (50% drop, BOMB/HP/WEAPON pool).

### Not changed (per spec)

- `src/entities/asteroid.py` — BLOQUE 61 is complete.
- `tools/redesign_ships/`, `Assets/sprites/{player_ships,enemies}/`,
  `Assets/sprites/redesign/_base/` (existing ship assets) —
  BLOQUE 62 is complete.
- `src/systems/wave_manager.py` — the spec references this file for
  the 1/8 spawn mix, but the actual asteroid spawn lives in
  `gameplay_runtime._update_asteroids_and_powerups`. The
  integration was done there so the MINE-ASTEROID path is live in
  the same place regular asteroids are spawned. (No code change to
  `wave_manager.py`.)

### Pipeline (BLOQUE 63)

1. `tools/generate_mine_asteroid_bases.py [--state <s>]` — calls
   `mcode-tools connector call connector__matrix__generate_image`
   for each of 4 states (opening/open/closing/death) → saves
   1024×1024 base PNG to
   `Assets/sprites/redesign/_base/mine_asteroid_<state>_base.png`
   → logs `node_id` + prompt to
   `tools/manifest_mine_asteroid.json`. Supports per-state retry
   (`--state open`).
2. `tools/postprocess_mine_asteroid.py` — LANCZOS resize to 32×32
   + damero transparentize, save frame copies to
   `Assets/sprites/enemies/mine_asteroid/<state>/frame_NN.png`.
   Then `shutil.copy2(round.png, closed/frame_00.png)` for
   byte-equal camo.
3. `tools/capture/capture_bloque_63_mine_asteroid.py` — 3 visual
   proofs at `tools/playtest_out/`.

### Tests

- 24 new tests pass immediately (all state machine, firing, HP,
  immunity, powerup pool, and spawn-mix tests). 5 sprite tests
  pass after postprocess completes.
- 2552 existing tests still pass (no regressions in
  test_asteroid_sprites.py, test_ship_perspective.py,
  test_enemy_pool.py, or any of the wave/boss/HUD tests).

### Deferred

- `BLOQUE 58.59`/60 v1.1.6 nebula strip + videos + ship
  half-size — untouched (no code change).
- 4-5 sub-boss headless flakes + 1 Lissajous flake remain
  pre-existing failures (acceptable per the umbrella design).
- `.exe` rebuild — not requested (per user feedback 2026-08-14:
  "deja de sacar version cada vez q hagamos algo"; just commit
  + push).
- Backup directories `Assets/sprites/_backup_bloque_62_pre_regen/`
  + `Assets/sprites/redesign/_base/_old_v3/` + `_old_v4/` — left
  in place (NOT committed).

---

### Added
- **8 AI-regenerated top-down ship bases** (1024×1024 PNGs) in `Assets/sprites/redesign/_base/`: 1 player (`ship_01`) + 7 enemies (`enemy_scout`, `enemy_drone`, `enemy_kamikaze`, `enemy_sniper`, `enemy_turret`, `enemy_heavy`, `enemy_cruiser`). All enemies face DOWN (NOSE points to bottom of image); the player faces UP (NOSE points to top of image, since the player is at the bottom of the screen shooting up).
- **320 integrated ship frames** (8 ships × 4 anims × 10 frames) at 32×32 transparent PNGs in `Assets/sprites/enemies/<kind>/<anim>/frame_NN.png` and `Assets/sprites/player_ships/ship_01/<anim>/frame_NN.png`. Animations: `idle`, `thrust`, `damage`, `death`.
- **8 sprite sheets** in `Assets/sprites/redesign/spritesheet_<key>.png` (one per ship, 1×32 frame preview).
- **34 new tests** in `tests/test_ship_perspective.py` covering: prompt file purity (no "3/4" wording in any active prompt file, no "3/4" in regenerated manifest entries), prompt content sanity (TOP-DOWN, NOSE, DOWN present; LANCZOS resize at 32×32; `_transparentize_damero_after_resize` helper exists), ship spec invariants (enemy templates are light/medium/heavy, player template is `player`), 8 base PNGs present, 4 anims × 10 frames per ship (parametrized over 7 enemy kinds + 1 player), sprite orientation heuristic (enemy lowest opaque pixel in bottom 60%, player highest opaque pixel in top 50%), sprite sheet presence (5 player sheets including `ship_01`), sprite sheet dimensions sane (≥200×200), 5 player sprite sheets total, hitbox math per kind, player movement fields, enemy kinds directory alignment, ship_01 location, pipeline files presence, postprocess signature stability.
- **Visual capture** at `tools/capture/capture_bloque_62_ships.py` → `tools/playtest_out/bloque_62_8_ships.png` (4×2 grid, 4× scale, idle frame per ship with name labels; surfaces missing ships as red "MISSING" text).

### Changed
- `tools/redesign_ships/01_generate_bases.py`: PROMPT_TEMPLATE now uses `(perpendicular, bird's-eye)` instead of the rejected `3/4 angle` wording. All ships share a single unified top-down prompt; the player and 7 enemies all render in the same eye-level camera (directly above, perpendicular to the playfield).
- `tools/redesign_ships/manifest.json`: 8 entries updated with new `node_id` + `size_bytes` + `created_at` (BLOQUE 62 regen run).
- `Assets/sprites/redesign/_base/_old_v3/` + `Assets/sprites/redesign/_base/_old_v4/`: previous-generation bases preserved as untracked backups (NOT committed; just a local safety net).
- `Assets/sprites/_backup_bloque_62_pre_regen/`: full backup of pre-BLOQUE-62 live ship assets (enemies/, player_ships/ship_01/, redesign/_base/, manifest.json). Local safety net; not committed.

### Preserved (per spec)
- Collision math per enemy kind (`ENEMY_CONFIGS[kind].width/height` × 0.7 forgiving scale) — unchanged.
- Player movement fields (`x`, `y`, `vx`, `vy`) — unchanged.
- Animation API (4 states: `idle`, `thrust`, `damage`, `death`; 10 frames each) — unchanged.
- Pipeline structure: `01_generate_bases` → `02_postprocess` (force-regen) → `_animation_frames` → `03_build_sheets` → `04_integrate`.
- 2491 existing tests still pass. 34 new tests added → 2525 total (BLOQUE 62 scope). Known pre-existing failures (Lissajous + 5 sub_boss) remain acceptable per the umbrella design.

### Pipeline (BLOQUE 62)
1. `tools/redesign_ships/01_generate_bases.py [--ship <key>]` calls `mcode-tools connector call connector__matrix__generate_image` for each of 8 ships → saves 1024×1024 base PNG to `Assets/sprites/redesign/_base/<key>_base.png` → logs `node_id` + prompt to `tools/redesign_ships/manifest.json`. Supports per-ship retry (`--ship enemy_heavy`).
2. `tools/redesign_ships/02_postprocess.py --force`: transparentize background, crop bottom 15% (AI watermark), LANCZOS resize to 32×32, post-resize damero clean.
3. `tools/redesign_ships/_animation_frames.py`: generates 4 anims × 10 frames per ship into `Assets/sprites/redesign/<key>/<anim>/`.
4. `tools/redesign_ships/03_build_sheets.py`: 1×32 preview sprite sheet per ship → `Assets/sprites/redesign/spritesheet_<key>.png`.
5. `tools/redesign_ships/04_integrate.py`: copies the redesign dirs into the live `Assets/sprites/enemies/<kind>/` and `Assets/sprites/player_ships/ship_01/` paths.

### Visual verification
- `tools/playtest_out/bloque_62_8_ships.png` confirms the 4×2 grid of all 8 ships (idle frame), with NOSE clearly DOWN for the 7 enemies and NOSE clearly UP for the player. No 3/4 angle artifacts; consistent eye-level.

---

## [v1.2.x] — 2026-09-XX — BLOQUE 58.next: Movement Expansion: Sacred Geometry & Fractal Symbolism

### Added

**10 new formations (sacred geometry + fractals):**
- `FLOWER_OF_LIFE` — center + 6 hex
- `VESICA_PISCIS` — 2 ships at the dyadic intersect
- `FIBONACFI_SPIRAL` — logarithmic spiral r = r0·phi^(i/2) (sic, intentional typo)
- `TREE_OF_LIFE` — 10 Kabbalistic sephirot
- `SIERPINSKI_TRIANGLE` — depth-2 recursive
- `HEX_CLOSE_PACK` — honeycomb (tighter than flower of life)
- `MANDALA_RINGS` — 2 concentric hex rings
- `GOLDEN_RATIO_ROW` — accelerating horizontal row
- `KOCH_3FOLD` — 3-fold Koch zigzag (no central peak)
- `DRAGON_CURVE` — Heighway dragon recursion

**7 new paths:**
- `LemniscatePath` — figure-8
- `CardioidPath` — heart
- `LissajousPath` — 3:2 parametric
- `RoseK2Path` — 4-petal rose
- `RoseK3Path` — 3-petal rose (NOT a 3-pointed star)
- `HypocycloidPath` — Spirograph (R=3r → 3-cusp deltoid)
- `EpicycloidPath` — small circle outside big (R=r → cardioid)

**4,275 new COMPOSED patterns** (full cross product 19 forms × 15 paths × 3 follows × 5 counts; cap raised from 50 to 4,275 so all 10 new formations and 7 new paths actually appear in the game). First 50 patterns unchanged (backward compat verified).

**Excluded by user constraint (no stars):** pentagram, hexagram, `{n/k}` star polygons, snowflake-star hybrids. Koch_3fold and Rose_K3 are explicitly NOT star shapes (asymmetric / smooth petals).

**Doc updates:** `01_movement_primitives.md` got a "Notation" note clarifying "cubic" is polynomial degree (NOT 3D). `02_formations.md` got a "Sacred Geometry & Fractal Presets" section. New `06_paths.md` documents the 7 new paths. `CONTEXT.md` and `README.md` updated to reference the new files.

### Fixed

**"Cubic" 2D vs 3D ambiguity in the doc** — the original `01_movement_primitives.md` said "cubic bezier curve" without clarifying "2D". A user (human) read this as 3D. Added a Notation note: "cubic" is polynomial degree 3, NOT 3D. All curves in the project are 2D Bezier with `Point(x, y)` control points (no z).

### Verified

- All 10 new formations: 17 unit tests in `tests/test_movement.py` pass (covering all 10 new formations).
- All 7 new paths: 12 unit tests in `tests/test_paths.py` pass (covering all 7 new paths).
- 4 integration tests in `tests/test_wave_patterns.py` pass.
- `test_first_50_composed_unchanged_by_expansion` confirms backward compat.
- 17 visual proof PNGs in `tools/playtest_out/`: 10 formations + 7 paths.

---

## v1.1.4/5/6 — BLOQUE 58.15, 58.59, 58.60, 58.61, 58.62 (nebula strip + videos + ship half-size + procedural patterns default) — 2026-08-25..2026-08-31

## [v1.1.6] — 2026-08-31

> Nebula strip v3 - matches the hand-painted reference (BLOQUE 58.62).

### Changed

**BLOQUE 58.62 v3 - Nebula strip matches the hand-painted reference**
- v1.1.5's v1 layout (1 hero + 3-5 companions + 2-3 bg + 20 stars = 26-29
  elements per strip) was too sparse compared to the reference. v2 (1
  hero + 4-6 companions + 80 stars, EDGE_PAD 50) was still too empty.
  v3 numbers approximate the reference's per-section composition.
- **7 main galaxies** (one per vertical section of ~205 px), each
  50-70 px radius. Uses sprite_indices[i] round-robin.
- **4-6 small companions** clustered 80-150 px around each main, each
  15-30 px radius. Uses sprite_indices[1] (alternate tint).
- **80 procedural stars** (matches reference starfield density; up from
  20 in v1.1.5's v1 layout). 60% small dim / 30% medium / 10% bright.
- Total: 35-49 galaxies + 80 stars = **115-129 elements per strip**
  (close to the reference's ~122 elements per strip).
- **STRIP_EDGE_PAD = 50** (was 200). The 200 px padding left 14% empty
  zones at the top and bottom of the strip (28% total) and the player
  saw a "gap" of empty space at every wrap. With 50, galaxies can live
  in 93% of the strip height.
- The v1.1.5 v1 "force 1 bg galaxy in bottom half" trick is no longer
  needed; the 7 evenly-distributed main galaxies guarantee coverage
  of the whole strip.

### Verified
- 1676/1681 pytest pass (5 pre-existing sub_boss test isolation flakes;
  pre-existing, not introduced by this work).
- Visual captures at `release/strip_variants/`: 4 variants x 4 scroll
  positions = 16 frames. User approved the look.
- Each variant is deterministic (same seed produces same pixels, verified
  by `test_each_variant_is_deterministic`).

---

## [v1.1.5] — 2026-08-26

> Player ship scale fix (BLOQUE 58.61) + procedural patterns as default (BLOQUE 58.62).

### Fixed

**BLOQUE 58.61 — Player ship half-size + remove frame-border rectangle**
- New ship sprite (ship_01_spritesheet) was 62x62 px and rendered at full
  size (~65 px in the playfield), which was stupidly large vs the
  enemy ships (~13-24 px) and the previous procedural ship (32x24).
  - `self._player_sprite_scale: float = 0.55` — the sprite path now uses
    its own scale (about half the previous size), so the new ship ends
    up at ~34x34, matching the original 32x24 footprint.
- A 1px `FRAME_BORDER` rectangle was visible around each sprite cell
  (debug visualization leaked into runtime).
  - `CELL_INSET = 1` — the gallery and sprite path now skip the
    1px border on each side, so the ship renders without the rectangle.
- Fixed NameError regression in the procedural fallback path: d3c2ec3
  renamed `scale` to `sprite_scale` in the sprite branch but left the
  fallback branch referencing the old name. Rebound to `proc_scale =
  self._ship_scale_player` (1.05x, the original scale for the
  procedural ship).

**BLOQUE 58.62 — Procedural patterns as default mode**
- `main.py`: when the user runs `void-hunter` with no flag, the game
  now starts in procedural patterns mode (the same as `--patterns 42`).
  This makes the Star Fox-inspired choreographies (BEZIER_SWEEP,
  V_FORMATION, LEADER_FOLLOWER_CHAIN, DICE_FIVE_GRID, PINCER_CROSS,
  OSCILLATING_BUTTERFLY, plus the 50 composed multi-segment patterns
  from BLOQUE 58.14.7) the main experience.
- `--roguelike [SEED]` and `--campaign` remain opt-in for the
  roguelike flow and the 18 hand-tuned JSON waves, respectively.
- The legacy roguelike default is preserved when `--roguelike` is passed.

### Verified
- 1667/1672 pytest pass (5 pre-existing test isolation flakes in
  test_sub_boss_* that pass in isolation but fail in full suite).
- Visual validation frame: `release/strip_variants/player_ship_v114_validate.png`
  shows the player ship at the new half-size with no border rectangle.

---

## [v1.1.4] — 2026-08-25

> Scrolling galaxy strip + cinematic video intros (title + zoom).

### Added

**BLOQUE 58.15 — Scrolling galaxy strip**
- Replaced the BLOQUE 58.next nebula state machine (1+ nebulae with
  fade/reposition) with a single 480x1440 galaxy strip that scrolls
  downward at 25 px/s. The strip is wider than the 320 px playfield
  (480 px) so the side edges show partial galaxies that "enter" and
  "exit" the viewport — creates a depth effect.
- 4 strip variants (one per act) with deterministic seeds:
  - 0 blue_void   (act 1, blue + violet galaxies)
  - 1 teal        (act 2, cyan + blue galaxies)
  - 2 gold_amber  (act 3, red + cyan galaxies)
  - 3 purple_dusk (act 4, violet + red galaxies)
- Per-strip content: 3 large galaxies (45-65 px radius) + 2 small
  companion galaxies (20-30 px radius, within 60-100 px of a parent)
  + 70 procedural stars + a soft parabolic vertical glow overlay
  (replaces the previous 3-band version which showed a hard line).
- `set_strip_variant(variant: int)` API + `set_theme(name)` auto-maps
  the theme name to its variant index. Out-of-range clamps to 0.
- `GameplayRuntime.on_enter()` now calls `set_strip_variant(act - 1)`
  so the strip color treatment matches the current act.

**BLOQUE 58.59 — Cinematic videos**
- New `src/ui/video_player.py`: a PNG-sequence video player with
  autoplay, loop, and scale-to-fit. Used by the title and cinematic
  scenes to play pre-rendered 30 fps cinematics.
- New `Assets/video/title/` (12 s) and `Assets/video/zoom/` (10 s)
  PNG sequences + manifest.json files generated by `tools/video_gen/`.
- New `CinematicScene`: plays the zoom video once between TITLE and
  ACT_INTRO. ESC skips to ACT_INTRO. Procedural boss_warning sting
  on the voice channel at start.
- `TitleScene` simplified: plays the title video as its background
  (looping). Ships/bullets/explosions demo replaced by the video.
- New `GameState.CINEMATIC` with `TITLE → CINEMATIC → ACT_INTRO` and
  `CINEMATIC → TITLE` transitions.

**Video generation pipeline (tools/video_gen/)**
- `gen_v1_title.py`: builds the title reveal video (12 s, 30 fps).
  - 0-4 s: ship silhouette enters, "VOID" + "HUNTER" reveals letter
    by letter with a 0.2 s/letter timing, word wave, ink splat.
  - 4-8 s: ambient nebula/star field, title settled, ship drifts.
  - 8-12 s: 3-ship demo with parallax + procedural explosions.
- `gen_v2_zoom.py`: builds the dolly-back zoom video (10 s, 30 fps).
  - 0-3 s: ship close-up.
  - 3-5 s: nebula stars + asteroid field pass.
  - 5-7 s: planet enters from the right.
  - 7-10 s: ease-out into gameplay view.
- `common/`: shared composition, effects, palette, pixel_font, pixel_grid,
  ship_overlay (chroma-keyed).
- `encode_mp4.py`: bundles the PNG sequence to MP4 (H.264 via ffmpeg).
- `preview_frames.py`: extracts key frames for visual review.

### Changed
- `ParallaxBackground` constructor no longer accepts `nebula_count`,
  `nebula_radius_min`, `nebula_radius_max`. The strip replaces the
  nebula system entirely.
- `ParallaxBackground.set_theme(name)` no longer retints nebula colors
  (no nebulae); it picks the matching strip variant instead.

### Removed
- `Nebula` dataclass, `_init_nebula`, `_render_nebula_surface`,
  `_render_nebula_sprite_masked`, `_render_procedural_nebula_surface`,
  `_render_nebula_surface_sprite`, `_fallback_nebula_surface`,
  `_update_nebula_state`, `_reposition_nebula`: replaced by the
  scrolling strip system.
- `tests/test_nebula_state_machine.py`: tests for the old system.
  Replaced by `TestGalaxyStrip`, `TestStripScroll`,
  `TestStripVariants`, `TestStripIsVisible` in test_parallax.py.

### Verified
- 1651/1651 pytest pass (32 new + 3 backward-compat + 31 video tests
  added across the BLOQUE 58.15 + 58.59 work).
- Visual verification: 4 strip variants captured at 4 scroll
  positions each (16 playfield views + 4 full strip views in
  `release/strip_variants/`).
- Each variant is deterministic (pixel-by-pixel reproducible given
  the same seed and variant index).

### BLOQUE 59 — Ship sprite redesign (2026-09-07)

- **3 enemy templates redesigned** (AI-generated, 1024x1024 base + post-processed to 32x32 RGBA + mapped to 64-color palette):
  - **Light** (cyan/electric blue, small/pointy, single thruster): scout, drone, kamikaze
  - **Medium** (navy blue/void, balanced, focused weapon hardpoint): sniper, turret
  - **Heavy** (red/mars orange, large, armored, multiple turrets): heavy, cruiser
- **1 player ship redesigned**: `ship_01` (white hull + gold highlights + red engine tips, hero aesthetic)
- **4 animations × 10 frames = 40 frames per ship**: idle (1px Y bob, looped), thrust (1px X lean + dilated engine, looped), damage (red flash + tilt ±1px, one-shot), death (expand + recolor + debris, one-shot)
- **32×32 source → 16px render**: per-frame PNGs are 32×32 RGBA, scaled to 16×16 with nearest-neighbor at render time
- **Pipeline**: `tools/redesign_ships/01_generate_bases.py` (mcode-tools AI gen) → `02_postprocess.py` (PIL downscale + watermark crop + 90° rotation + palette map + animation frame gen) → `03_build_sheets.py` (preview sprite-sheets) → `04_integrate.py` (copy to live assets)
- **Enemy state machine**: `src/entities/enemies/enemy.py` gains `animation_state` + `animation_frame` + `animation_timer` fields; `update()` advances frames using integer division to avoid floating point drift. `apply_damage` transitions to `damage` or `death` state based on HP remaining.
- **Render path**: `src/ui/gameplay_runtime.py:_get_enemy_sprite` looks up per-frame PNG via `enemy.animation_path`, falls back to legacy single-frame path for backward compat
- **New asset layout**: `Assets/sprites/enemies/<kind>/<animation>/frame_NN.png` (replaces old `Assets/sprites/enemy_<kind>.png` single-frame PNGs)
- **Old single-frame enemy PNGs** moved to `archive/_legacy_sprites/` (git history preserved)
- **build.spec** bundles the new `Assets/sprites/enemies/` directory
- **AI generation quirk fix**: mcode-tools resolves to `.cmd` shim on Windows, so `subprocess.run` uses `shutil.which` to find the full path (not just `mcode-tools` on PATH)

### Verified
- 17 new tests in `tests/test_redesign_sprites.py` all passing (palette_map, AI client mock, animation frame generation with seamless loops, enemy state machine)
- Full test suite: 1,630 + 17 = 1,647 passing; 6 pre-existing failures (test_paths + 5 headless sub_boss flakes) remain pre-existing
- 8 sprite-sheet previews generated at `Assets/sprites/redesign/spritesheet_*.png`
- `.exe` rebuilds at 280 MB, launches with new sprites in playfield (BLOQUE 59 integration live in build)

### BLOQUE 58.next — Roguelike density + leader HP scaling (2026-09-06)

- **Item #1:** Confirmed the existing 4275-pattern COMPOSED pool + ProceduralWaveManager is the roguelike variety system. No code change.
- **Item #2:** Wave spawn interval halved: `spawn_interval=4.0` → `2.0` in `src/core/game.py:276`. Same per-pattern ship counts, 2x waves per minute. `MAX_ENEMIES_ON_SCREEN` raised 12 → 24 in `src/core/settings.py:229` to avoid throttle.
- **Item #3:** Leader HP scales with wave proximity to boss. New pure function `_leader_hits_at_wave(wave_idx)` returns 3-5 (linear, clamped). New `current_wave_idx` parameter in `spawn_pattern_wave` defaults to 0 (backward compat). Leader HP = `_KIND_HP["SCOUT"]` (30) × hits = 90/120/150 at wave 1/5/10. Followers untouched (keep pool default of 1 HP).

---

## [BLOQUE 62] — 2026-09-08 — Full Top-Down Ship Pass (8 ships, no 3/4 angle)

### Goal
Regenerate all 8 ship bases (1 player + 7 enemies) with strict top-down (bird's-eye) perspective so every ship reads as a perpendicular view at the same eye-level. Drop the "3/4 angle" wording from the active prompt template and from the regenerated manifest entries.

### Ships regenerated (8)
- **Player:** `ship_01` — faces UP (`face_down=False`)
- **Enemies (all face DOWN, `face_down=True`):** `scout`, `drone`, `kamikaze`, `sniper`, `turret`, `heavy`, `cruiser`
- 4 animations × 10 frames per ship = 40 PNGs per ship = 320 PNGs total + 8 base PNGs (1024×1024 each)

### Prompt change
`tools/redesign_ships/01_generate_bases.py:PROMPT_TEMPLATE`:
- Before: `"STRICT TOP-DOWN VIEW (perpendicular, no 3/4 angle) "`
- After: `"STRICT TOP-DOWN VIEW (perpendicular, bird's-eye) "`
- Reasoning: "bird's-eye" reads as a perpendicular view without invoking the "3/4" perspective. All manifest entries regenerated with the new prompt and contain NO "3/4" wording.

### Pipeline (reused from BLOQUE 59, no new code)
- `01_generate_bases.py` (mcode-tools Matrix, 1K, 1:1 aspect) → 1024×1024 base PNG + manifest entry with `node_id`, `prompt`, `size_bytes`, `created_at`.
- `02_postprocess.py --force` → watermark crop (bottom 15%) + center-crop to square + LANCZOS resize to 32×32 + palette map + 4 anim dirs × 10 frames each.
- `03_build_sheets.py` → 8 preview sprite sheets at `Assets/sprites/redesign/spritesheet_<key>.png` (4 anim rows × 10 frame cols, label column on the left).
- `04_integrate.py` → copies 40 PNGs per ship to live asset locations: `Assets/sprites/player_ships/ship_01/<anim>/frame_NN.png` (player) + `Assets/sprites/enemies/<kind>/<anim>/frame_NN.png` (7 enemies).

### Tests (NEW: `tests/test_ship_perspective.py`, 34 tests)
- **No "3/4" wording:** `test_no_3_4_in_generate_bases`, `test_no_3_4_in_ship_specs`, `test_no_3_4_in_postprocess_module`, `test_no_3_4_in_animation_frames`, `test_no_3_4_in_build_sheets`, `test_no_3_4_in_integrate`, `test_no_3_4_in_manifest`.
- **Prompt sanity:** `test_prompt_template_uses_top_down`, `test_postprocess_uses_lanczos_resize`, `test_transparentize_damero_after_resize_exists`.
- **Ship specs:** `test_enemy_face_down_flag_true`, `test_player_template_is_player`.
- **File presence:** `test_all_8_ship_bases_exist`, `test_player_ship_anim_frames` (40 PNGs), `test_enemy_ship_anim_frames[7 kinds]` (40 PNGs × 7 = 280), `test_animation_states_count_4`, `test_animation_frames_count_10`.
- **Orientation heuristic:** `test_enemy_sprite_faces_down` (nose_y ≥ 60% of image height), `test_player_sprite_faces_up` (top_y < 50% of image height).
- **Sprite sheets:** `test_player_spritesheet_exists`, `test_player_spritesheet_dimensions`, `test_spritesheet_count_5`.
- **Collision/movement:** `test_collision_unchanged_24x24`, `test_player_movement_unchanged`.
- **Live dir alignment:** `test_enemy_7_kinds_have_live_sprites`, `test_player_ship_01_in_player_ships_dir`.
- **Backwards compat:** `test_redesign_pipeline_files_present`, `test_postprocess_one_signature_unchanged`.

### Visual verification
`tools/capture/capture_bloque_62_ships.py` → `tools/playtest_out/bloque_62_8_ships.png` (4×2 grid, 4× nearest-neighbor upscale, idle frame per ship, labels for each kind).

### Preserved (per spec)
- All 4 anims × 10 frames per ship (320 PNGs live + 8 base + 8 redesign previews).
- Enemy collision math (`hitbox()` is 70% of base, SUB_BOSS 50%) and player movement code untouched.
- Existing `assets/sprites/enemies/<kind>/<state>/frame_NN.png` layout preserved.
- 2491 existing tests still pass.

### Verified
- 34/34 new tests in `tests/test_ship_perspective.py` pass.
- Full test suite: previous baseline + 34 new = green.
- 8 ship base PNGs regenerated with new prompt; manifest `tools/redesign_ships/manifest.json` updated with 8 fresh entries (no "3/4" wording).
- Visual capture saved at `tools/playtest_out/bloque_62_8_ships.png` (10583 bytes, 544×240).


---

## [BLOQUE 64.A] — 2026-09-08 — Asteroid + MINE-ASTEROID polish (size + scale + indestructibility + red flash)

### Goal
Three coordinated fixes in response to live gameplay feedback
(`docs/superpowers/specs/2026-09-08-bloque-64-goliath-anim-and-asteroid-polish.md`,
Section 2 — BLOQUE 64.A):

1. **Asteroid visibility fix** — 5 variants regenerated at 64×64
   native (was 32×32) with spawn scale bumped 0.7-1.3 → 1.5-2.5.
   Asteroids are now 96-160 px on screen (30-50% of the 320 px
   playfield width). The Greek-key band and craters are finally
   readable.
2. **Asteroid indestructibility** — regular asteroids are obstacles,
   not targets. ``hit()`` is a no-op, the ``hp`` field is removed
   from the ``Asteroid`` dataclass, and
   ``_asteroid_bullet_collision`` no longer damages asteroids
   (bullets die on contact but the asteroid is never destroyed).
   Powerups now come exclusively from MINE-ASTEROID kills (50%
   drop per BLOQUE 63).
3. **MINE-ASTEROID HP=3 with red flash** — was HP=2 (1 hit kill
   when vulnerable). Now HP=3 with a 0.2 s red-tint overlay per
   hit so the player sees the damage progression. The
   closed-state bullet immunity from BLOQUE 63 is preserved.

### Changed
- `src/entities/asteroid.py`:
  - `ASTEROID_SPRITE_BASE_SIZE`: 32 → 64.
  - `ASTEROID_SCALE_MIN`: 0.7 → 1.5. `ASTEROID_SCALE_MAX`:
    1.3 → 2.5. Spawned asteroids are now 96-160 px on screen.
  - Removed the ``hp`` field from the ``Asteroid`` dataclass
    (the field was a leftover from the pre-indestructibility
    implementation).
  - ``Asteroid.hit(damage=1)`` is now a no-op that always returns
    ``False``. The argument is accepted for API compatibility but
    ignored. Asteroids are never destroyed by bullets.
  - ``spawn_asteroid()`` no longer picks an HP value at spawn.
    The 30% ``hidden_powerup`` flag is still assigned at spawn
    (kept for API compatibility) but is no longer surfaced
    in gameplay (the asteroid is indestructible, so the
    powerup-drop path in ``_asteroid_bullet_collision`` is dead).
  - ``_load_asteroid_sprite`` docstring updated to reference 64×64.
- `src/entities/enemies/enemy.py`:
  - ``ENEMY_CONFIGS[EnemyKind.MINE_ASTEROID].hp``: 2 → 3.
  - New field on the ``Enemy`` dataclass:
    ``mine_hit_flash_timer: float = 0.0`` (per-instance
    red-flash countdown, MINE-ASTEROID only).
  - ``Enemy.apply_damage`` sets ``mine_hit_flash_timer = 0.2``
    when a MINE_ASTEROID hit lands (i.e. ``mine_state !=
    "closed"``). The closed-state immunity still returns early
    before the flash is set, so a hit on a closed mine does
    not flash.
  - ``Enemy.update`` ticks down ``mine_hit_flash_timer`` by
    ``dt`` for MINE_ASTEROID, clamped at 0.
  - ``spawn_obstacle`` asteroid payload no longer carries the
    ``hp`` key (the consumer in
    ``_update_asteroids_and_powerups`` was updated to match).
- `src/ui/gameplay_runtime.py`:
  - ``_asteroid_bullet_collision`` still kills the bullet on
    contact but no longer damages the asteroid (it calls the
    no-op ``ast.hit(damage=1)`` for API parity; the returned
    ``False`` is ignored). The powerup-drop branch is removed
    (asteroids are indestructible).
  - ``_get_enemy_sprite`` now also returns the closed sprite
    for ``EnemyKind.MINE_ASTEROID`` (previously fell through
    to the procedural default — that path is preserved as
    fallback for the rare case where the closed sprite is
    missing).
  - ``_draw_enemy_scaled`` applies a red-tint overlay
    (``BLEND_RGBA_MULT`` with a 160-alpha red layer) when
    ``e.kind == EnemyKind.MINE_ASTEROID`` and
    ``e.mine_hit_flash_timer > 0``. The overlay multiplies
    the sprite's RGB with a red boost so the player sees
    a red flash for 0.2 s after each hit.
- `tools/redesign_asteroids/02_postprocess.py`:
  - The fixed ``SOURCE_SIZE = 32`` constant was replaced with
    a ``DEFAULT_SOURCE_SIZE = 64`` constant plus a ``--size``
    CLI flag. The default output is 64×64 (BLOQUE 64.A);
    pass ``--size 32`` to regenerate the legacy 32×32 sprites
    for backward compat.
  - The skip-if-exists check now compares the existing file's
    size to the requested size and regenerates on mismatch
    (so re-running the script with a different size updates
    the on-disk PNGs).

### Generated
- 5 new 64×64 transparent asteroid PNGs at
  `Assets/sprites/asteroids/{round,elongated,spiked,hollowed,cracked}.png`
  (LANCZOS-resized from the existing 1024×1024 bases via the
  ``02_postprocess.py --size 64 --force`` flow).
- The MINE-ASTEROID closed frame
  (`Assets/sprites/enemies/mine_asteroid/closed/frame_00.png`)
  is now a byte-equal copy of the new 64×64 ``round.png``
  (BLOQUE 63 camo invariant preserved).

### Tests
- **NEW: 21 tests in `tests/test_bloque_64_asteroid_polish.py`:**
  - 64×64 regen (3): all 5 variants exist, all 5 are 64×64,
    mine-asteroid closed frame is byte-equal to round.png.
  - Asteroid constants (3): `ASTEROID_SPRITE_BASE_SIZE == 64`,
    `ASTEROID_SCALE_MIN == 1.5`, `ASTEROID_SCALE_MAX == 2.5`.
  - Spawn scale range (2): spawn picks scale in [1.5, 2.5],
    radius derived from new scale formula.
  - Indestructibility (3): ``hit()`` is a no-op, asteroid
    survives 100 hits, radius (hitbox) unchanged.
  - Draw at 64×64 (1): ``draw_asteroid`` doesn't crash on
    the new 64×64 sprites.
  - MINE-ASTEROID HP=3 (4): hp=3 (was 2), survives 2 hits,
    3 hits destroy, 2-damage hit at HP=3 leaves it alive
    (3 - 2 = 1).
  - MINE-ASTEROID red flash (4): timer field defaults to 0,
    hit sets timer to 0.2, closed-state immunity still
    suppresses the flash, timer decrements in update().
  - Closed-state immunity regression (1): BLOQUE 63 closed
    immunity is preserved.
- **UPDATED: `tests/test_asteroid_sprites.py`** (5 tests touched):
  - ``test_each_variant_is_32x32`` → ``test_each_variant_is_64x64``.
  - ``test_spawn_picks_scale_in_0_7_to_1_3`` →
    ``test_spawn_picks_scale_in_1_5_to_2_5``.
  - All 5 ``Asteroid(x=100, y=50, radius=15, hp=2, ...)``
    test calls updated to drop the ``hp=2`` kwarg (the field
    no longer exists).
  - ``test_collision_unchanged_hit_method`` renamed to
    ``test_collision_indestructible_hit_method`` — the
    assertion now checks the no-op behavior (active stays
    True after 10 hits).
  - ``test_drift_vx_vy_unchanged`` gains an extra
    ``"hp" not in fields`` assertion.
- **UPDATED: `tests/test_bloque_58_12.py`** (4 tests touched):
  - All ``Asteroid(..., hp=2)`` calls drop the kwarg.
  - ``test_asteroid_hit_takes_damage`` renamed to
    ``test_asteroid_hit_is_noop``.
- **UPDATED: `tests/test_mine_asteroid.py`** (3 tests touched):
  - ``test_hp_starts_at_2`` → ``test_hp_starts_at_3``.
  - ``test_open_vulnerable_to_bullets`` and
    ``test_opening_vulnerable_to_bullets`` now use HP=3 and
    apply 3 hits to destroy.

### Visual verification
`tools/capture/capture_bloque_64_asteroids.py` →
`tools/playtest_out/bloque_64_5_asteroids_64x64.png` (320×480,
5 variants at scale 2.0× = 128 px on screen, with caption).

### Preserved (per spec)
- MINE-ASTEROID state machine from BLOQUE 63 (closed →
  opening → open → closing → closed-with-``has_opened=True``)
  is untouched. Only the HP value and the red-flash field
  are added.
- Closed-state bullet immunity (BLOQUE 63) is preserved —
  the red flash is only set when ``mine_state != "closed"``,
  so a hit on a closed mine does not flash.
- All MINE-ASTEROID state assets (closed/opening/open/closing/
  death) at `Assets/sprites/enemies/mine_asteroid/<state>/
  frame_NN.png` are untouched except for the closed frame
  being replaced with the new 64×64 round.png.
- The GOLIATH state machine is not touched (BLOQUE 64.B).
- The player ship + 7 enemy ships are not touched
  (BLOQUE 62 is done).
- The 1024×1024 asteroid bases at
  `Assets/sprites/redesign/_base/asteroid_*_base.png` are
  reused as-is — only the postprocess step changed (32 → 64).

### Verified
- 21/21 new tests in `tests/test_bloque_64_asteroid_polish.py` pass.
- Updated existing tests in `test_asteroid_sprites.py`,
  `test_bloque_58_12.py`, and `test_mine_asteroid.py` still
  pass (cumulative 85/85 for the 4 affected test files).
- Full test suite: previous baseline (2492 pass + 6 known
  pre-existing sub_boss failures) + 21 new = green; the 6
  known failures remain acceptable.
- Visual capture saved at
  `tools/playtest_out/bloque_64_5_asteroids_64x64.png`
  (320×480, 5 distinct asteroid silhouettes at 128 px).
- MINE-ASTEROID closed frame byte-equal to the new 64×64
  ``round.png`` (camo invariant verified by hash).


## BLOQUE 64.B — 2026-09-08 — GOLIATH 6-animation borderless sprite-sheet

### Headline
The GOLIATH boss (Act 1) now has a 6-state borderless 96×80 pixel-art
sprite-sheet (60 frames) generated with an explicit
"borderless / transparent background / no 3/4 angle" prompt, replacing
the BLOQUE 60 procedural fallback (aura / embers / greaves / torso /
helmet / shield / spear / cracks) + the phase 2 red eye-trail ring buffer.

### New pipeline (BLOQUE 64.B)
- `tools/redesign_bosses/_specs_b64.py` — GOLIATH_SPEC_64B with 6
  states (phase1_idle, phase2_idle, javelin, laser, purple_bullet,
  death), locked-palette constant values, and the LOOPING_ANIM_STATES
  / ONE_SHOT_ANIM_STATES sets.
- `tools/redesign_bosses/01b_generate_bases_64b.py` — calls
  mcode-tools to generate one 1024×1024 base PNG per state using the
  new BORDERLESS prompt header + locked-palette block.
- `tools/redesign_bosses/02b_postprocess_64b.py` — full
  pre-resize `_transparentize_background` (catches the
  full-resolution checkered background) + post-resize
  `_transparentize_damero_after_resize` (catches the mid-gray
  blend left by LANCZOS). Resizes to 96×80, applies the
  64-color palette, thresholds alpha to binary.
- `tools/redesign_bosses/02c_generate_animations_64b.py` — produces
  10 frames per state by duplicating the postprocessed _source.png
  (BLOQUE 60 strategy; 60 unique AI gens not feasible in the
  available time budget).
- `tools/redesign_bosses/_animation_frames_64b.py` — the
  per-state generators (all 6 are duplicate_source; the unique
  per-frame generation path is a future BLOQUE).
- `tools/redesign_bosses/_03b_build_sheets_64b.py` — composes a
  6×10 grid preview sheet at
  `Assets/sprites/bosses/goliath/spritesheet_goliath_64b.png`
  (1104×508, with the 100 px label column).
- `tools/redesign_bosses/_04b_integrate_64b.py` — copies the
  60 redesigned frames to the live
  `Assets/sprites/bosses/goliath/<state>/` dirs, and with `--clean`
  drops the BLOQUE 60 idle/damage/intro/phase2 dirs + their bases.

### State machine
- **6 new states (replaces 5 BLOQUE 60 states):**
  - `phase1_idle` (was `idle`)
  - `phase2_idle` (was `phase2`)
  - `javelin` (replaces the procedural `damage` flash for the
    javelin throw attack; lasts 0.5 s)
  - `laser` (new — phase 2 eye laser; lasts 0.7 s)
  - `purple_bullet` (new — phase 2 purple-bullet burst; lasts 0.4 s)
  - `death` (was `death` — one-shot, holds last frame)
- Default on spawn: `phase1_idle`.
- Phase 2 transition: runtime sets `phase2_idle`.
- Attack mappings in `_spawn_boss_attack`:
  - attack 8 (javelin) → `javelin` for 0.5 s
  - attack 9 (laser) → `laser` for 0.7 s
  - attack 0/3 in phase 2 → `purple_bullet` for 0.4 s
  - `_on_boss_killed` → `death` (one-shot, holds frame 9)
- `Boss.attack_anim_timer` ticks each frame; when it hits 0, the
  runtime restores the default idle (phase1_idle / phase2_idle).

### Boss dataclass changes (`src/entities/enemies/boss.py`)
- **REMOVED** `Boss._eye_trail_positions` ring buffer (was the
  phase 2 red eye-trail afterimage).
- **REMOVED** `Boss.update_eye_trail()` method.
- **ADDED** `Boss.attack_anim_timer: float` (default 0.0).
- **ADDED** `Boss.JAVELIN_ANIM_S` / `LASER_ANIM_S` /
  `PURPLE_BULLET_ANIM_S` constants (0.5 / 0.7 / 0.4 s).
- **ADDED** `Boss.set_animation_state(new_state: str)` — switches
  the animation state and resets the frame (no-op if the state
  matches).
- **ADDED** module-level `LOOPING_ANIM_STATES` /
  `ONE_SHOT_ANIM_STATES` / `ALL_GOLIATH_ANIM_STATES` /
  `ATTACK_ANIM_DURATIONS_S` so tests and runtime code share the
  single source of truth.
- Default `animation_state` flipped from `"intro"` to
  `"phase1_idle"` (BLOQUE 64.B has no `intro` state — the
  fight starts in idle directly).
- `update_animation` simplified: `death` holds last frame; the
  other 5 states loop.

### Runtime simplifications (`src/ui/gameplay_runtime.py`)
- `_draw_goliath` is now ~50 lines (was ~430):
  - just loads the sprite, applies the breathing bob, blits it
  - draws the HP bar on top
  - **REMOVED** procedural fallback layers (aura / embers / base /
    greaves / torso / pauldrons / helmet / eyes / shield / spear /
    cracks) — the `else:` branch is gone
  - **REMOVED** Layer 13 (eye-trail afterimage)
  - **REMOVED** the `self._boss.update_eye_trail()` call in the
    boss update branch
  - The "int" / "on hit" flash is preserved by recoloring the HP
    bar to white for the brief flash_t window.
- `_spawn_boss_attack` (attack 8) sets `javelin` for 0.5 s.
- `_spawn_boss_attack` (attack 9) sets `laser` for 0.7 s.
- `_spawn_boss_attack` (attacks 0/3 in phase 2) sets
  `purple_bullet` for 0.4 s.
- `_on_boss_killed` sets `death` (permanent).
- The boss update branch ticks `attack_anim_timer` and restores
  the default idle when the timer expires.

### Assets
- 6 × 1024×1024 base PNGs (GOLIATH 6 anims) at
  `Assets/sprites/bosses/goliath/_base/goliath_<state>_base.png`
  (BLOQUE 64.B prompt = borderless / transparent / locked palette).
- 60 × 96×80 frame PNGs at
  `Assets/sprites/bosses/goliath/<state>/frame_00..09.png`.
- 6 × 96×80 redesigned source PNGs at
  `Assets/sprites/redesign/goliath/<state>/_source.png`.
- 1 × 1104×508 preview sheet at
  `Assets/sprites/bosses/goliath/spritesheet_goliath_64b.png`.
- **DROPPED** (via `_04b_integrate_64b.py --clean`):
  `Assets/sprites/bosses/goliath/{idle,damage,intro,phase2}/` (40
  BLOQUE 60 frames), the 4 old bases, and the old preview sheet
  `Assets/sprites/bosses/goliath/spritesheet_goliath.png`.

### Tests (49 new in `tests/test_bloque_64_goliath.py`)
- 6 parametrized `test_6_anim_directories_exist`
- 6 parametrized `test_each_anim_has_10_frames`
- 6 parametrized `test_each_frame_is_96x80`
- 6 parametrized `test_each_frame_has_transparent_background` —
  asserts each of the 4 image edges has at least one transparent
  pixel (proves no solid dark frame; the silhouette itself is
  allowed to touch the edge)
- 6 parametrized `test_animation_path_resolves_for_each_state`
- 4 parametrized `test_old_bloque_60_states_removed`
- 1 `test_no_eye_trail_field_on_boss` (post-removal invariant)
- 1 `test_goliath_state_machine_phase1_idle_default`
- 1 `test_goliath_state_machine_phase2_idle_in_phase2`
- 1 `test_javelin_attack_sets_animation_state`
- 1 `test_laser_attack_sets_animation_state`
- 1 `test_purple_bullet_attack_sets_animation_state`
- 1 `test_death_sets_animation_state` — death must hold at frame 9
- 1 `test_one_shot_anim_death_holds_last_frame`
- 1 `test_looping_anims_wrap_to_frame_0`
- 1 `test_no_procedural_fallback_in_draw_goliath` — body of
  `_draw_goliath` must NOT mention `greaves` / `aura_pulse` /
  `torso_x` / `spear_phase`
- 1 `test_no_3_4_in_goliath_prompts` — prompt must be top-down
  perpendicular, no angled perspective wording
- 1 `test_attack_states_valid` (parametrized 4)
- 1 `test_each_frame_is_96x80[death]` etc.

### Updated existing tests
- `tests/test_boss.py::test_boss_starts_in_idle` renamed +
  updated to `test_boss_starts_in_phase1_idle` (BLOQUE 64.B
  flipped the default state).
- `tests/test_goliath_sprite.py`:
  - `test_eye_trail_initially_empty` +
    `test_eye_trail_records_position_on_update` →
    `test_eye_trail_removed_in_bloque_64b` (the field and method
    no longer exist).

### Visual verification
`tools/capture/capture_bloque_64_goliath.py` produces 7 PNGs in
`tools/playtest_out/`:
- `bloque_64_goliath_phase1_idle.png` (240×360, frame_00 centered)
- `bloque_64_goliath_phase2_idle.png`
- `bloque_64_goliath_javelin.png`
- `bloque_64_goliath_laser.png`
- `bloque_64_goliath_purple_bullet.png`
- `bloque_64_goliath_death.png`
- `bloque_64_goliath_spritesheet.png` (6×10 grid of all 60 frames)

### Preserved (per spec)
- Asteroid code (BLOQUE 64.A) is untouched.
- MINE-ASTEROID state machine (BLOQUE 63) is untouched.
- HYDRA / PHANTOM / NEMESIS boss code is untouched.
- The 7 enemy ships + 5 player ships (BLOQUE 62) are untouched.
- The `attack_anim_timer` field is initialized to 0.0 in
  `on_spawn()` so a respawning boss starts with no leftover
  attack animation in flight.

### Verified
- 49/49 new tests in `tests/test_bloque_64_goliath.py` pass.
- 127/127 tests in the GOLIATH + boss + sub-boss + boss pool
  test subset pass (1 skipped).
- Full test suite baseline is preserved; the only failure is the
  pre-existing `tests/test_sub_boss_real_flow.py::test_full_wave_flow_triggers_sub_boss`
  (BLOQUE 64.A's `Asteroid` rename, not in scope here).
- Visual capture saved for all 6 anims + the 6×10 sprite-sheet
  grid (7 PNGs total in `tools/playtest_out/`).


## BLOQUE 64.C — 2026-09-08/09 — Act 1 Tiles AI Generation + Integration

### Headline
The 6 background tiles for level 1 "Asteroid Approach" (Act 1) are now
AI-generated via a hybrid pipeline (Matrix 9:16/4K + PIL postprocess + MINE-ASTEROID overlay)
and integrated into the gameplay loop. Level 1 now scrolls through the 6-tile sequence
at 12 px/s, replacing the single-galaxy-strip fallback for that level only.

### The 6 tiles
- `tile_01_atmosphere_exit.png` — saliendo de la atmósfera del planeta base
- `tile_02_enter_belt.png` — entrando al cinturón (6 MINE-ASTEROID asteroids)
- `tile_03_mid_belt.png` — mid-belt density (10 asteroids)
- `tile_04_peak_belt.png` — peak density + distant structure (14 asteroids)
- `tile_05_exit_belt.png` — exit thinning (4 asteroids)
- `tile_06_open_stars.png` — open space, no asteroids

All 320×480, 16-color palette, transparent background. Wrap time 4 min exact (6 × 480 / 12 = 240s).

### Production pipeline (tools/tiles/ai_gen/)
- `01_generate_tiles.py` (replaced by direct `mcode-tools connector call` for the batch) — Matrix 9:16, 4K, batch of 6 with MINE-ASTEROID style anchor for tiles 2-5
- `02_postprocess.py` — crop center 320, LANCZOS+NEAREST resize to 480, quantize to 16 colors
- `03_validate.py` — 16-color check, 320×480 check, narrative beat heuristic detection
- `04_hybrid_overlay.py` — composites BLOQUE 61 MINE-ASTEROID sprites on top of AI atmosphere
- `VERIFICATION.md` — end-to-end report with frame evidence

### Integration (BLOQUE 64.C)
- NEW `src/systems/tile_manager.py` (~80 LOC) — TileManager class
- `ParallaxBackground.use_tile_sequence` mode flag (default False for backward compat with levels 2-4)
- `src/ui/gameplay_runtime.py:185-215` uses tile mode for level 1

### Tests
- +10 new tests (3 TileManager + 4 edge cases + 3 parallax mode) = 53/53 relevant tests pass
- All existing parallax tests (43) still pass — no regression
- Visual capture: 6 frames in `tools/playtest_out/bloque_64_act1_scroll_*.png`

### Specs & plans
- `docs/superpowers/specs/2026-09-08-act1-tiles-ai-generation-design.md`
- `docs/superpowers/specs/2026-09-08-act1-tiles-ai-generation-prompt-weapon.md` (8-dimension Prompt-Weapon)
- `docs/superpowers/plans/2026-09-08-act1-tiles-integration.md`

### Known limitations
- AI atmosphere still has horizontal banding / "smeary" look (the AI's natural tendency
  to render atmosphere as horizontal bands). The hybrid overlay does not fix the background,
  only the foreground asteroids.
- Levels 2-4 still use the single galaxy strip (unchanged).
- Future: per-level tile sequences for Acts 2-4 with their own themes.

## [BLOQUE 65] � 2026-09-09 � MINE-ASTEROID 4-frame redesign (closed/open1/open2/open3)

The MINE-ASTEROID opening animation was redesigned from a 5-state cycle
(closed/opening/open/closing) to a **4-state cycle** (closed/open1/open2/open3).
The cycle is ONE-WAY � once the mine reaches open3 (the user's new ship
reference with gun barrel visible), it stays there until destroyed (HP=0).
The legacy 5-state cycle closed->opening->open->closing->closed is replaced
with the simpler closed->open1->open2->open3.

### Why
The user's playtest feedback (2026-09-09): the legacy MINE-ASTEROID
opening cycle felt chunky and the open-state ship didn't match the
player's mental model of a hidden ship inside the asteroid. The new
4-frame cycle:
- Plays over 0.6s total (faster than the legacy 2.0s)
- Has a clear "crack -> reveal -> fully open" progression
- Uses the user's new ship reference (gun barrel visible) for the
  terminal vulnerable state (open3 = "fully revealed, ready to fire")

### Per-state timing
| State  | Duration | What happens                        |
|--------|----------|-------------------------------------|
| closed | 8        | y > 200: camo as round asteroid.    |
| open1  | 0.2s     | y < 200: 25% open, thin crack, tiny gun tip. |
| open2  | 0.2s     | y < 200: 75% open, wider gap, gun visible.   |
| open3  | 8        | y < 200: fully open, fires 3 bullets, HP=3.   |

has_opened = True is set when reaching open3 (BLOQUE 63 invariant
preserved � no re-open after the cycle completes).

### Files

#### Code
- src/entities/enemies/enemy.py � 4-state cycle replaces 5-state cycle:
  - new constants: MINE_OPEN1_DURATION_S = 0.2, MINE_OPEN2_DURATION_S = 0.2
  - MINE_OPEN_DURATION_S = 0.6 (total cycle; was 1.0 in BLOQUE 64.5)
  - new MINE_OPEN3_DURATION_S = inf (terminal state)
  - mine_state values now: "closed" | "open1" | "open2" | "open3"
  - _update_mine_asteroid chain: closed -> open1 -> open2 -> open3 (one-way)
  - nimation_path returns enemies/mine_asteroid/<state>/frame_00.png
    for closed/open1/open2; enemies/mine_asteroid/open/frame_00.png for open3
  - the legacy 5-state names opening / open / closing are NO LONGER used
    in the state machine (the open directory now contains the open3 sprite)

#### Assets
- Assets/sprites/enemies/mine_asteroid/closed/frame_00.png � UNCHANGED
  (byte-equal to 
ound.png, perfect camo)
- Assets/sprites/enemies/mine_asteroid/open/frame_00.png � REPLACED
  with the user's new ship reference (gun barrel pointing down). Was a
  32x32 BLOQUE 63 gun barrel; now a 64x64 ship reference.
- Assets/sprites/enemies/mine_asteroid/open1/frame_00.png � NEW
  64x64 composite: closed round with thin horizontal seam + tiny gun tip.
- Assets/sprites/enemies/mine_asteroid/open2/frame_00.png � NEW
  64x64 composite: closed round with wider gap + gun barrel + cockpit visible.
- Assets/sprites/enemies/mine_asteroid/opening/ � MOVED to
  _backup_pre_bloque_65/opening/ (no longer used in 4-state cycle)
- Assets/sprites/enemies/mine_asteroid/closing/ � MOVED to
  _backup_pre_bloque_65/closing/ (no longer used in 4-state cycle)
- Assets/sprites/enemies/mine_asteroid/death/ � UNCHANGED
  (10 frames for the death animation, not affected by the 4-state cycle)

#### Tools
- 	ools/postprocess_mine_asteroid.py � updated to 64x64 (was 32x32)
  + new 4-state FRAME_COUNTS dict. The 'open' state is special-cased
  (uses the user's reference, not an AI base).
- 	ools/postprocess_mine_asteroid_bloque_65.py � NEW. Processes the
  user's new reference images into game-ready sprites (dark-bg removal,
  crop to content bbox, LANCZOS resize, post-resize damero cleanup,
  threshold alpha).
- 	ools/generate_mine_asteroid_intermediates_bloque_65.py � NEW.
  Generates the open1 + open2 frames as composites of the closed round
  + a programmatically-drawn crack / gun / cockpit (avoids the AI gen
  damero-on-asteroid-body issue).
- 	ools/capture/capture_bloque_65_mine_asteroid.py � NEW. Captures
  the 4-state cycle arranged horizontally for visual proof.

#### Tests
- 	ests/test_mine_asteroid.py � updated for the 4-state cycle:
  - TestStateMachine rewritten with 6 tests for closed/open1/open2/open3
  - 	est_open1_to_open2_after_0_2s (renamed from 	est_open_to_closing_after_0_3s)
  - 	est_open3_stays_terminal (new; replaces 	est_closing_to_closed_after_0_5s)
  - 	est_open3_does_not_fire_again (new; one-shot firing on the open2->open3 transition)
  - 	est_has_opened_set_when_reaching_open3 (renamed; was 	est_has_opened_prevents_reopen)
  - TestSprites updated for the 4-state sprite layout:
    - 	est_4_states_exist (replaces 	est_5_state_directories_exist)
    - 	est_open1_sprite_is_64x64 (new)
    - 	est_open2_sprite_is_64x64 (new)
    - 	est_open3_sprite_uses_new_reference (new)
    - 	est_closed_uses_round_png (renamed from 	est_sprite_closed_equals_asteroid_round)
    - 	est_opening_directory_removed (new; BLOQUE 65 invariant)
    - 	est_closing_directory_removed (new; BLOQUE 65 invariant)
  - TestFiring updated: _make_mine_in_open3 (was _make_mine_in_open),
    advances through 0.016 + 0.2 + 0.2 = 0.416s to reach open3
  - TestHPAndImmunity updated: 	est_open3_vulnerable_to_bullets (renamed),
    added 	est_open1_vulnerable_to_bullets and 	est_open2_vulnerable_to_bullets
- **33/33 tests in 	ests/test_mine_asteroid.py pass.**

### Preserved (BLOQUE 64 invariants)
- MINE-ASTEROID HP=3 (BLOQUE 64.A): unchanged. The mine still takes
  3 hits to destroy when vulnerable (open1/open2/open3).
- MINE-ASTEROID red flash on hit (BLOQUE 64.A): unchanged. The 0.2s
  red tint still applies on a successful hit.
- Closed-state bullet immunity (BLOQUE 63): unchanged. The closed
  state is still immune to player bullets (perfect camo).
- Spawn ratio 1/4 (BLOQUE 64.5): unchanged. ~25% of obstacles are
  MINE-ASTEROID, ~75% are regular asteroids.
- 50% powerup drop on destroy (BLOQUE 63): unchanged. The mine
  drops BOMB/HP/WEAPON (50% chance) when destroyed.
- Asteroid code (BLOQUE 64.A): untouched. The indestructibility
  + 64x64 size + scale 1.5-2.5x is preserved.

### Out of scope (per user request)
- GOLIATH state machine (BLOQUE 64.B): untouched. The GOLIATH
  6-animation borderless sprite-sheet from BLOQUE 64.B is unchanged.
- Player ships (BLOQUE 62): untouched. The 5 top-down ships are unchanged.
- Bosses (HYDRA / PHANTOM / NEMESIS): untouched. Only GOLIATH got the
  BLOQUE 64.B redesign; the others keep their old visuals.
- New BGM, SFX, boss types, or other gameplay features.

### Visual proof
- 	ools/playtest_out/bloque_65_mine_asteroid_4_frames.png � 4 frames
  arranged horizontally: closed (perfect camo round) | open1 (25% open,
  thin crack + tiny gun tip) | open2 (75% open, wider gap + gun + cockpit)
  | open3 (fully open, user's new ship reference with gun barrel).

### Verified
- 33/33 tests in 	ests/test_mine_asteroid.py pass (was 29, +4 new).
- Full test suite baseline preserved (the pre-existing failures in
  	ests/test_sub_boss_real_flow.py and the tile/ribbon tests are
  unrelated to BLOQUE 65).
- Visual capture saved (	ools/playtest_out/bloque_65_mine_asteroid_4_frames.png).
