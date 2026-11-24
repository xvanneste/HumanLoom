"""Assemble la planche des vêtements (Pillow) : python tools/assemble_garments_board.py DOSSIER_RENDUS SORTIE.png"""
from pathlib import Path
import sys

from PIL import Image, ImageDraw

src, out = Path(sys.argv[1]), Path(sys.argv[2])
outfits = ["tenue_A", "tenue_B", "tenue_C"]
morphs = ["defaut", "homme_age", "femme_jeune", "enfant", "gabarit"]
states = ["repos", "pose"]
first = Image.open(src / f"{outfits[0]}_{morphs[0]}_repos.png")
w, h = first.size
board = Image.new("RGB", (len(morphs) * w + 90, len(outfits) * len(states) * h + 24), "white")
draw = ImageDraw.Draw(board)
for c, m in enumerate(morphs):
    draw.text((90 + c * w + w // 2 - 25, 6), m, fill="black")
r = 0
for o in outfits:
    for s in states:
        draw.text((4, 24 + r * h + h // 2), f"{o}\n{s}", fill="black")
        for c, m in enumerate(morphs):
            board.paste(Image.open(src / f"{o}_{m}_{s}.png").convert("RGB"), (90 + c * w, 24 + r * h))
        r += 1
board.save(out)
print(out, board.size)
