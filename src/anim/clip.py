"""BLOQUE 74: the clip player.

Turns elapsed time into a frame index and composes the parts of a clip
into a target surface.

The timing is driven by the manifest's fps, so the animation no longer
depends on a constant hardcoded in the boss class.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pygame

from src.anim.anchors import AnchorSet
from src.anim.manifest import AnimSet, Clip
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

    def state(self, clip_id: str, elapsed: float) -> ClipState:
        """The frame index for `elapsed` seconds into `clip_id`."""
        clip = self.set.clip(clip_id)
        if clip.frames <= 0:
            return ClipState(clip=clip, frame=0)
        step = 1.0 / clip.fps if clip.fps > 0 else 0.1
        index = int(elapsed / step)
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
        for part in parts:
            if wanted is not None and part.id not in wanted:
                continue
            surf = self.surface(clip_id, frame) if part.draw == "frames" else None
            draw_part(target, part, surf, anchor, origin, self.set.canvas)
