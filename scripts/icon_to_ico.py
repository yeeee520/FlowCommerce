"""将像素皇冠鲸鱼图标转为 .ico 格式"""
from PIL import Image
from pathlib import Path

src = Path(__file__).parent.parent / "static" / "icons" / "A_super_cute_kawaii_pixel_art__2026-07-03T08-25-14.png"
dst = Path(__file__).parent.parent / "icon.ico"

img = Image.open(src).convert("RGBA")

# 正方形裁剪
w, h = img.size
size = min(w, h)
left = (w - size) // 2
top = (h - size) // 2
img = img.crop((left, top, left + size, top + size))

sizes = [256, 128, 64, 48, 32, 16]
img.save(dst, format="ICO", sizes=[(s, s) for s in sizes])
print(f"icon.ico generated! sizes: {sizes}")
print(f"path: {dst}")
