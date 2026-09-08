"""BLOQUE 60 Task 9/10 layering fix.

Wraps the procedural fallback body of `_draw_goliath` in `else:` so that
the procedural layers do NOT overdraw the BLOQUE 60 sprite. The Phase 2
eye trail at the end of the function remains outside the if/else so it
renders on both paths.

Run from repo root: python tools/_bloque60_layering_fix.py
"""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TARGET = REPO / "src" / "ui" / "gameplay_runtime.py"


def main() -> None:
    text = TARGET.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)

    # Find the start of _draw_goliath method.
    start_idx = None
    for i, line in enumerate(lines):
        if line.startswith("    def _draw_goliath("):
            start_idx = i
            break
    assert start_idx is not None, "Could not find _draw_goliath"

    # Find the end of _draw_goliath (next method at 4-space indent).
    end_idx = None
    for i in range(start_idx + 1, len(lines)):
        if lines[i].startswith("    def "):
            end_idx = i
            break
    assert end_idx is not None, "Could not find end of _draw_goliath"

    # Sanity: find the function-body anchor lines.
    boss_none_idx = None
    sprite_if_idx = None
    sprite_blit_idx = None
    trailing_comment_end_idx = None  # one past the last Task 10 fix line
    procedural_start_idx = None  # "# --- Procedural fallback ..."
    eye_trail_start_idx = None  # "# ----...\n# Layer 13: BLOQUE 60..."
    hp_bar_end_idx = None  # last line of HP bar (pygame.draw.rect with hp_color)

    for i in range(start_idx, end_idx):
        stripped = lines[i].rstrip("\n")
        if (
            boss_none_idx is None
            and stripped == "        if self._boss is None:"
        ):
            boss_none_idx = i
        if (
            sprite_if_idx is None
            and stripped == "        if sprite is not None:"
        ):
            sprite_if_idx = i
        if (
            sprite_blit_idx is None
            and sprite_if_idx is not None
            and stripped == "            target.blit(sprite, (blit_x, blit_y))"
        ):
            sprite_blit_idx = i
        if (
            procedural_start_idx is None
            and "# --- Procedural fallback" in stripped
        ):
            procedural_start_idx = i
        if (
            eye_trail_start_idx is None
            and "Layer 13: BLOQUE 60" in stripped
        ):
            eye_trail_start_idx = i

    # The trailing "BLOQUE 60 Task 10 fix" comment is a 5-line block starting
    # right after the sprite blit. It ends at the line just before
    # `# --- Procedural fallback`.
    assert (
        boss_none_idx is not None
        and sprite_if_idx is not None
        and sprite_blit_idx is not None
        and procedural_start_idx is not None
        and eye_trail_start_idx is not None
    ), (
        f"idx: boss_none={boss_none_idx} sprite_if={sprite_if_idx} "
        f"sprite_blit={sprite_blit_idx} proc={procedural_start_idx} "
        f"eye={eye_trail_start_idx}"
    )

    # The "bob = math.sin(...)" duplicate inside the procedural body sits
    # right after `# Visual is centered on the hitbox; offset y for the
    # "breathing" bob.`. The second occurrence of that comment line
    # is INSIDE the procedural body.
    # Same for "cx = int(self._boss.x + ox)" and "cy = int(self._boss.y + oy)".
    # These three lines need to be removed from the procedural body when
    # we wrap it in `else:`.

    # We'll build the new function body explicitly. The structure:
    # - boss_none / return            (unchanged)
    # - BLOQUE 60 sprite-load comment + import + sprite = _load_sprite(...)
    # - bob = math.sin(...)           (NEW: moved before if/else)
    # - cx = int(self._boss.x + ox)   (NEW: moved before if/else)
    # - cy = int(self._boss.y + oy)   (NEW: moved before if/else)
    # - if sprite is not None:        (sprite branch, no longer computes
    #                                  bob/cx/cy inside)
    # - else:
    # - cfg, flash_t, flashing, vw, vh, vx, vy  (procedural body, dedented
    #                                              duplicate bob/cx/cy)
    # - ...all procedural layers...   (indented +4)
    # - eye trail block               (UNCHANGED indent: 8 spaces; sits at
    #                                  function level, outside the else)

    # Build the new function body from scratch.
    # Strategy: take the lines from boss_none_idx to end_idx, transform them.

    # We'll define the new head (from after the docstring to just past the
    # `else:` line), then append the indented procedural body, then append
    # the eye trail (already at 8 spaces).

    # --- Build the new head (lines 5524-5544 in current file) ---
    new_head = []
    # 1) `if self._boss is None: return`
    new_head.append(lines[boss_none_idx])         # "        if self._boss is None:"
    new_head.append(lines[boss_none_idx + 1])     # "            return"
    # 2) BLOQUE 60 comment + import + sprite = _load_sprite(...)
    new_head.append(lines[sprite_if_idx - 6])  # "        # BLOQUE 60: try to load ..."
    new_head.append(lines[sprite_if_idx - 5])
    new_head.append(lines[sprite_if_idx - 4])
    new_head.append(lines[sprite_if_idx - 3])
    new_head.append(lines[sprite_if_idx - 2])  # "        from src.ui.scenes import _load_sprite"
    new_head.append(lines[sprite_if_idx - 1])  # "        sprite = _load_sprite(...)"
    # 3) NEW: bob, cx, cy BEFORE the if/else
    new_head.append("        # Shared anchor values: used by both the sprite\n")
    new_head.append("        # branch and the procedural fallback. Moved here\n")
    new_head.append("        # (BLOQUE 60 layering fix) so the procedural body\n")
    new_head.append("        # does NOT overdraw the sprite when one is loaded.\n")
    new_head.append("        bob = math.sin(self._t * 1.0) * 1.5\n")
    new_head.append("        cx = int(self._boss.x + ox)\n")
    new_head.append("        cy = int(self._boss.y + oy)\n")
    # 4) sprite branch (kept but no longer computes bob/cx/cy)
    new_head.append("        if sprite is not None:\n")
    new_head.append("            vw, vh = 96, 80\n")
    new_head.append("            blit_x = cx - vw // 2\n")
    new_head.append("            blit_y = cy - vh // 2 + int(bob)\n")
    new_head.append("            target.blit(sprite, (blit_x, blit_y))\n")
    # 5) else: wraps the procedural body
    new_head.append("        else:\n")
    # 6) opening of procedural body (cfg, flash, vw/vh/vx/vy)
    #    We re-emit the existing lines from `# --- Procedural fallback ...`
    #    to `vy = cy - vh // 2 + int(bob)`, dedented by 0 (they were 8 spaces,
    #    will become 12 spaces after the `else:` indent shift below).
    #    BUT we must SKIP the duplicate `bob = math.sin(...)`, `cx = ...`, `cy = ...`
    #    that are no longer needed here.
    #    Easiest: emit the procedural body with +4 indent, dropping the
    #    three duplicate lines.

    # Collect procedural body lines (from "# --- Procedural fallback" up
    # to but not including the eye trail comment).
    proc_lines = lines[procedural_start_idx:eye_trail_start_idx]
    # Identify and drop the three duplicate lines.
    bob_line_marker = '        bob = math.sin(self._t * 1.0) * 1.5'
    cx_line_marker = '        cx = int(self._boss.x + ox)'
    cy_line_marker = '        cy = int(self._boss.y + oy)'
    kept_proc = []
    for ln in proc_lines:
        if (
            ln.rstrip("\n") == bob_line_marker
            or ln.rstrip("\n") == cx_line_marker
            or ln.rstrip("\n") == cy_line_marker
        ):
            continue
        # Indent +4 spaces.
        assert ln.startswith("        "), (
            f"Unexpected indent in procedural body line: {ln!r}"
        )
        kept_proc.append("    " + ln)

    # Build the new procedural body block.
    new_proc = []
    new_proc.extend(new_head)
    new_proc.extend(kept_proc)

    # --- Build the eye trail block (unchanged) ---
    # The eye trail starts at eye_trail_start_idx and runs to the end of
    # the function body (end_idx).
    eye_trail = lines[eye_trail_start_idx:end_idx]

    # --- Assemble new function body ---
    new_body = new_proc + eye_trail

    # Replace the original body region with the new one.
    new_lines = lines[:boss_none_idx] + new_body + lines[end_idx:]

    TARGET.write_text("".join(new_lines), encoding="utf-8")
    print(f"OK: rewrote {TARGET}")
    print(f"  before: {end_idx - boss_none_idx} lines (function body)")
    print(f"  after:  {len(new_body)} lines (function body)")


if __name__ == "__main__":
    main()
