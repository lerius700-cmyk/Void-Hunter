# VOID HUNTER — Roadmap

**Last updated:** 2026-08-15
**Current version:** v1.27 (last release)
**In progress:** v1.28 (4 BLOQUES, awaiting release decision)

---

## Now (in progress)

### Visual polish
- ✅ Galaxy background scroll (BLOQUE 58.6w, 58.7ad)
- ✅ Sub-boss visibility (BLOQUE 58.7x, 58.7ab, 58.7ac)
- ✅ HUD at BOTTOM (BLOQUE 58.7ab)
- ✅ DASH afterimage restored (BLOQUE 58.7aa)
- ✅ Ultra-neon propulsion (BLOQUE 58.6y)

### Audio
- ✅ Streaming BGM (BLOQUE 58.45)
- ✅ SAPI voices removed (BLOQUE 58.59)
- ✅ Music no restart on sub-boss (BLOQUE 58.6y)

### Performance
- ✅ 1,024 / 1,024 tests passing
- ✅ 120 FPS lock
- ✅ Zero numpy/scipy

---

## Next (4-6 weeks)

### More enemy variety
- [ ] Add 2 more enemy archetypes (BOMBER, MINELAYER)
- [ ] More bezier paths for O3, O4
- [ ] Multi-wave boss patterns

### Boss 2
- [ ] Second mid-boss dart (variation of BLOQUE 50)
- [ ] Boss intro cinematic (cutscene)

### Polish
- [ ] Refactor `gameplay_runtime.py` (5,773 → ~3,000 LOC)
- [ ] Type hints coverage
- [ ] Public API docs (sphinx)

---

## Later (3-6 months)

### Gameplay depth
- [ ] **Act 2** — new level, new enemies, new boss
- [ ] **Power-ups** — more variety (currently limited)
- [ ] **Leaderboard / highscore persistence** (JSON → SQLite)
- [ ] **Mode historia** with cinematics
- [ ] **Achievements** (Steam-style)

### Polish
- [ ] **Difficulty levels** (easy/normal/hard unlockable)
- [ ] **Settings menu** (volume, controls, graphics)
- [ ] **Mod support** (roguelike is foundation)

### Distribution
- [ ] **Steam release** (achievements, leaderboards, workshop)
- [ ] **Itch.io release** (early access)
- [ ] **Multiplayer local** (2-player co-op)
- [ ] **Linux + Mac builds** (PyInstaller supports)

---

## Backlog (open-ended)

### Tech debt
- [ ] Modularize `gameplay_runtime.py` into `ui/draw/` modules
- [ ] Move hardcoded magic numbers to `settings.py`
- [ ] Add type hints to all public APIs
- [ ] Sphinx-generated API docs

### Gameplay
- [ ] More wave types (carrier, swarm, kamikaze wave)
- [ ] Bullet hell patterns for bosses
- [ ] Combo system (chain kills for multiplier)
- [ ] More sub-boss variants (3 total: dart, hunter, etc.)

### Polish
- [ ] Animated title screen
- [ ] Options menu
- [ ] Pause menu with controls reference
- [ ] Steam Cloud save

### Rejected (out of scope for now)
- ❌ Mobile port (touch controls complex, pygame not ideal)
- ❌ Online multiplayer (scope creep, scope of single game)
- ❌ VR mode (out of scope, not target platform)

---

## Release policy

- **v1.28** — awaiting user decision. 4 BLOQUES accumulated (58.7aa-58.7ad).
  Critical fix: sub-boss visibility (58.7ac root cause).
- **User controls release cadence** — no auto-bundling.
- **Each release is a `.zip` in `releases/`** (gitignored).
- **v1.0 → v1.27** already shipped (26 zips total).

---

*Last updated: 2026-08-15*
