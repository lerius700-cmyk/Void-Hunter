# GOLIATH Handoff — para Mavis M3.1 (cloud session, no local)

> **Stop. Read this BEFORE you touch anything.**
>
> This file is a recovery map. The local session found several bugs the
> GOLIATH work hid behind each other. A cloud session that doesn't know
> the history will re-introduce them at random. Read all the way through
> before editing.

## 1. Where you are when you start

- **Repo**: `https://github.com/lerius700-cmyk/Void-Hunter`
- **Branch**: `master` at `1808e07` (v1.6.2, BLOQUE 73.5)
- **Tag**: `v1.6.2` at `1808e07` (lightweight tag, points to source commit)
- **Pre-built .exe**: `void-hunter-v1.6.2.exe` in the v1.6.2 GitHub Release
- **Tests**: 226 / 1 skipped on `boss or goliath or shield or javelin`

`git log --oneline --since="2026-10-20"` gives you the last 11 commits.
The interesting ones for the GOLIATH work, in order:

```
0985ccc fix: BLOQUE 73.1 TileManager degrades gracefully when tiles/act1 is missing
65a1a7e feat: BLOQUE 73.2 GOLIATH shield is finally drawn (oval on the arm)
c556d93 docs: release notes for v1.5.1
60a9836 fix: BLOQUE 73.3 restore GOLIATH's 60 animation frames
e948c40 docs: release notes for v1.6.0
6c71e1b fix: BLOQUE 73.4 port the remaining BLOQUE 66 work (eye laser, hitbox, padding)
611314a docs: release notes for v1.6.1
c6679b4 fix: BLOQUE 73.5 GOLIATH's animation was never ticked, and --boss never reached a boss
1808e07 docs: release notes for v1.6.2
```

## 2. What BLOQUE 73.x actually contains

This is the work the local session did. Each BLOQUE fixed a specific
regression or finished a piece of pre-existing work that had never
landed. Do not undo any of this without explicit user approval.

### BLOQUE 73.1 — TileManager crash fix (commit `0985ccc`)

- **What**: `Assets/background/tiles/act1/` does NOT exist in the repo.
  Those 6 AI-generated tile PNGs were never committed. `TileManager`
  used to raise `FileNotFoundError` from its constructor, which
  `ParallaxBackground` calls eagerly in `Game.register_scenes()`. The
  shipped `v1.4.0.exe` could not launch.
- **What changed**: `TileManager` accepts missing/partial/unreadable
  dirs as `available=False` and draws nothing. Procedural galaxy
  strip is the visible backdrop. 9 of the 14 test_tile_manager.py
  tests run without tiles; 5 carry a `skipif` that re-enables if the
  PNGs are ever committed.
- **What the user said about it**: The crash had been there since
  v1.4.0 shipped. They were told the game "crashed on launch" and
  wanted both v1.4.0 and v1.5.0 fixed.

### BLOQUE 73.2 — Shield visual + draw (commit `65a1a7e`)

- **What**: The shield MECHANICS shipped in BLOQUE 53a (`_handle_shield_collisions`,
  `_draw_shield_laser`, `_start_shield_laser`, the state machine).
  The visual NEVER did. So the player had an invisible hitbox that
  consumed bullets.
- **What changed**: `_draw_goliath_shield(target, ox, oy)` draws a
  translucent oval on the boss's left arm. Charge ramp
  iron → blue → cyan with a pulsing outer glow. Brings the
  `_handle_shield_collisions`, `_draw_shield_laser`, and
  `_draw_goliath_shield` to all read `_goliath_shield_center` —
  one anchor, three consumers.
- **Helpers in `src/ui/scenes.py`**:
  - `get_sprite_arm_anchor(name)` — finds the brass plate by colour
    signature, with a torso clamp (col 42-54) so it doesn't latch
    onto helmet crests or javelin tips.
  - `get_sprite_centroid_offset(name)` — re-aligns the sprite so the
    body's visual centroid, not the canvas, lands on the world
    anchor. Without this, leaning frames (javelin/frame_03 was
    dx=+20) crowded the right viewport edge.
