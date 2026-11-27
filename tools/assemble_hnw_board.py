"""Assemble la planche hanche / cou / poignet (Pillow) : python tools/assemble_hnw_board.py DOSSIER_RENDUS SORTIE.png [morphologie]"""
from pathlib import Path
import sys

from PIL import Image, ImageDraw

src, out = Path(sys.argv[1]), sys.argv[2]
morph = sys.argv[3] if len(sys.argv) > 3 else "defaut"
joints = {"hanche_flexion": [0, 60, 120], "hanche_abduction": [0, 20, 40], "cou_rotation": [0, 35, 70], "cou_flexion": [0, 25, 45], "poignet_flexion": [0, 40, 80], "poignet_extension": [0, 35, 70]}
w, h = Image.open(src / f"{morph}_hanche_flexion_0_profil.png").size
rows = [(j, v) for j in joints for v in ("profil", "trois_quarts")]
board = Image.new("RGB", (3 * w + 170, len(rows) * h), "white")
draw = ImageDraw.Draw(board)
for r, (j, v) in enumerate(rows):
    draw.text((6, r * h + h // 2), f"{j}\n{v}", fill="black")
    for c, a in enumerate(joints[j]):
        board.paste(Image.open(src / f"{morph}_{j}_{a}_{v}.png").convert("RGB"), (170 + c * w, r * h))
        draw.text((175 + c * w, r * h + 4), f"{a}°", fill="black")
board.save(out)
