"""Quick screenshot capture for the running game window."""
import sys
sys.path.insert(0, r'D:\AI\void-hunter')
from PIL import ImageGrab
import ctypes
import ctypes.wintypes as wt
import time

user32 = ctypes.windll.user32

hwnd = 4984192
rect = wt.RECT()
user32.GetWindowRect(hwnd, ctypes.byref(rect))
print(f'Window: {rect.left},{rect.top} -> {rect.right},{rect.bottom}')

HWND_TOPMOST = -1
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | 0x0040)
time.sleep(0.5)

out_dir = r'D:\AI\void-hunter\release'
for i in range(10):
    img = ImageGrab.grab(bbox=(rect.left, rect.top, rect.right, rect.bottom))
    out = out_dir + '\\verify_vh_restored_' + str(i).zfill(2) + '.png'
    img.save(out)
    print('Saved', out, img.size[0], 'x', img.size[1])
    time.sleep(1.0)
