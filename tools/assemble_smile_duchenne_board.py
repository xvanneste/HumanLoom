"""Assemble la planche du sourire de Duchenne (Pillow, hors Blender) : python tools/assemble_smile_duchenne_board.py DOSSIER_RENDUS SORTIE.png"""
from pathlib import Path
import sys

from PIL import Image, ImageDraw

src, out = Path(sys.argv[1]), Path(sys.argv[2])
morphs = ["neutre", "femme_jeune", "homme_age"]
views = [("face", "face"), ("trois_quarts", "3/4"), ("yeux", "yeux (gros plan)")]
levels = [0, 25, 50, 75, 100]
first = Image.open(src / "neutre_face_000.png")
w, h = first.size
pad = 20
rows = len(morphs) * len(views)
board = Image.new("RGB", (len(levels) * w + 110, rows * (h + pad // 2) + pad * 2), "white")
draw = ImageDraw.Draw(board)
for c, level in enumerate(levels):
    draw.text((110 + c * w + w // 2 - 15, 4), f"{level} %", fill="black")
r = 0
for m in morphs:
    for key, label in views:
        y = pad * 2 + r * (h + pad // 2) - pad
        draw.text((4, y + h // 2), f"{m}\n{label}", fill="black")
        for c, level in enumerate(levels):
            board.paste(Image.open(src / f"{m}_{key}_{level:03d}.png").convert("RGB"), (110 + c * w, y))
        r += 1
board.save(out)
print(out, board.size)
