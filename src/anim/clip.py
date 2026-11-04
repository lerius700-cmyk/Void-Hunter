"""BLOQUE 74: the clip player.

Turns elapsed time into a frame index and composes the parts of a clip
into a target surface.

The timing is driven by the manifest's fps, so the animation no longer
depends on a constant hardcoded in the boss class.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import pygame

from src.anim.anchors import AnchorSet, load_anchors
from src.anim.manifest import AnimSet, Clip, Part, loaded_set
from src.anim.parts import draw_part


@dataclass(frozen=True)
class ClipState:
    """A clip resolved against the anchor table."""

    clip: Clip
    frame: int


class ClipPlayer:
    """Composes the parts of one animated set."""

    def __init__(self, anim_set: AnimSet, anchors: AnchorSet) -> None:
        self.set = anim_set
        self.anchors = anchors
        # The frames are loaded once and kept: a clip is played at 10-30 fps
        # and the PNG is decoded from disk every time otherwise.
        self._surface_cache: dict[Path, pygame.Surface] = {}
        # The SCALED frames are kept too, for the same reason: the enemy
        # sets are drawn at 1.05x and `pygame.transform.scale` on every
        # single frame would cost more than the blit it feeds.
        self._scaled_cache: dict[tuple[str, int, float, float], pygame.Surface] = {}

    def state(self, clip_id: str, elapsed: float) -> ClipState:
        """The frame index for `elapsed` seconds into `clip_id`.

        The index is `elapsed * fps`, with a 1e-6 epsilon: 0.3 * 10 is
        2.9999999999999996 in binary floating point, so an exact frame
        boundary would land on the PREVIOUS frame and the animation
        would advance 100 ms early whenever the runtime feeds rounded
        seconds in. The epsilon is a microsecond -- it rescues an exact
        boundary and does not move a frame that is genuinely mid-interval.
        """
        clip = self.set.clip(clip_id)
        if clip.frames <= 0:
            return ClipState(clip=clip, frame=0)
        fps = clip.fps if clip.fps > 0 else 10.0
        index = int(elapsed * fps + 1e-6)
        if clip.loop:
            index %= clip.frames
        else:
            index = min(index, clip.frames - 1)
        return ClipState(clip=clip, frame=index)

    def frame_at(self, clip_id: str, elapsed: float) -> int:
        """The frame index for `elapsed` seconds into `clip_id`."""
        return self.state(clip_id, elapsed).frame

    def surface(self, clip_id: str, frame: int) -> pygame.Surface | None:
        """The PNG of one frame, or None when it is missing.

        The CLIP DIRECTORY is what names the PNG, not the clip id: the two
        are allowed to differ, and the anchor table is keyed by the clip
        ID. The frame lives inside the set's own directory, next to the
        manifest and the anchor table that describe it -- the art and its
        measurement can never come from different trees.

        The loader is deliberately LOCAL: `src/anim/` is the data layer and
        must not depend on `src/ui/` (the type gate runs mypy over
        `src/anim/`, and importing the UI module from here would drag its
        errors into that gate).
        """
        clip = self.set.clip(clip_id)
        path = self.set.path / clip.dir / f"frame_{frame:02d}.png"
        cached = self._surface_cache.get(path)
        if cached is not None:
            return cached
        if not path.is_file():
            return None
        try:
            loaded = pygame.image.load(str(path)).convert_alpha()
        except pygame.error:
            return None
        self._surface_cache[path] = loaded
        return loaded

    def canvas_for(self, clip_id: str) -> tuple[int, int]:
        """The canvas the clip is drawn on: its OWN, or the set's.

        A clip may override the set's canvas: the mine's death art is
        32x32 inside a 64x64 set, and it has to be centred on ITS OWN
        canvas -- the set's would push it half a screen away.

        The lookup is a `.get()` and not `set.clip()` on purpose: a clip
        id that does not exist draws nothing, and it must not raise.
        """
        clip = self.set.clips.get(clip_id)
        if clip is not None and clip.canvas:
            return clip.canvas
        return self.set.canvas

    def scaled_surface(
        self, clip_id: str, frame: int, part: Part
    ) -> pygame.Surface | None:
        """The frame's surface, scaled by the part's scale.

        The runtime draws the enemy at `_ship_scale_enemy` (1.05) with the
        SAME truncation: `int(32 * 1.05) == 33`. Reproducing that exactly
        is what keeps the golden frames identical.

        A part that declares NO scale gets the raw surface back, untouched:
        that is GOLIATH's case, and the boss must not move a single pixel.
        """
        raw = self.surface(clip_id, frame)
        if raw is None:
            return None
        sx, sy = part.scale
        if sx == 1.0 and sy == 1.0:
            return raw
        width = int(raw.get_width() * sx)
        height = int(raw.get_height() * sy)
        if width <= 0 or height <= 0:
            return None
        key = (clip_id, frame, sx, sy)
        cached = self._scaled_cache.get(key)
        if cached is not None:
            return cached
        scaled = pygame.transform.scale(raw, (width, height))
        self._scaled_cache[key] = scaled
        return scaled

    def draw(
        self,
        target: pygame.Surface,
        clip_id: str,
        frame: int,
        origin: tuple[int, int],
        part_ids: tuple[str, ...] | None = None,
    ) -> None:
        """Draw the parts of one frame, in z order."""
        wanted = set(part_ids) if part_ids else None
        parts = sorted(self.set.parts, key=lambda p: p.z)
        anchor = self.anchors.get(clip_id, frame)
        # The CLIP's canvas, not the set's: a clip that declares one owns
        # the frame it draws.
        canvas = self.canvas_for(clip_id)
        for part in parts:
            if wanted is not None and part.id not in wanted:
                continue
            surf = (
                self.scaled_surface(clip_id, frame, part)
                if part.draw == "frames"
                else None
            )
            draw_part(target, part, surf, anchor, origin, canvas)


# ---------------------------------------------------------------------------
# BLOQUE 75: the loader that reads a set BY KIND
# ---------------------------------------------------------------------------
#
# The enemies live in `Assets/sprites/enemies/<kind>/` and the bosses in
# `Assets/sprites/bosses/<name>/`. `src/anim/manifest.py::_sets_root`
# resolves only the bosses' root, and it is NOT changed: this is the one
# place that knows BOTH roots, and it knows them separately.


def _enemies_root() -> Path:
    """Where the enemy sets live.

    The SAME probe the bosses use (`src/anim/manifest.py::_sets_root`),
    for the other root:

        running from source: <project root>/Assets/sprites/enemies
        frozen (PyInstaller):  <_MEIPASS>/Assets/sprites/enemies

    The probe is resolved on CALL, never at import time: a frozen build
    never needs the source tree.
    """
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass) / "Assets" / "sprites" / "enemies"
    return (
        Path(__file__).resolve().parent.parent.parent
        / "Assets"
        / "sprites"
        / "enemies"
    )


# The player cache: one ClipPlayer per (kind, root). The manifest is
# cached too, by `src.anim.manifest.loaded_set`, and THAT cache is what
# invalidates this one: the entry is only reused while the manifest it
# was built from is still the one the manifest cache holds (the same
# object). `clear_loaded_cache()` therefore drops the players as well,
# without this module having to know about the hook.
_PLAYER_CACHE: dict[tuple[str, Path], tuple[AnimSet, ClipPlayer]] = {}


def load_player_for_kind(kind: str, root: Path | None = None) -> ClipPlayer | None:
    """The ClipPlayer for an enemy kind, or None when it cannot load.

    The enemies live in `Assets/sprites/enemies/<kind>/`; the bosses in
    `Assets/sprites/bosses/<name>/`. This is the ONE place that knows
    both roots -- `src/anim/manifest.py::_sets_root` currently knows
    only the bosses.

    `root` is the directory that HOLDS the sets (the one that contains
    `<kind>/`); None means the default enemies root, resolved at call
    time.

    None -- never an exception -- when the set cannot be loaded: the
    manifest is missing or malformed, or the anchor table cannot be
    read. The caller then falls back to its own drawing path instead of
    breaking the game loop.
    """
    effective_root = _enemies_root() if root is None else root
    # `loaded_set` parses the manifest ONCE, caches the failure too, and
    # degrades a malformed manifest to None instead of raising.
    anim_set = loaded_set(kind, effective_root)
    if anim_set is None:
        return None
    key = (kind, effective_root)
    cached = _PLAYER_CACHE.get(key)
    if cached is not None and cached[0] is anim_set:
        # The SAME manifest object: the player is still current.
        return cached[1]
    try:
        anchors = load_anchors(anim_set.path / "anchors.toml")
    except (OSError, ValueError):
        # A missing or corrupt anchor table degrades to None. The
        # enemies' bodies are drawn with the `fixed` pivot, which does
        # not read the anchor table at all -- but a player without one
        # is not a player, and the caller has a fallback.
        return None
    player = ClipPlayer(anim_set, anchors)
    _PLAYER_CACHE[key] = (anim_set, player)
    return player
