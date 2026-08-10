# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for VOID HUNTER (BLOQUE 54).

Builds a single-folder distribution `dist/void-hunter/` with the launcher
executable at `dist/void-hunter/void-hunter.exe`. No external assets to bundle
(the game is fully procedural: graphics drawn in code, audio synthesized).

Usage:
    pyinstaller build.spec            # one-time build
    pyinstaller build.spec --clean    # nuke build/ + dist/ first

Output:
    dist/void-hunter/void-hunter.exe  ~ launcher
    dist/void-hunter/_internal/       python runtime + pygame + game code

Size: ~15-25 MB (mostly Python stdlib + pygame).
"""
from pathlib import Path
import sys

# Resolve project root so the spec is location-independent.
PROJECT_ROOT = Path(SPECPATH).resolve()  # SPECPATH is injected by PyInstaller

block_cipher = None

a = Analysis(
    [str(PROJECT_ROOT / "main.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=[],
    hiddenimports=[
        # pygame submodules that PyInstaller's static analysis can miss.
        "pygame",
        "pygame.mixer",
        "pygame.font",
        "pygame.image",
        "pygame.transform",
        "pygame.draw",
        "pygame.surface",
        "pygame.time",
        "pygame.event",
        "pygame.display",
        "pygame.key",
        "pygame.mouse",
        "pygame.joystick",
        "pygame.scrap",
        "pygame.sndarray",
        "pygame.surfarray",
        "pygame.math",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Strip unused heavy stdlib to keep the .exe lean.
        "tkinter",
        "unittest",
        "xml",
        "xmlrpc",
        "pydoc",
        "doctest",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,  # split: binaries go in _internal/, exe is small
    name="void-hunter",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX would shrink but adds AV false-positive risk
    console=False,  # GUI subsystem on Windows (no terminal window)
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon=str(PROJECT_ROOT / "tools" / "playtest_out" / "polish_29_goliath_phase1.png"),  # uncomment if you add an .ico
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="void-hunter",
)
