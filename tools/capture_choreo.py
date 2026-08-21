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
HWND = 656008
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
for i in range(10):
    img = ImageGrab.grab(bbox=(rect.left, rect.top, rect.right, rect.bottom))
    out = OUT_DIR / f'choreo_{i:02d}.png'
    img.save(out)
    print(f'Saved {out} {img.size[0]}x{img.size[1]}')
    time.sleep(1.5)