- **Constants in `src/ui/gameplay_runtime.py`** (user-approved at
  0837a86):
  - `GOLIATH_SHIELD_DX = -11`
  - `GOLIATH_SHIELD_DY = 6`
  - `GOLIATH_SHIELD_R = 11`
  - `GOLIATH_SHIELD_RX = 11`
  - `GOLIATH_SHIELD_RY = 17`
  - `GOLIATH_SHIELD_MAX_HITS = 20`

### BLOQUE 73.3 — 60 animation frames restored (commit `60a9836`)

- **What was the actual root cause** of the "javelin/frame_03 está
  cortado" complaint. Not an anchor bug, not a viewport clip, not a
  compositor. Commit `562eb58` ("BLOQUE 64.B stage 1 - 6 GOLIATH
  anims x 10 frames borderless") had shipped 10 byte-identical
  copies per animation. That commit is an ancestor of `master` and
  landed AFTER `ac53596` (BLOQUE 65 regen) which had produced 10
  genuinely distinct frames per animation. So the regen was silently
  reverted. GOLIATH became a still image wearing the filename
  `frame_00`...`frame_09`.
- **What changed**: `git checkout ac53596 -- Assets/sprites/bosses/goliath/`
  restored the 60 distinct frames. No code changes.
- **How to verify**: every animation directory should have
  10/10 unique MD5s:
  ```bash
  foreach ($a in phase1_idle,phase2_idle,javelin,laser,purple_bullet,death) {
    $h = Get-ChildItem "Assets/sprites/bosses/goliath/$a/frame_*.png" |
         ForEach-Object { (Get-FileHash $_.FullName -Algorithm MD5).Hash }
    Write-Host "$a $(@($h | Sort-Object -Unique).Count)/10"
  }
  ```
  Expected: `10/10` for all six.

### BLOQUE 73.4 — BLOQUE 66 remainder (commit `6c71e1b`)

Three pieces of pre-existing work that 73.3 had not yet ported:

1. **`get_sprite_eye_anchor(name)`** (BLOQUE 66.4l). Per-frame eye
   position by colour signature (saturated red inside the head band).
   `attack == 9` (the GOLIATH eye laser) now spawns at the eye, not at
   `boss.y + 30`. The previous fixed offset put the beam 2-6 px below
   the eye, which read as "the laser comes from the chest".

2. **4 re-padded frames** from BLOQUE 66 (commits b9dca9b and
   8092d6b):
   - `phase1_idle/frame_02` (was T=1)
   - `phase1_idle/frame_03` (was T=1)
   - `javelin/frame_00` (was T=1)
   - `purple_bullet/frame_02` (was T=5)
   3 more padded in this BLOQUE: `laser/01`, `phase2_idle/04`,
   `phase2_idle/08` (all T=1). All now T>=3.

3. **Shield hitbox rebuilt from oval half-extents**. The hitbox
   used `GOLIATH_SHIELD_R` (11) for both axes, leaving 6 px of the
   visible oval's tall axis non-colliding. Now uses
   `max(R, RX)+1` × `max(R, RY)+1`. The `+1` is because `pygame.Rect`
   is half-open and would otherwise exclude the rim pixels at exactly
   ±RX.

### BLOQUE 73.5 — Animation was never ticked, --boss was a stub (commit `c6679b4`)

The two bugs that were masking each other. After 73.3/73.4 the user
asked "como abro el juego con el goliath animado y todo?". A 6-second
playtest showed the boss holding frame 0. Then:

1. **`Boss.update_animation()` had no caller anywhere**. The method
   was added in BLOQUE 64.B but a grep across `src/` and `main.py`
   found the definition and nothing else. `Boss.update(dt)` moves the
   entity and never touched `animation_frame`, so it stayed pinned
   at 0. The 60 distinct frames in 73.3 were still showing one pose.
   - **Wire**: in `src/ui/gameplay_runtime.py`, after the call to
     `self._boss.update(dt)`, add
     `self._boss.update_animation(dt)`.
   - **Verify**: `phase1_idle` should cycle 10 frames in 1 second.
     `death` should hold at frame 9 instead of wrapping to 0.

2. **`--boss` was a stub**. `main.py` printed
   `"full integration in next BLOQUE; running main game"` and ran
   the title screen. Worse, the dev-loop flag every doc recommends
   is `--boss-test`, which **never existed on master** either — the
   real flag is `--boss`. So the documented dev loop was a no-op
   twice over.
   - **Fix**: `_cmd_play(duration, boss=None, act=None)` walks
     `TITLE → ACT_INTRO → GAMEPLAY → BOSS_INTRO → BOSS_FIGHT`,
     mapping the boss name to its act first
     (GOLIATH act 1, HYDRA act 2, PHANTOM and NEMESIS act 3).
   - **Verify**: `python main.py --boss goliath --easy` prints
     `jumped to GOLIATH (act 1)`.

## 3. What M3.1 should NOT do

These are things that LOOK like obvious improvements but the user
explicitly told the local session NOT to do. Confirm with the user
before undoing any of them.

- **Don't change the oval constants** (`DX=-11, DY=6, RX=11, RY=17`).
  The user approved those in BLOQUE 66.4o. They are the user-approved
  state. Reverting to BLOQUE 66.5 values (DX=-2, DY=0, RX=7, RY=10)
  is exactly what the local session was warned not to do. The
  precedent is that this is the value they like.
- **Don't introduce a backplate (translucent silhouette beneath the
  sprite to fill AI gaps)**. The local session tried this in BLOQUE
  66.4e/66.4g. The user said "corrige eso para que solo haya uno"
  because the backplate overlay produced a visually doubled boss. The
  backplate is gone; do not bring it back.
