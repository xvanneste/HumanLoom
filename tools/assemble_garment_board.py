"""Assemble la planche du dégagement de flexion des vêtements (Pillow) : python tools/assemble_garment_board.py DOSSIER_RENDUS PREFIXE_SORTIE

Produit PREFIXE_coude.png et PREFIXE_genou.png (lignes : profil / trois-quarts × sans / clés / passe ; colonnes : angles)."""
from pathlib import Path
import sys

from PIL import Image, ImageDraw

src, prefix = Path(sys.argv[1]), sys.argv[2]
LABELS = {"sans": "SANS (peau seule)", "cles": "AVEC clés de dégagement", "passe": "Passe Shrinkwrap seule"}


def board(joint, angles, out):
    rows = [(v, s) for v in ("profil", "trois_quarts") for s in ("sans", "cles", "passe")]
    probe = Image.open(src / f"sans_{joint}_0_profil.png")
    w, h = probe.size
    image = Image.new("RGB", (len(angles) * w + 200, len(rows) * h + 22), "white")
    draw = ImageDraw.Draw(image)
    for c, a in enumerate(angles):
        draw.text((200 + c * w + 6, 5), f"{joint} {a}°", fill="black")
    for r, (v, s) in enumerate(rows):
        y = 22 + r * h
        draw.text((4, y + h // 2 - 12), f"{v.replace('_', '-')}\n{LABELS[s]}", fill="black")
        for c, a in enumerate(angles):
            path = src / f"{s}_{joint}_{a}_{v}.png"
            if path.exists():
                image.paste(Image.open(path).convert("RGB"), (200 + c * w, y))
    image.save(out)
    print(out, image.size)


board("coude", [0, 90, 110, 135, 150], f"{prefix}_coude.png")
board("genou", [0, 90, 110, 135], f"{prefix}_genou.png")
