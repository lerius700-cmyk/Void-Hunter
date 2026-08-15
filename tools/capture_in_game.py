"""Launch the .exe and capture a screenshot at t=45s to see the sub-boss state.

Uses PIL to grab the game window via PrintWindow at specific times.
"""
import os
import sys
import time
import subprocess
from pathlib import Path
import ctypes
from ctypes import wintypes

ROOT = Path(__file__).resolve().parent.parent
EXE = ROOT / "dist" / "void-hunter" / "void-hunter.exe"
OUT = ROOT / "tools" / "playtest_out" / "in_game_sub_boss_check.png"
OUT.parent.mkdir(parents=True, exist_ok=True)

# Start the .exe
print(f"Launching: {EXE}")
proc = subprocess.Popen([str(EXE)], cwd=str(ROOT / "dist" / "void-hunter"))
print(f"PID: {proc.pid}")

# Wait for the game window
user32 = ctypes.windll.user32
time.sleep(3.0)

# Find the window
hwnd = None
def enum_windows_callback(h, lParam):
    global hwnd
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
    if pid.value == proc.pid:
        length = user32.GetWindowTextLengthW(h)
        if length > 0:
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(h, buff, length + 1)
            if "VOID" in buff.value:
                hwnd = h
                return False
    return True
ENUM_PROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))
user32.EnumWindows(ENUM_PROC(enum_windows_callback), 0)

if not hwnd:
    print("Could not find game window")
    proc.terminate()
    sys.exit(1)

print(f"Found window: hwnd={hwnd}")

# Wait until t=45s of gameplay
# The game starts when the user clicks. We need to click on the title screen first.
# For now, just wait 45s and capture whatever is on screen.
print("Waiting 45s for gameplay to progress...")
time.sleep(45.0)

# Capture the window
class RECT(ctypes.Structure):
    _fields_ = [("L", ctypes.c_long), ("T", ctypes.c_long),
                ("R", ctypes.c_long), ("B", ctypes.c_long)]
r = RECT()
user32.GetWindowRect(hwnd, ctypes.byref(r))
w = r.R - r.L
h = r.B - r.T
print(f"Window rect: {r.L},{r.T} -> {r.R},{r.B} ({w}x{h})")

# Use PrintWindow to capture
import ctypes.wintypes as wt
PW_RENDERFULLCONTENT = 0x00000002
hdc = user32.GetDC(hwnd)
from PIL import Image
bmp = Image.new("RGB", (w, h))
# Use win32gui PrintWindow via ctypes
gdi32 = ctypes.windll.gdi32
hdc_mem = gdi32.CreateCompatibleDC(hdc)
hbm = gdi32.CreateCompatibleBitmap(hdc, w, h)
gdi32.SelectObject(hdc_mem, hbm)
user32.PrintWindow(hwnd, hdc_mem, PW_RENDERFULLCONTENT)

# Get bitmap bits
bmpinfo = ctypes.create_string_buffer(40)
gdi32.GetBitmapBits(hbm, w * h * 4, bmpinfo)
gdi32.DeleteObject(hbm)
gdi32.DeleteDC(hdc_mem)
user32.ReleaseDC(hwnd, hdc)

# Save as PNG
bmp.frombytes(bytes(bmpinfo)[:w*h*4])
bmp = bmp.resize((320, 480))  # Resize to internal playfield size
bmp.save(str(OUT))
print(f"Saved: {OUT}")

# Check the sub-boss log
log_path = ROOT / "logs" / "_sub_boss.log"
if log_path.exists():
    print(f"\n_sub_boss.log contents:")
    with open(log_path) as f:
        for line in f.readlines()[-10:]:
            print(f"  {line.rstrip()}")
else:
    print(f"\n_sub_boss.log does not exist at {log_path}")

# Cleanup
proc.terminate()
time.sleep(1.0)
if proc.poll() is None:
    proc.kill()