- **Don't regenerate GOLIATH frames with AI** for "polish". BLOQUE
  66's regen attempts repeatedly produced debris (frame_05 + laser
  arm issue) and the backplate workaround. The 60 ac53596 frames
  are what the user spent "tantísimo esfuerzo" on. The right path to
  AI regen is the next session, not a quiet substitution.
- **Don't bump the major version again without the user**. v1.6.2 is
  the user's next release. The remote has `v1.0.0` through `v1.5.1`
  and now `v1.6.0`, `v1.6.1`, `v1.6.2`.

## 4. Things that ARE broken and the user expects to be fixed

`docs/KNOWN_ISSUES.md` lists them. The user said "v1.5.1 (or v1.6.x)
fixes ISSUE-001", so:

- **ISSUE-001 (source⇄binary gap)**: RESOLVED in v1.5.1+ by the
  reset-to-origin/master + cherry-pick strategy. The current
  master is the source for v1.6.2, so this issue is closed.
- **ISSUE-002 (8 pre-existing test files fail on `D:\AI\void-hunter\...`)**:
  OPEN. ~19 test failures. Not in scope for the polish session.
  The user is aware. If the cloud session wants to tackle it, the
  fix is to replace `D:\\AI\\void-hunter\\` with
  `F:\\AI\\MM\\void-hunter\\` (or, better, make the paths relative
  to the repo root via `Path(__file__).resolve().parent.parent`).
- **ISSUE-003 (CLAUDE.md stale)**: OPEN. CLAUDE.md says
  "v1.2.5 (BLOQUE 58.60)". Should say "v1.6.2 (BLOQUE 73.5)".
  Trivial to fix; the user knows.
- **ISSUE-004 (smoke test fails in CI without display)**: OPEN. The
  user is aware. Most local runs are fine with the dummy SDL driver
  but CI may need a `conftest.py` that auto-inits pygame.

## 5. Action plan for M3.1

If you are M3.1 and have just cloned the repo, here is the order to
work in.

### Step 0 — Don't break what works

1. Run `git log --oneline -5` to confirm you are on
   `1808e07` (or later — if the user is on a different hash, ask
   before changing anything).
2. Run the smoke test described in §6. If it prints
   `jumped to GOLIATH (act 1)` you are on a good commit.
