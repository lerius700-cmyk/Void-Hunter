# VOID HUNTER v1.6.3 — main menu + background switcher

> Replaces the direct post-cinematic → ACT_INTRO flow with a menu that
> gives the user three options. New Game, Boss Time, or a Background
> submenu that toggles between Space Void and Asteroid Nebula.

---

## ✨ The new menu

After the cinematic plays (or you press Esc to skip it), you land in
the new **Main Menu**:

```
VOID HUNTER

> NEW GAME
  BOSS TIME
  BACKGROUND

ARROWS: NAVIGATE   ENTER: SELECT   ESC: BACK
```

- **NEW GAME** → ACT_INTRO → GAMEPLAY (the regular flow)
- **BOSS TIME** → BOSS_INTRO → BOSS_FIGHT (skip directly to GOLIATH)
- **BACKGROUND** → opens a 2-item submenu:
  - **SPACE VOID** — sparse starfield, no procedural strip
  - **ASTEROID NEBULA** — the rich purple procedural strip

After you pick a background, the submenu closes and the choice takes
effect on the next scene that needs a background.

Esc from the top level returns to TITLE. Esc from the submenu returns
to the top level without applying.

## 🐛 Fix: the procedural strip was never drawn

In v1.6.0 / v1.6.2, `GameplayRuntime.update` called
`self._galaxy_bg.update(effective_dt)` — so the strip was animating —
but `GameplayRuntime.render` never called `self._galaxy_bg.draw(target)`.
The result: the strip's pixels were computed every frame and then
discarded, so the user saw the sparse starfield even with the strip
loaded. This is why v1.4.0 looked procedural and v1.6.2 looked empty.

BLOQUE 73.7 fixes the draw path:
- `bg_mode == 0` (Space Void): only `_parallax_bg.draw()`
- `bg_mode == 1` (Asteroid Nebula): `_galaxy_bg.draw()` first, then
  `_parallax_bg.draw()` for the sparkles on top
- Boss fights: unchanged (they use their own `_tiling_bg` / `_bg`)

The default `bg_mode` is 1 (Asteroid Nebula) to match the v1.4.0 look
the user approved.

## 🛠️ Implementation notes

- New scene: `MainMenuScene` (registered as `GameState.MENU`)
- New `Game.bg_mode: int` (0 or 1; default 1) for the user's choice
- `CinematicScene.update` chains into MENU (was: ACT_INTRO)
- `MainMenuScene._activate` picks the menu item, including
  `Game.bg_mode = self._bg_cursor` for BACKGROUND selections
- `GameplayRuntime.render` reads `Game.bg_mode` and routes to the
  correct draw path
- 3 valid transitions out of MENU: `ACT_INTRO`, `BOSS_INTRO`, `TITLE`

## ✅ Verification

| Check | Resultado |
|---|---|
| `void-hunter-v1.6.3.exe --check` | `VOID HUNTER check OK` — 9 scenes, 18 waves, 4 bosses |
| Tests boss/goliath/shield/javelin | 252 passed, 6 skipped (was 242 + 10 new menu tests) |
| MainMenuScene transitions | all 3 options route to the correct state |
| Background submenu | applies `bg_mode` and closes; Esc backs out without applying |
| 1-2 / 1-2-3 number keys | K_1/K_2 in submenu vs K_1/K_2/K_3 on top — distinct paths, no overlap |

Visual evidence:
- `tools/playtest_out/menu_top_newgame.png` — top level, NEW GAME
- `tools/playtest_out/menu_top_bosstime.png` — top level, BOSS TIME
- `tools/playtest_out/menu_bg_submenu.png` — BACKGROUND submenu open
- `tools/playtest_out/menu_bg_space_void.png` — submenu, SPACE VOID
- `tools/playtest_out/menu_bg_asteroid_nebula.png` — submenu, ASTEROID NEBULA

## ⬇️ Como jugar

1. Descargá `VoidHunter-v1.6.3-win64.zip` (~423 MB).
2. Extraé en cualquier carpeta.
3. Doble-click en `void-hunter-v1.6.3.exe`.
4. Pasá la title screen y la cinematica para llegar al menu.

El menu también está disponible vía flag:
```
void-hunter-v1.6.3.exe --boss goliath
```
salta directo a la pelea (no pasa por el menu).

## 💻 Requisitos

Windows 10/11 64-bit · ~430 MB disco · ~200 MB RAM