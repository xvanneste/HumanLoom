"""Assemble les planches AVANT / APRÈS des articulations (Pillow) : python tools/assemble_joint_board.py DOSSIER_RENDUS SORTIE_PREFIXE  (une image par morphologie : SORTIE_PREFIXE_<morphologie>.png)."""
from pathlib import Path
import sys

from PIL import Image, ImageDraw

src, prefix = Path(sys.argv[1]), sys.argv[2]
joints = {"coude": [0, 45, 90, 120, 150], "epaule": [0, 45, 90, 135, 180], "genou": [0, 45, 90, 135]}
views = ["profil", "trois_quarts"]
for morph in ("defaut", "femme_jeune", "homme_age"):
    first = Image.open(src / f"avant_{morph}_coude_0_profil.png")
    w, h = first.size
    rows = [(j, v, s) for j in joints for v in views for s in ("avant", "apres")]
    board = Image.new("RGB", (5 * w + 150, len(rows) * h + 20), "white")
    draw = ImageDraw.Draw(board)
    for r, (joint, view, state) in enumerate(rows):
        y = 20 + r * h
        draw.text((4, y + h // 2), f"{joint}\n{view}\n{'AVANT' if state == 'avant' else 'APRÈS'}", fill="black")
        for c, angle in enumerate(joints[joint]):
            board.paste(Image.open(src / f"{state}_{morph}_{joint}_{angle}_{view}.png").convert("RGB"), (150 + c * w, y))
            if r == 0:
                draw.text((150 + c * w + 4, 4), f"coude {angle}°", fill="black")
    # étiquettes d'angles des autres articulations : dans la marge gauche de la première ligne de chaque articulation
    for r, (joint, view, state) in enumerate(rows):
        if view == "profil" and state == "avant":
            draw.text((4, 20 + r * h + 4), " / ".join(str(a) for a in joints[joint]) + "°", fill="black")
    board.save(f"{prefix}_{morph}.png")
    print(f"{prefix}_{morph}.png", board.size)