3. Do NOT touch `Assets/sprites/bosses/goliath/` PNGs. They are the
   product of multiple BLOQUEs of work and look correct (10 unique
   MD5s per animation).
4. Do NOT change the GOLIATH_SHIELD_* constants in
   `src/ui/gameplay_runtime.py`.

### Step 1 — If asked to do "GOLIATH more polish", start here

The remaining visual gaps you can address without breaking the
tested invariants:

- **The eye laser's column is the GOLIATH-SHIELD-centre-shifted beam**.
  Right now it's a vertical line. It could sweep horizontally as the
  boss moves. Tests in `tests/test_goliath_anchor_coincidence.py`
  probe it at a fixed column, so any change to angle is a refactor of
  the test.
- **Shield flash on hit**. There is `self._boss_shield_hits` and a
  counter. A 4-frame flash tint on the boss sprite when a bullet
  hits the shield is a small visual add. The hitbox test covers the
  geometric hit; a flash test would be a separate assert.
- **phase2_idle cracked-armour overlay**. The user mentioned "phase 2
  has cracks on the armour" but no overlay exists. The frames are
  already painted; a runtime overlay would be additive.

### Step 2 — If asked to clean up the test suite

`pytest tests/` reports 19 failures from `test_paths_legacy.py`,
`test_tile_manager.py`, `test_asteroid_sprites.py`,
`test_bloque_*.py`, `test_parallax_tile_mode.py`,
`test_paths.py::test_paths_no_star_shapes`,
`test_gameplay_runtime.py::test_boss_phase_change_spawns_burst`
(now passes — the boss phase change was repaired in BLOQUE 73.5 by
the new `--boss` flow).

The fix path is universal: convert hardcoded `D:\\AI\\void-hunter\\`
to `Path(__file__).resolve().parent.parent` or similar. This is
tedious but mechanical.

### Step 3 — If asked to update documentation

- `CLAUDE.md` says `v1.2.5 (BLOQUE 58.60)`. Should be
  `v1.6.2 (BLOQUE 73.5)`. The local session intentionally left it
  alone because `CLAUDE.md` is the persistent identity doc and the
  user wants to update it deliberately, not as a side-effect of a
  polish commit.
- `docs/KNOWN_ISSUES.md` has ISSUE-001 marked resolved (it is) and
  ISSUE-002/003/004 still open. If the cloud session closes 002 or
  003, edit the doc in the same commit.

## 6. Smoke test for "is the local session's state healthy"

```bash
$env:SDL_AUDIODRIVER = "dummy"
$env:SDL_AUDIODRIVER = "dummy"
python main.py --boss goliath --easy --duration 3
```

Expected output (last 2 lines):
```
VOID HUNTER: jumped to GOLIATH (act 1)
```

If you don't see that, the state is broken.

```bash
$env:SDL_AUDIODRIVER = "dummy"
$env:SDL_AUDIODRIVER = "dummy"
python -m pytest tests/ -k "boss or goliath or shield or javelin" --ignore=tests/test_paths_legacy.py -q
```

Expected: `226 passed, 1 skipped`.

## 7. Files M3.1 should know about

- **`src/ui/gameplay_runtime.py`**: GOLIATH drawing, hitbox, eye laser.
  Search for `GOLIATH_SHIELD`, `_draw_goliath`, `_draw_goliath_shield`,
  `_handle_shield_collisions`, `_goliath_shield_center`. BLOQUE 73
  work landed here.
- **`src/ui/scenes.py`**: `get_sprite_arm_anchor`,
  `get_sprite_centroid_offset`, `get_sprite_eye_anchor`. New in
  BLOQUE 73.
- **`src/entities/enemies/boss.py`**: `Boss.update_animation` is
  BLOQUE 64.B; the BLOQUE 73.5 fix is the caller in
  `gameplay_runtime.py`, not in this file.
- **`src/systems/tile_manager.py`**: BLOQUE 73.1 (graceful
  degradation).
