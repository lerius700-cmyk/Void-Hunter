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
- untime.py: spawn_pattern_wave() tracks leader_enemy_ids in
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

