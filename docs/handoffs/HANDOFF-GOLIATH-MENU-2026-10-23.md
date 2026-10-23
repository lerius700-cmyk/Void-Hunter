# GOLIATH + Main Menu — Consolidated Session Record

> **Scope**: everything BLOQUE 73.1 → 73.7 landed on `master`. This document
> is the single authoritative map of the GOLIATH and main-menu work.
>
> **It supersedes `docs/GOLIATH_HANDOFF.md`**, which was frozen at v1.6.2
> (BLOQUE 73.5) and therefore has no knowledge of the background selector
> (73.6) or the post-cinematic main menu (73.7). Keep that file for history;
> work from this one.

---

## 1. Where you are when you start

- **Repo**: `https://github.com/lerius700-cmyk/Void-Hunter`
- **Branch**: `master` at `a8bf14f`
- **Latest tag**: `v1.6.3` at `e5a67fc`
- **Latest release**: https://github.com/lerius700-cmyk/Void-Hunter/releases/tag/v1.6.3
- **Built artifacts**: `dist/void-hunter.exe`, `dist/VoidHunter-v1.6.3-win64.zip`

```bash
git log --oneline --since="2026-10-20"
```

---

## 2. What this session actually produced

Two things, both shipped:

1. **GOLIATH became a real animated boss with a visible, warming shield.**
   Before this session it had a full shield *mechanic* (state machine,
   collision handling, laser) shipped since BLOQUE 53a, but the shield was
   never *drawn* — so the player was eating hits from an invisible oval.
   Its 60 animation frames had been silently reverted to 6 stills by a
   later commit, and `Boss.update_animation()` had never been called by
   anything. The animation code was correct and inert.

2. **A post-cinematic main menu** with `NEW GAME` / `BOSS TIME` /
   `BACKGROUND`, where `BACKGROUND` opens a submenu with `SPACE VOID` and
   `ASTEROID NEBULA`.

---

## 3. The BLOQUE ladder

| BLOQUE | Commit | Release | Symptom → root cause → fix |
|---|---|---|---|
| 73.1 | `0985ccc` | v1.5.1 | Game crashed on launch → `Assets/background/tiles/act1/` was never committed, and `TileManager` raised `FileNotFoundError` from its constructor → it now degrades to `available=False` and draws nothing |
| 73.2 | `65a1a7e` | v1.5.1 | Shield hitbox consumed bullets with no visual → `_draw_goliath_shield()` never existed → added: translucent oval on the arm, iron→blue→cyan charge ramp |
| 73.3 | `60a9836` | v1.6.0 | "GOLIATH looks cut off" → not an anchor bug: commit `562eb58` shipped 10 *byte-identical* copies per animation, silently reverting BLOQUE 65's regen → `git checkout ac53596 -- Assets/sprites/bosses/goliath/` restored 60 distinct frames. No code change |
| 73.4 | `6c71e1b` | v1.6.1 | Eye laser spawned 2-6px below the eye ("comes from the chest") → fixed offset `boss.y + 30` → `get_sprite_eye_anchor()` per-frame by colour signature. Plus 7 re-padded frames, plus shield hitbox rebuilt from `max(R,RX)+1` × `max(R,RY)+1` |
| 73.5 | `c6679b4` | v1.6.2 | Boss held frame 0 forever → `Boss.update_animation()` had **no caller anywhere** in `src/` or `main.py` → wired into `GameplayRuntime._update_boss`. And `--boss` was a stub that printed "full integration in next BLOQUE" → `_cmd_play()` now walks `TITLE → ACT_INTRO → GAMEPLAY → BOSS_INTRO → BOSS_FIGHT` |
| 73.6 | `e553189` | v1.6.3 | Background variant selector on the title screen → `src/core/game.py` + `src/ui/scenes.py` |
| 73.7 | `cfa8e22` | v1.6.3 | Post-cinematic main menu → new `MainMenuScene`, new `GameState.MENU`, `TitleScene` chains into it instead of `ACT_INTRO` |