- **`main.py`**: BLOQUE 73.5 (`_cmd_play` walks scenes for `--boss`).
- **`tests/test_goliath_anchor_coincidence.py`**: 8 tests added
  in 73.4. They prove the shield/eye anchors stay consistent
  across the runtime, hitbox, and visual.
- **`tests/test_goliath_animation_advances.py`**: 6 tests added
  in 73.5. They prove the animation actually advances and
  `--boss` reaches BOSS_FIGHT.
- **`tests/test_tile_manager.py`**: BLOQUE 73.1 (graceful
  degradation).
- **`Assets/sprites/bosses/goliath/<anim>/frame_NN.png`**: 60
  distinct frames, restored in 73.3 from ac53596.
- **`tools/release_notes_v1.6.2.md`**: the user-facing summary of
  what shipped.
- **`docs/KNOWN_ISSUES.md`**: the live issue list.
- **`docs/OPERATIONS.md`**: gh CLI / PAT setup — needed if the cloud
  session publishes a new release.

## 8. What the user told the local session (verbatim, paraphrased)

- "el ovalo esta dentro de la silueta del escudo, y se ve bastante bien"
  — oval at 0837a86 is approved, don't change it.
- "lo unico es que goliath se sigue viendo cortado en algunas
  animaciones (como cuando va a lanzar su jabalina)" — the javelin
  cortado is the visual gap to fix. 73.3 turned out to be the root
  cause.
- "no agresivo regen" / "no vayas a cambiar el ovalo" — preserve
  the approved work; don't break things with new AI generations.
- "no pelea más con eso. ... es tu perfil, tu decisión." — give
  Mavis autonomy on the ship strategy.
- "como abro el juego con el goliath animado y todo? el de esta
  version" — what the user actually wants: to be able to play
  v1.6.2 and see the boss move. v1.6.2 does this. The README's
  Development section is the canonical answer; don't let that doc
  drift.

## 9. If something is wrong

If `main.py --boss goliath` doesn't print
`jumped to GOLIATH (act 1)`, the most likely cause is that
`_goliath_shield_center` is not being called from
`_draw_goliath` (the helper that the hitbox/laser/visual all share).
The chain that needs to hold:

1. `main.py` → `_cmd_play` walks TITLE → ACT_INTRO → GAMEPLAY →
   BOSS_INTRO → BOSS_FIGHT (BLOQUE 73.5).
2. `BossFightScene.on_enter` builds the `GameplayRuntime` with
   `is_boss=True`.
3. `GameplayRuntime._update_boss(dt)` calls `self._boss.update(dt)`
   then `self._boss.update_animation(dt)` (BLOQUE 73.5).
4. `Boss.update_animation(dt)` advances `animation_frame` and
   `animation_timer` (already there, just not called before).
5. `Boss.animation_path` → `bosses/goliath/<state>/frame_NN.png`.
6. `_goliath_shield_center(runtime)` reads
   `get_sprite_arm_anchor(animation_path) + get_sprite_centroid_offset(animation_path)`
   and adds the GOLIATH_SHIELD_* constants.
7. `_draw_goliath_shield` and `_handle_shield_collisions` read
   the same `_goliath_shield_center` result.

If any of those breaks, GOLIATH visually breaks. The tests in
`tests/test_goliath_anchor_coincidence.py` and
`tests/test_goliath_animation_advances.py` are the regression net.

## 10. TL;DR for M3.1

| Action | Why |
|--------|-----|
| `git log --oneline -5` | confirm you are at v1.6.2 |
| Run the smoke test in §6 | confirm the local session's state is healthy |
| Read `docs/KNOWN_ISSUES.md` | see what's still broken |
| Read `tools/release_notes_v1.6.2.md` | see what just shipped |
| Read this file's §3 | see what NOT to change |
| If asked for "more GOLIATH polish" | start with §5 Step 1 |
| If asked to fix pre-existing tests | see §5 Step 2 |
| If asked to update docs | see §5 Step 3 |
| If nothing works | see §9 and run the regression tests in §7 |

The user has been waiting hours to see the boss animate. The
animation does animate. The .exe ships. The release is live.
Whatever you do, don't break that.