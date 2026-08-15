"""Capture the actual .exe game window to verify the new galaxy background."""
from __future__ import annotations
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Find the void-hunter window and capture it
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

# Find window by title
hwnd = None
def enum_windows_proc(h, lParam):
    global hwnd
    length = user32.GetWindowTextLengthW(h)
    if length > 0:
        buff = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(h, buff, length + 1)
        if "VOID HUNTER" in buff.value.upper():
            hwnd = h
            return False
    return True
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
user32.EnumWindows(WNDENUMPROC(enum_windows_proc), 0)
if not hwnd:
    print("[ERROR] VOID HUNTER window not found")
    sys.exit(1)
print(f"Found window: hwnd={hwnd}")

# Get window rect
rect = wintypes.RECT()
user32.GetWindowRect(hwnd, ctypes.byref(rect))
print(f"Window rect: {rect.left},{rect.top} -> {rect.right},{rect.bottom} ({rect.right-rect.left}x{rect.bottom-rect.top})")

# Get window DC
hwnd_dc = user32.GetWindowDC(hwnd)
mfc_dc = gdi32.CreateCompatibleDC(hwnd_dc)
bitmap = gdi32.CreateCompatibleBitmap(hwnd_dc, rect.right-rect.left, rect.bottom-rect.top)
gdi32.SelectObject(mfc_dc, bitmap)

# PrintWindow with PW_RENDERFULLCONTENT (3) to capture the surface
result = user32.PrintWindow(hwnd, mfc_dc, 3)
print(f"PrintWindow result: {result}")

# Save as BMP first
out_bmp = ROOT / "tools" / "playtest_out" / "galaxy_real.bmp"
gdi32.BitBlt(mfc_dc, 0, 0, rect.right-rect.left, rect.bottom-rect.top, hwnd_dc, 0, 0, 0x00CC0020)
# Use a different approach: save bitmap
import struct
# Get BITMAPINFO
class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", ctypes.c_uint32),
        ("biWidth", ctypes.c_int32),
        ("biHeight", ctypes.c_int32),
        ("biPlanes", ctypes.c_uint16),
        ("biBitCount", ctypes.c_uint16),
        ("biCompression", ctypes.c_uint32),
        ("biSizeImage", ctypes.c_uint32),
        ("biXPelsPerMeter", ctypes.c_int32),
        ("biYPelsPerMeter", ctypes.c_int32),
        ("biClrUsed", ctypes.c_uint32),
        ("biClrImportant", ctypes.c_uint32),
    ]
class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", ctypes.c_uint32 * 3)]
bmi = BITMAPINFO()
bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
bmi.bmiHeader.biWidth = rect.right - rect.left
bmi.bmiHeader.biHeight = -(rect.bottom - rect.top)  # negative for top-down
bmi.bmiHeader.biPlanes = 1
bmi.bmiHeader.biBitCount = 32
bmi.bmiHeader.biCompression = 0  # BI_RGB
bmi.bmiHeader.biSizeImage = 0
w, h = rect.right - rect.left, rect.bottom - rect.top
buf = ctypes.create_string_buffer(w * h * 4)
gdi32.GetDIBits(mfc_dc, bitmap, 0, h, buf, ctypes.byref(bmi), 0)

# Convert to PNG using pygame
import pygame
pygame.init()
surf = pygame.image.frombuffer(buf, (w, h), "BGRA")
out_png = ROOT / "tools" / "playtest_out" / "galaxy_real.png"
pygame.image.save(surf, str(out_png))
print(f"Saved {out_png}")

# Cleanup
gdi32.DeleteObject(bitmap)
gdi32.DeleteDC(mfc_dc)
user32.ReleaseDC(hwnd, hwnd_dc)
