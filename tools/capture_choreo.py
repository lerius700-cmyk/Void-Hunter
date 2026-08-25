"""Capture running game window for visual verification."""
import sys
import time
from pathlib import Path

sys.path.insert(0, r'D:\AI\void-hunter')
from PIL import ImageGrab
import ctypes
import ctypes.wintypes as wt

user32 = ctypes.windll.user32

# Hardcoded handle - update if needed
HWND = 787862
OUT_DIR = Path(r'D:\AI\void-hunter\release')

rect = wt.RECT()
user32.GetWindowRect(HWND, ctypes.byref(rect))
print(f'Window: {rect.left},{rect.top} -> {rect.right},{rect.bottom}')

HWND_TOPMOST = -1
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_SHOWWINDOW = 0x0040
user32.SetWindowPos(HWND, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
time.sleep(0.5)

OUT_DIR.mkdir(parents=True, exist_ok=True)
# Capture the title screen with the new 6-nebula fade behavior.
# 6 nebulae desync naturally (random hold timers), so over 25s we
# should see at least some of them mid-fade.
for i in range(8):
    img = ImageGrab.grab(bbox=(rect.left, rect.top, rect.right, rect.bottom))
    out = OUT_DIR / f'verify_title_{i:02d}.png'
    img.save(out)
    print(f'Saved {out} {img.size[0]}x{img.size[1]}')
    time.sleep(3.0)
