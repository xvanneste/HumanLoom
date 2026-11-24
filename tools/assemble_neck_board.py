"""Planche du cou à 80° (Pillow) : python tools/assemble_neck_board.py DOSSIER_RENDUS SORTIE.png  (rendus de `diagnose_neck.py --angles 60,70,80 --images 1 --tag lbs`)."""
from pathlib import Path
import sys

from PIL import Image, ImageDraw

src, out = Path(sys.argv[1]), Path(sys.argv[2])
morphs = ["neutre", "homme_age", "femme_jeune"]
poses = ["axiale_80", "flexion_80"]
views = ["face", "trois_quarts", "profil"]
cell = 300
board = Image.new("RGB", (3 * cell + 110, 6 * (cell + 14)), "white")
draw = ImageDraw.Draw(board)
row = 0
for m in morphs:
    for p in poses:
        y = row * (cell + 14)
        draw.text((4, y + cell // 2), f"{m}\n{p}", fill="black")
        for c, v in enumerate(views):
            image = Image.open(src / f"cou_lbs_{m}_{p}_{v}.png").convert("RGB").resize((cell, cell))
            board.paste(image, (110 + c * cell, y + 14))
            if row == 0:
                draw.text((110 + c * cell + 4, y + 1), v, fill="black")
        row += 1
board.save(out)
print(out, board.size)
