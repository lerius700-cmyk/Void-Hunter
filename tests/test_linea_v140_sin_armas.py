"""BLOQUE 67: esta linea es v1.4.0 — NO tiene sistema de armas.

El 2026-10-25 el usuario corrigio un port que habia metido el sistema de
4 armas (BLOQUE 72 + BLOQUE 73 Fase A/B/C) en la linea v1.4.0:

    "la version 1.4 no tenia armas extra, ni los 4 cuadros donde se
     guardan las armas. nada de armas nuevas. la base es la version 1.4.
     donde no hay armas!!"

Ademas ese port arrastraba d43f7be (BLOQUE 73 Fase A), que borra el
laser de carga del LMB que v1.4.0 SI tiene.

Estos tests son el guard de esa correccion: si alguien vuelve a portar
armas a esta linea, la suite se pone roja.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SRC = ROOT / "src"


def test_no_weapon_slot_module() -> None:
    """El modulo WeaponSlot no existe en la linea v1.4.0."""
    assert not (SRC / "entities" / "weapon_slot.py").exists(), (
        "src/entities/weapon_slot.py no pertenece a la linea v1.4.0"
    )


def test_no_weapon_slot_assets() -> None:
    """Ni los sprites de bala ni los SFX por arma."""
    weapons_sprites = SRC.parent / "Assets" / "sprites" / "weapons"
    if weapons_sprites.is_dir():
        pngs = list(weapons_sprites.glob("bullet_*.png"))
        assert not pngs, f"sprites de bala que no van en esta linea: {pngs}"
    sounds = SRC.parent / "Assets" / "sounds"
    if sounds.is_dir():
        for name in ("shoot_thick", "laser_hum", "flame_loop", "shoot_double"):
            assert not (sounds / f"{name}.wav").exists(), (
                f"el SFX {name}.wav es del sistema de armas de BLOQUE 72, "
                "no de la linea v1.4.0"
            )


def test_hud_has_no_weapon_slot_boxes() -> None:
    """El HUD de v1.4.0 no dibuja los 4 cuadros de slots."""
    hud = (SRC / "ui" / "hud.py").read_text(encoding="utf-8")
    for token in ("weapon_slot", "WeaponSlot", "WEAPON_SLOT", "draw_weapon_slots"):
        assert token not in hud, (
            f"el HUD de la linea v1.4.0 no tiene {token} (eso es BLOQUE 72)"
        )


def test_powerup_kind_has_only_the_v140_weapons() -> None:
    """`PowerupKind` de v1.4.0 tiene WEAPON, no los 4 tipos de arma."""
    from src.entities.asteroid import PowerupKind

    values = {p.value for p in PowerupKind}
    assert "weapon" in values, "v1.4.0 tiene el powerup WEAPON original"
    for arma in ("thick", "laser", "flame", "double"):
        assert not any(arma in v for v in values), (
            f"PowerupKind no deberia tener el tipo de arma '{arma}' "
            "(BLOQUE 72, no pertenece a la linea v1.4.0)"
        )


def test_lmb_charge_laser_still_exists() -> None:
    """El laser de carga del LMB es de v1.4.0: BLOQUE 73 Fase A lo borra.

    Ese commit (d43f7be) vino con el port del sistema de armas. Al
    revertir las armas, el laser de carga tiene que seguir en su sitio.
    """
    player = (SRC / "entities" / "player" / "player.py").read_text(encoding="utf-8")
    assert "charge" in player.lower(), (
        "el laser de carga del LMB desaparecio: no hay que portar BLOQUE 73 "
        "Fase A a esta linea"
    )


def test_input_has_no_weapon_slot_remap() -> None:
    """v1.4.0 no remapea la rueda del mouse ni el RMB a los slots de arma."""
    settings = (SRC / "core" / "settings.py").read_text(encoding="utf-8")
    for token in ("WEAPON_SLOT", "weapon_slot", "CYCLE_WEAPON"):
        assert token not in settings, (
            f"settings.py no deberia tener {token} (BLOQUE 72)"
        )
