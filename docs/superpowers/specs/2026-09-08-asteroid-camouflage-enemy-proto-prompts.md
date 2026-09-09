# Proto-Prompts — Asteroid Camouflage Enemy + Asteroid Variants (BLOQUE 60.5+)

**Date:** 2026-09-08
**Author:** Lerius (idea) + Mavis (draft)
**Status:** DRAFT — ready to feed into mcode-tools / `tools/redesign_ships/01_generate_bases.py`

These are AI-ready proto-prompts (the seed text the user pasted into a prompt-expander like `prompt-weapon-definitivo`). They build on the existing BLOQUE 59 ship pipeline and the BLOQUE 58.12 procedural asteroid style.

---

## Context: what we already have

- **Asteroids are procedurally generated** in `src/entities/asteroid.py`. Brown palette `(140, 100, 60)` with Greek-key stripes (Star Fox 64 vibe). 8-bit rocky, irregular polygon outlines (12-16 points).
- **Enemy ships are AI-generated top-down views** (BLOQUE 59 v4, prompt forces "NOSE points DOWN, wings left/right, engines top, cockpit upper body").
- The camouflage enemy would be a NEW ship that lives in the BLOQUE 59 pipeline but is "shaped like a half-asteroid" so it blends with the background.

---

## Proto-Prompt 1 — Half-Asteroid Camouflage Enemy

A new enemy ship that pretends to be an asteroid. Two visual states:

### Default state (CLOSED — "asleep")
Looks like a regular asteroid, indistinguishable from a real one. Brown rocky body, Greek-key stripes, irregular outline.

### Combat state (OPEN — "deployed")
The asteroid splits horizontally down the middle. The two halves slide apart like jaws. Inside the seam: a ship cockpit, weapons, and a glowing engine exhaust. The body rocks slightly to "scan" the area.

### Shared AI prompt (pass to mcode-tools)

```
16-bit pixel art, top-down view (strictly perpendicular, no 3/4 angle)
viewed from directly above, isolated on pure black background, sharp
clean pixel edges, no anti-aliasing, no gradients, limited palette
(max 12 colors), Metal Slug aesthetic.

Character: "MINE-ASTEROID" — a hollowed-out asteroid half that conceals
a small ship inside.

Closed state ("asleep"):
  - Looks like a normal rocky asteroid: irregular polygon outline
    (12-16 craggy edges), brown rocky body with Greek-key stripe pattern
    (Star Fox 64 style angular bands across the middle).
  - Palette: base brown (140, 100, 60), highlight (180, 140, 90),
    shadow (90, 60, 30), deep crack (50, 30, 15).
  - 2-3 small crater pock marks scattered on the surface.
  - No visible ship parts. The asteroid is fully closed.

Open state ("deployed"):
  - Same outer asteroid outline but split along a horizontal seam at
    the equator of the body.
  - The two halves separate by ~30% of the asteroid's diameter (top
    half slides up, bottom half slides down), revealing the ship
    inside the seam.
  - Inside the seam: a small angular cockpit (dark blue or gunmetal),
    1 small cannon barrel pointing forward (toward the bottom of the
    image), 2 glowing orange thrusters (RGB 255, 140, 60) at the rear
    of the inner cavity.
  - The exposed ship parts are small relative to the asteroid body
    (the asteroid is the dominant shape, the ship is the secret).

Pose: top-down view (strictly perpendicular, no 3/4 angle) with the
seam horizontal and the ship nose pointing DOWN toward the bottom of
the image. Single object per frame.
```

### Per-frame animation notes (4 anims × 10 frames)

| State | Anim | Description |
|-------|------|-------------|
| closed | idle | 10 identical closed-asleep frames, runtime applies ±1px vertical bob |
| closed | thrust | 10 identical closed-asleep frames with subtle Greek-key stripe animation (one band shifts 1px per frame for "scanning" feel) |
| open | damage | Same as closed (the ship retracts on hit) — use the closed sprite |
| open | death | Asteroid halves fly apart in 10 frames (top half up, bottom half down, ship explodes in the middle, fragments scatter) |

**Key contract:** In `closed` states, the sprite must be visually indistinguishable from a regular asteroid at the playfield scale. In `death`, the two halves separate and the inner ship is revealed as it explodes.

---

## Proto-Prompt 2 — 16-bit Pixel Art Asteroid Variants

We currently have ONE procedural asteroid generator. We want a sprite sheet of 6-8 distinct asteroid variants for visual variety. Same palette and Greek-key stripe language as the procedural, but more detailed (16-bit, not 8-bit), with intentional asymmetry.

### Shared AI prompt

```
16-bit pixel art, top-down view (strictly perpendicular, no 3/4 angle)
isolated on pure black background, sharp clean pixel edges, no
anti-aliasing, no gradients, limited palette (max 16 colors), Metal
Slug / Star Fox 64 aesthetic.

Subject: a single rocky asteroid floating in deep space.

Style:
  - Irregular polygon outline (14-18 craggy edges, asymmetric — not a
    perfect circle, not a regular shape).
  - Greek-key stripe pattern across the body: 2-3 horizontal bands
    with the iconic Star Fox 64 angular pattern (right-angle hooks
    at the band ends).
  - 2-4 small craters (darker brown circles) scattered on the body.
  - 1-2 surface cracks (thin dark lines following the contour).
  - 1-3 small mineral highlights (lighter speckles, 1-2 px each).

Palette (MUST use these exact RGB values, no new colors):
  - Base brown:    (140, 100, 60)
  - Highlight:     (180, 140, 90)
  - Mid-shadow:    ( 90,  60, 30)
  - Deep shadow:   ( 50,  30, 15)
  - Black crack:   ( 20,  10,  5)
  - Mineral hi:    (210, 170, 110)

Composition: the asteroid fills 80% of the image, centered, with
margin on all sides for rotation/scale in-game.
```

### Variants (6 designs, 32×32 each)

1. **Round chunky** — squat potato shape, low eccentricity, lots of craters.
2. **Elongated** — horizontal stretched, like a loaf, single big Greek-key band.
3. **Spiked** — 3-4 sharp protrusions (mineral crystals or jagged peaks) sticking out.
4. **Hollowed** — one big crater on one side (hint: this is the "open" asteroid from proto-prompt 1 without the ship).
5. **Cracked** — one big surface crack running diagonally, looks like it could break apart.
6. **Mineral-rich** — extra bright speckles (mineral deposits), more vibrant highlight.

### Per-frame animation notes

Asteroids in the game are static sprites (no per-frame animation), so each variant is **one 32×32 PNG**. Use `_source.png` only (no idle/thrust/damage/death variants needed).

---

## Pipeline integration (BLOQUE 60.5+)

If the user wants to implement these:

1. Add `EnemyKind.MINE_ASTEROID` (= `"mine_asteroid"`) to the `EnemyKind` enum in `src/entities/enemies/enemy.py`.
2. Add the entry to `_ship_specs.py` with the new `prompt_fill` and 5 animation states (closed/idle, closed/thrust, closed/damage, death, intro).
3. Use the existing BLOQUE 59 pipeline: AI gen → postprocess → 4 anims × 10 frames → integrate.
4. Behavior: idle/thrust look identical (closed asteroid). Damage triggers a brief flash + transition to closed/damage. The `mine_asteroid` looks like a regular asteroid 90% of the time and "deploys" briefly when it attacks.
5. For the asteroid variants: simpler — just regenerate 6 PNGs at 32×32, save to `Assets/sprites/asteroids/<variant>.png`, load via `_load_sprite` in `src/entities/asteroid.py` (replacing the procedural generator with a variant-pick).