Release-notes commits: `c556d93` (v1.5.1), `e948c40` (v1.6.0), `611314a`
(v1.6.1), `1808e07` (v1.6.2), `e5a67fc` (v1.6.3).

---

## 4. GOLIATH anatomy — the four things that must stay wired

This is the chain that made the bug invisible: each piece existed
separately and correctly, and nothing connected them.

```
main.py  --boss goliath
  └─ _cmd_play() walks TITLE → ACT_INTRO → GAMEPLAY → BOSS_INTRO → BOSS_FIGHT
       └─ BossFightScene.on_enter builds GameplayRuntime(is_boss=True)
            └─ _update_boss(dt): boss.update(dt) THEN boss.update_animation(dt)   ← 73.5
                 └─ Boss.animation_path → bosses/goliath/<state>/frame_NN.png
                      └─ _goliath_shield_center(runtime)
                           = get_sprite_arm_anchor(path)
                           + get_sprite_centroid_offset(path)
                           + GOLIATH_SHIELD_*
                           ├─ consumed by _draw_goliath_shield()      ← visual  (73.2)
                           ├─ consumed by _handle_shield_collisions() ← hitbox  (73.4)
                           └─ consumed by the eye laser via get_sprite_eye_anchor()  (73.4)
```

**One anchor, three consumers.** If `_goliath_shield_center` stops being
shared, the visual and the hitbox drift apart again — that is exactly the
invisible-shield bug of 73.2, inverted.

### Sacred constants

User-approved at `0837a86`. **Do not change without explicit approval.**

```python
GOLIATH_SHIELD_DX = -11
GOLIATH_SHIELD_DY = 6
GOLIATH_SHIELD_R  = 11
GOLIATH_SHIELD_RX = 11
GOLIATH_SHIELD_RY = 17
GOLIATH_SHIELD_MAX_HITS = 20
```

The verdict, in the user's words: *"el ovalo esta dentro de la silueta del
escudo, y se ve bastante bien"*. The charge ramp is iron → blue → cyan.

---

## 5. Main menu

`MainMenuScene` in `src/ui/scenes.py:937`. It appears **after** the
cinematic, before any wave fires.

```
TitleScene --finish--> GameState.MENU --> MainMenuScene
                                            |
                    +-----------------------+-----------------------+
                    |                       |                       |
              NEW GAME               BOSS TIME              BACKGROUND
                    |                       |                       |
              ACT_INTRO              BOSS_INTRO            _layer = "bg"
                    |                       |                       |
               GAMEPLAY               BOSS_FIGHT        SPACE VOID (0)
                                                         ASTEROID NEBULA (1)
```

- `_ITEMS_TOP = ("NEW GAME", "BOSS TIME", "BACKGROUND")`
- `_ITEMS_BG  = ("SPACE VOID", "ASTEROID NEBULA")`
- `_bg_cursor` defaults to **1** (`ASTEROID NEBULA`) — that is the look the
  user approved, matching v1.4.0. Do not reset it to 0.
- Up/Down navigate · Enter activates · Esc returns to TITLE.
- The `BACKGROUND` submenu intercepts its keys **before** the top-level
  `K_1`/`K_2` shortcuts, otherwise `1`/`2` inside the submenu would jump
  to NEW GAME / BOSS TIME instead of toggling the background.
- `BOSS TIME` uses its own boss arena background; only the gameplay
  backdrop changes with the bg mode.

### Background semantics

| Mode | id | What it is |
|---|---|---|
| `SPACE VOID` | 0 | parallax starfield / falling star dust, no procedural strip |
| `ASTEROID NEBULA` | 1 | `ScrollingGalaxyBackground`, the rich purple procedural strip (default) |

---

## 6. Verification

```powershell
$env:SDL_AUDIODRIVER = "dummy"
$env:SDL_VIDEODRIVER = "dummy"
python main.py --boss goliath --easy --duration 60
```

Expected last line: `VOID HUNTER: jumped to GOLIATH (act 1)`

```powershell
python -m pytest tests/ -k "boss or goliath or shield or javelin or menu or bg_variant" `
  --ignore=tests/test_paths_legacy.py -q --tb=no
