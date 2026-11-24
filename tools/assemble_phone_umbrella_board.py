"""Assemble la planche téléphone / parapluie (Pillow) : python tools/assemble_phone_umbrella_board.py DOSSIER_RENDUS SORTIE.png"""
from pathlib import Path
import sys

from PIL import Image, ImageDraw

src, out = Path(sys.argv[1]), Path(sys.argv[2])
rows = [
    [("1_tel_main", "téléphone en main"), ("2_oreille_face", "à l'oreille : face"), ("3_oreille_3q", "3/4"), ("4_oreille_profil", "profil")],
    [("5_parapluie_ferme_corps", "parapluie fermé"), ("6_parapluie_ferme_main", "main (fermé)"), ("7_parapluie_ouvert_corps", "parapluie ouvert"), ("8_parapluie_ouvert_main", "main (ouvert)")],
]
first = Image.open(src / (rows[0][0][0] + ".png"))
w, h = first.size
board = Image.new("RGB", (4 * w, 2 * (h + 16)), "white")
draw = ImageDraw.Draw(board)
for r, row in enumerate(rows):
    for c, (name, label) in enumerate(row):
        board.paste(Image.open(src / (name + ".png")).convert("RGB"), (c * w, r * (h + 16) + 16))
        draw.text((c * w + 6, r * (h + 16) + 2), label, fill="black")
board.save(out)
print(out, board.size)
