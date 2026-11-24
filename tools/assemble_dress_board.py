"""Assemble la planche des robes simulées (Pillow) : python tools/assemble_dress_board.py DOSSIER_RENDUS SORTIE.png"""
from pathlib import Path
import sys

from PIL import Image, ImageDraw

src, out = Path(sys.argv[1]), Path(sys.argv[2])
rows = [("defaut", "corps par défaut"), ("femme_jeune", "femme jeune"), ("gabarit", "gabarit jambes+1 torse-1")]
columns = [("repos", "repos"), ("marche", "marche (image 10)"), ("bras_leve", "bras levés (image 20)")]
first = Image.open(src / "defaut_repos.png")
w, h = first.size
others = ["autres_robe_courte.png", "autres_robe_longue.png", "autres_jupe.png"]
board = Image.new("RGB", (3 * w + 110, (len(rows) + 1) * (h + 18)), "white")
draw = ImageDraw.Draw(board)
for c, (_, label) in enumerate(columns):
    draw.text((110 + c * w + 6, 3), label, fill="black")
for r, (key, label) in enumerate(rows):
    y = 18 + r * (h + 18)
    draw.text((4, y + h // 2), label, fill="black")
    for c, (column, _) in enumerate(columns):
        board.paste(Image.open(src / f"{key}_{column}.png").convert("RGB"), (110 + c * w, y))
y = 18 + len(rows) * (h + 18)
draw.text((4, y + h // 2), "autres pièces\nen marche", fill="black")
for c, name in enumerate(others):
    board.paste(Image.open(src / name).convert("RGB"), (110 + c * w, y))
    draw.text((110 + c * w + 6, y + 3), name.replace("autres_", "").replace(".png", ""), fill="black")
board.save(out)
print(out, board.size)
