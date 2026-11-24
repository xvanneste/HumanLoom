"""Assemble la planche des accessoires (Pillow) : python tools/assemble_accessories_board.py DOSSIER_RENDUS SORTIE.png"""
from pathlib import Path
import sys

from PIL import Image, ImageDraw

src, out = Path(sys.argv[1]), Path(sys.argv[2])
files = sorted(src.glob("scene_*.png"))
first = Image.open(files[0])
w, h = first.size
columns = 3
rows = (len(files) + columns - 1) // columns
board = Image.new("RGB", (columns * w, rows * (h + 18)), "white")
draw = ImageDraw.Draw(board)
for i, f in enumerate(files):
    x, y = (i % columns) * w, (i // columns) * (h + 18)
    draw.text((x + 4, y + 3), f.stem.replace("scene_", ""), fill="black")
    board.paste(Image.open(f).convert("RGB"), (x, y + 18))
board.save(out)
print(out, board.size)
