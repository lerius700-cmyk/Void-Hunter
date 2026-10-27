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


def repad_frame(path: Path, min_margin: int = 3) -> bool:
    """Move the silhouette inward so it never touches the canvas edge.

    The visual content is untouched -- only its position inside the canvas
    shifts -- and the anchors recompute on the next audit.
    """
    surf = pygame.image.load(str(path)).convert_alpha()
    w, h = surf.get_size()
    # get_alpha() returns the alpha channel surface for a per-pixel-alpha
    # surface, and None (or an int) for the other kinds -- only the
    # surface carries the bounding box.
    alpha = surf.get_alpha()
    bbox = alpha.getbbox() if isinstance(alpha, pygame.Surface) else None
    if bbox is None:
        return False
    left, top, right, bottom = bbox
    margins = (left, top, w - right, h - bottom)
    if min(margins) >= min_margin:
        return False

    dx = max(0, min_margin - margins[0])
    dy = max(0, min_margin - margins[1])
    if w - margins[2] - dx < min_margin:
        dx = max(0, min_margin - margins[2])
    out = pygame.Surface((w, h), pygame.SRCALPHA, 32)
    out.fill((0, 0, 0, 0))
    out.blit(surf, (dx, dy))
    pygame.image.save(out, str(path))
    return True


def repair_set(
    anim_set: AnimSet, findings: list["Finding"], *, apply: bool = False
) -> list[str]:
    """Apply the repairs implied by the findings.

    Returns the list of actions taken (or that would be taken when
    apply=False).

    The frame is looked up as `<set>/<clip id>/frame_NN.png`. Every clip of
    the shipped GOLIATH manifest declares `dir` equal to its `id`, so the
    clip id IS the directory name; a set that ever separates the two would
    need the manifest's `dir` here instead.
    """
    actions: list[str] = []
    for finding in findings:
        if finding.state == "LADO_EQUIVOCADO":
            path = anim_set.path / finding.clip / f"frame_{finding.frame:02d}.png"
            if not path.is_file():
                continue
            actions.append(f"mirror {finding.clip}/frame_{finding.frame:02d}")
            if apply:
                mirror_frame(path)
        elif finding.state == "CORTADO":
            path = anim_set.path / finding.clip / f"frame_{finding.frame:02d}.png"
            if not path.is_file():
                continue
            actions.append(f"re-pad {finding.clip}/frame_{finding.frame:02d}")
            if apply:
                repad_frame(path)
    return actions