```

Expected: **243 passed, 1 skipped** (244 selected, 0 failed) — verified
2026-10-23.

Full suite:

```powershell
python -m pytest tests/ --tb=no
```

Expected: **2,791 passed, 8 failed, 6 skipped** (2,805 total) — verified
2026-10-23. Down from 2,700 pass + 23 fail at the start of BLOQUE 73.

> **Do not add a second `-q`.** `pyproject.toml` already sets
> `addopts = "-q --strict-markers --tb=short"` (line 63). Passing `-q`
> again makes it `-qq`, which **silences the summary line entirely** —
> the dots print and you get no `N passed` at all. Read the counts off the
> progress bar, or pass `--tb=no` alone.

### The background-selector regression net

```powershell
python -m pytest tests/test_bg_mode_render.py --tb=no
```

Expected: **5 passed**. These are the pixel tests the BLOQUE 73.6 spec
demanded and that never existed — see §11.2.

### Frames are still 60 unique files

```powershell
foreach ($a in phase1_idle,phase2_idle,javelin,laser,purple_bullet,death) {
  $h = Get-ChildItem "Assets/sprites/bosses/goliath/$a/frame_*.png" |
       ForEach-Object { (Get-FileHash $_.FullName -Algorithm MD5).Hash }
  Write-Host "$a $(@($h | Sort-Object -Unique).Count)/10"
}
```

Expected `10/10` on all six (verified 2026-10-23).

---

## 7. What NOT to do

- **Don't change the `GOLIATH_SHIELD_*` constants.** Approved at BLOQUE
  66.4o. The BLOQUE 66.5 values (`DX=-2, DY=0, RX=7, RY=10`) are the
  rejected ones.
- **Don't regenerate GOLIATH frames with AI.** The 60 `ac53596` frames are
  the product of *"tantísimo esfuerzo"*. Earlier regens repeatedly
  produced debris and forced a backplate workaround.
- **Don't reintroduce the backplate.** BLOQUE 66.4e/66.4g tried a
  translucent silhouette beneath the sprite to fill AI gaps; it produced
  a visually doubled boss. The user's verdict: *"corrige eso para que
  solo haya uno"*. It is gone.
- **Don't bump the major version without asking.** v1.6.3 is the current
  release.
- **Don't default `bg_mode` to 0.** `ASTEROID NEBULA` (1) is the
  user-approved look.

---

## 8. File map

| File | What matters |
|---|---|
| `src/ui/gameplay_runtime.py` | GOLIATH draw, shield hitbox, eye laser, the `GOLIATH_SHIELD_*` constants, the `update_animation` call |
| `src/ui/scenes.py` | `MainMenuScene`, `get_sprite_arm_anchor`, `get_sprite_centroid_offset`, `get_sprite_eye_anchor`, `TitleScene` → `GameState.MENU` |
| `src/core/game.py` | bg_mode plumbing |
| `src/core/scene_manager.py` | `GameState.MENU` |
| `src/entities/enemies/boss.py` | `Boss.update_animation` (BLOQUE 64.B — correct all along, just uncalled) |
| `src/systems/tile_manager.py` | graceful degradation (73.1) |
| `main.py` | `_cmd_play` scene walk for `--boss` (73.5) |
| `Assets/sprites/bosses/goliath/` | 60 distinct frames from `ac53596` |
| `tests/test_goliath_anchor_coincidence.py` | 73.4 — anchor/hitbox/visual agree |
| `tests/test_goliath_animation_advances.py` | 73.5 — animation actually advances |
| `tests/test_bg_variant_selector.py` | 73.6 |
| `tests/test_main_menu_scene.py` | 73.7 |
| `tests/test_tile_manager.py` | 73.1 |
| `docs/superpowers/specs/2026-10-22-prompt-weapon-goliath-port-v1-4-0.md` | Prompt-Weapon 8D to port this back into a v1.4.0 (BLOQUE 71) base. Commit `a8bf14f` |

---

## 9. Known open issues

### The 8 remaining test failures are all pre-existing

None were introduced by BLOQUE 73.1→73.7. Verified by running the same
files in a clean `git worktree` at v1.6.2 (`1808e07`) — they failed there
too.

| Test | Cause | Status |
|---|---|---|
| `test_sub_boss_full_flow.py` × 4 | **Order-dependent pollution.** Pass in isolation, fail in the full suite | Pre-existing |
| `test_sub_boss_real_flow.py` × 1 | Same | Pre-existing |
| `test_asteroid_sprites.py` × 2 | Same | Pre-existing |
| `test_paths.py::test_paths_no_star_shapes` | Real geometry assertion: `LissajousPath` tangent rotates 150.9° at t=0.17 (star spike) | Pre-existing |

The 5 sub_boss + 2 asteroid failures need a *fix*, not an update: something
leaks state between test modules. Root cause not yet found. `ISSUE-002`
below is separate.

### ISSUE-002 — hardcoded `D:\AI\void-hunter\` paths

The repo lives at `F:\AI\MM\void-hunter\`. Some tests still assume the old
path. Fix is mechanical: `Path(__file__).resolve().parent.parent`.

> One instance of this was already fixed on 2026-10-23: the module docstring
> in `src/audio/music.py` contained `D:\AI\void-hunter\Assets\*.wav`, whose
> `\A` is an invalid Python escape sequence. That made
> `test_music_module_imports_clean` fail with `SyntaxError` on
> `py_compile`. The docstring now documents the *real* resolution
> (`Path(__file__).resolve().parent.parent.parent`), and the test passes.

### ISSUE-003 — `CLAUDE.md` version string is stale

Fixed 2026-10-23: now reads `v1.6.3`.

### ISSUE-004 — smoke test needs a display in CI

`python main.py --boss goliath` opens a window. Headless CI needs
`SDL_VIDEODRIVER=dummy`, but the smoke test also asserts on screen output,
so it does not fully run headless yet.

See `docs/KNOWN_ISSUES.md` for the live list.

---

## 10. If something is wrong

If `--boss goliath` doesn't print `jumped to GOLIATH (act 1)`, or GOLIATH
looks frozen, or the shield is invisible again: walk the chain in §4
top-down. `tests/test_goliath_anchor_coincidence.py` and
`tests/test_goliath_animation_advances.py` are the regression net for
exactly these failures.

---

## 11. Session consolidation — 2026-10-23

A second pass over the same session, this time with three auditing tools
(`synapse-deep`, `sf-sm-doctor`, `gstack-review`) instead of manual
inspection. It found a **shipped functional defect** in v1.6.3.

### 11.1 What the tools found

| Tool | Result |
|---|---|
| `synapse-deep` | Updated `CLAUDE.md`, `CONTEXT.md`, `.synapse`; fixed 4 broken doc paths, 6 duplicated rows in the Switch's bridge table, 2 stale path references |
| `sf-sm-doctor` | **4/7 → 7/7**, 0 findings. The gap was `docs/handoffs/CONTEXT.md` missing its Token Budget section |
| `gstack-review` | Gate scan: `listed=4 eligible=4 tagged={}` — no RH-* relaxation tags fired. Shell injection: clean. `.gitignore`: no tracked file newly ignored |

### 11.2 CRITICAL — the BACKGROUND menu option never worked

`GameState.MENU` and the `bg_mode` draw branch shipped in v1.6.3. The
selector was **functionally inert in gameplay**: the menu wrote
`Game.bg_mode`, and the runtime read it — through a back-reference that
was never there.

`GameplayRuntime` is **not** a `Scene`, so it never received the `_game`
that `_register_with_back_ref()` (`src/core/game.py:277-279`) injects
into scenes. `getattr(self, "_game", None)` was always `None`, so
`bg_mode` was always the default `1` and the `bg_mode == 0` branch was
dead code. Choosing SPACE VOID changed nothing on screen.

Two compounding bugs:

1. **Root cause** — the runtime had no `_game`. Fixed in
   `src/ui/scenes.py` `GameplayScene.on_enter()` by handing the
   back-reference to the runtime before `on_enter()` runs.
2. **Composition** — mode 1 drew only the galaxy strip. The parallax
   layer had been moved *inside* the `bg_mode == 0` branch, so the
   nebula lost the "galaxy + parallax encima" composition the spec and
   the v1.6.3 release notes both specify. Fixed in
   `src/ui/gameplay_runtime.py`.

Measured before and after (320×480 frame, full runtime draw):

| | non-black px | bright px |
|---|---|---|
| mode 0 (SPACE VOID) | 9,700 | 8,782 |
| mode 1 (ASTEROID NEBULA) | 153,584 | 34,791 |

**93.99%** of the frame now differs between the two modes. Before the
fix the difference was ~0%.

> This is the same failure class as the historical "no tiene fondo" bug
> (BLOQUE 73.7): the background was *updated* every frame but the pixels
> never reached the screen. The spec even demanded a pixel-comparison
> test for exactly this — and that test never existed, which is why two
> releases shipped the defect.

### 11.3 The test net that was missing

`tests/test_bg_mode_render.py` (5 tests) now locks:

1. The runtime holds the `_game` back-reference (the root cause).
2. `bg_mode` 0 and 1 render measurably different frames (>50% of bytes).
3. The nebula is meaningfully denser than Space Void.
4. The galaxy strip is loaded **and** actually draws (>50% lit pixels).
5. The menu's choice is the value the runtime reads.

Verified as a real regression net: with the fix reverted, 4 of the 5
fail; with it applied, 5/5 pass.

### 11.4 Also fixed in this pass

| Item | Where | What |
|---|---|---|
| `SyntaxError: invalid escape sequence '\A'` | `src/audio/music.py` module docstring | The docstring documented a stale `D:\AI\void-hunter\Assets\*.wav` path. `py_compile` turned the invalid escape into a hard failure. It now documents the *real* resolution (`Path(__file__).resolve().parent.parent.parent`) |
| 4 tests failing on `GameState.MENU` | `tests/test_game_state_machine.py`, `tests/test_cinematic_scene.py` | They still encoded the pre-73.7 expectation (`CINEMATIC → ACT_INTRO`). Now expect `MENU`, and additionally assert `ACT_INTRO` is **not** reached, so the menu's interception is proven |
| Stale cinematic ESC assertion | `tools/test_video_integration.py` | Asserted `ACT_INTRO`; the cinematic now goes to `MENU` |
| Stale scene counts | `main.py`, `src/core/game.py` | "9 scenes" → 15 (measured: 15 `GameState` members, 15 registered scenes, 0 orphans) |
| `.gitignore` | repo root | Ignore rules for the GOLIATH debug intermediates (`_mask/`, `_seed/`, `_strips/`, `_test/`, `gifs/`, `regen_report.json`, `spritesheet_goliath.png` ≈ 127 MB) and `_archive_*/` (424 MB, includes a duplicated `.exe`). Verified: no already-tracked file became ignored |

### 11.5 Findings that were **not** defects

- **`VALID_TRANSITIONS[TITLE]` has no `MENU` edge.** The spec defines
  `TITLE ──(key)──► CINEMATIC ──(10s o Esc)──► MENU`. MENU is reachable
  only through the cinematic *by design*, and `MENU → TITLE` lets the
  user come back. Not a bug.
- **The menu shows no live preview of the background.** The spec only
  asks for "submenu de 2 fondos". Optional enhancement.
- **`_base/` (the 1024px source strips, 23.1 MB) is not in git.** That
  is intentional and pre-existing: `.gitignore:85` points at
  `tools/redesign_bosses/01_generate_bases.py`, which exists. The 60
  committed frames are the product.

### 11.6 Still open

- The 8 pre-existing failures (§9) — order-dependent pollution plus one
  real Lissajous geometry assertion. None introduced by BLOQUE 73.
- `master` was **1 commit ahead of `origin/master`** at the start of
  this pass: `a8bf14f` (the Prompt-Weapon 8D spec) had never been
  pushed. It is a local-only commit until pushed.
- The next release needs a changelog entry for the `bg_mode` fix and
  the `GameState.MENU` test updates.