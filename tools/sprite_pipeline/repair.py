"""BLOQUE 74: deterministic, idempotent repairs.

Each failure state is repaired at the layer where it is actually fixable:

    LADO_EQUIVOCADO  build (PNG)  mirror the frame horizontally
    CORTADO          build (PNG)  re-pad onto a fresh transparent canvas
    FUERA_DE_RANGO   anchors      interpolate from the neighbouring frames
    AUSENTE          anchors      interpolate from the neighbouring frames
    FIRMA_AMBIGUA    config       widen detect.warm_fallback
    ESCALADO         --           reported, never auto-repaired (pixel art)
    COLAPSADO        --           not repairable: the art is gone

Repairs run with apply=False by default, so the caller must ask for the
writes explicitly.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pygame

from src.anim.manifest import AnimSet
from src.anim.measure import CORTADO_MARGIN, silhouette_margins

if TYPE_CHECKING:  # pragma: no cover - import cycle guard for type checkers
    from sprite_pipeline.audit import Finding


def mirror_frame(path: Path) -> bool:
    """Mirror a frame horizontally inside its own canvas.

    The canvas size is preserved, so the manifest's canvas stays valid.
    Returns True when the file was written.
    """
    surf = pygame.image.load(str(path)).convert_alpha()
    flipped = pygame.transform.flip(surf, True, False)
    pygame.image.save(flipped, str(path))
    return True


def _shift_for_margins(low: int, high: int, min_margin: int) -> int | None:
    """How far to move a silhouette that has `low` px before it and `high`
    px after it, so that both margins reach `min_margin`.

    Returns None when no shift can do that: the silhouette is then wider
    than the canvas minus two margins, and the only thing that would fix
    it is scaling -- which pixel art does not get.

    The shift is the smallest one that gives the too-close side its
    margin, and it never pushes the content past the opposite edge.
    """
    if low >= min_margin and high >= min_margin:
        return 0
    if low + high < 2 * min_margin:
        return None
    if low < min_margin:
        return min_margin - low
    return -(min_margin - high)


def repad_frame(path: Path, min_margin: int = CORTADO_MARGIN) -> bool:
    """Move the silhouette inward so it never touches the canvas edge.

    The visual content is untouched -- only its position inside the canvas
    shifts -- and the anchors recompute on the next audit. The canvas
    keeps its size: the sprite is MOVED inside its own canvas, never
    scaled.

    The bounding box comes from `src.anim.measure.silhouette_margins`, the
    SAME helper the auditor uses to raise the CORTADO finding, so the
    repair and the finding can never disagree about what "cut off" means.
    (pygame's `Surface.get_alpha()` is NOT that helper: it returns the
    surface's alpha VALUE -- the int 255 for a per-pixel-alpha surface --
    and never a channel to measure.)

    `min_margin` defaults to CORTADO_MARGIN, the threshold the auditor
    flags below. The repair targets exactly the threshold the auditor
    applies: a stricter target would leave frames the auditor flags
    unrepaired (the set could never pass), and a looser one would move
    art that does not need to move.

    Returns True when the file was written.
    """
    surf = pygame.image.load(str(path)).convert_alpha()
    w, h = surf.get_size()
    margins = silhouette_margins(surf)
    if margins is None:
        return False
    left, top, right, bottom = margins
    if min(margins) >= min_margin:
        return False

    dx = _shift_for_margins(left, right, min_margin)
    dy = _shift_for_margins(top, bottom, min_margin)
    if dx is None or dy is None:
        # No translation can give the silhouette its margin on every side.
        return False
    if dx == 0 and dy == 0:
        return False

    out = pygame.Surface((w, h), pygame.SRCALPHA, 32)
    out.fill((0, 0, 0, 0))
    out.blit(surf, (dx, dy))
    pygame.image.save(out, str(path))
    return True


def _frame_path(anim_set: AnimSet, clip_id: str, frame: int) -> Path | None:
    """The PNG of one frame, or None when the clip is unknown.

    A finding names the clip by ID; the DIRECTORY that holds the frames is
    the manifest's `clip.dir`. The two are allowed to differ, so the
    directory is always resolved from the manifest and never assumed to
    be the id.
    """
    clip = anim_set.clips.get(clip_id)
    if clip is None:
        return None
    return anim_set.path / clip.dir / f"frame_{frame:02d}.png"


def repair_set(
    anim_set: AnimSet, findings: list["Finding"], *, apply: bool = False
) -> list[str]:
    """Apply the repairs implied by the findings.

    Returns the list of actions ACTUALLY taken. With apply=False the
    actions are the ones that WOULD be taken and the wording says so, so a
    dry run and a real run never print the same line.

    A repair that could not be performed is NOT reported: the list is
    what happened, not what was attempted.

    The frame is looked up as `<set>/<clip dir>/frame_NN.png`, with the
    directory taken from the manifest (`clip.dir`).
    """
    actions: list[str] = []
    for finding in findings:
        if finding.state not in ("LADO_EQUIVOCADO", "CORTADO"):
            continue
        path = _frame_path(anim_set, finding.clip, finding.frame)
        if path is None or not path.is_file():
            continue
        # The message names the FILE, so it uses the directory.
        name = f"{path.parent.name}/frame_{finding.frame:02d}"
        if finding.state == "LADO_EQUIVOCADO":
            if not apply:
                actions.append(f"would mirror {name}")
                continue
            if mirror_frame(path):
                actions.append(f"mirrored {name}")
        else:
            if not apply:
                actions.append(f"would re-pad {name}")
                continue
            if repad_frame(path):
                actions.append(f"re-padded {name}")
    return actions
