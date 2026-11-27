"""Assemble les planches des correctifs de flexion (Pillow) : python tools/assemble_hinge_board.py DOSSIER_RENDUS PREFIXE_SORTIE

Produit PREFIXE_coude.png, PREFIXE_genou.png (profil et trois-quarts, AVANT / APRÈS [/ RECALCULÉ] par morphologie) et PREFIXE_poses.png (téléphone à l'oreille, accroupi, vêtements)."""
from pathlib import Path
import sys

from PIL import Image, ImageDraw

src, prefix = Path(sys.argv[1]), sys.argv[2]
MORPHS = [("defaut", "corps par défaut"), ("femme_jeune", "femme jeune"), ("homme_age", "homme âgé")]
LABELS = {"avant": "AVANT (sans correctifs)", "apres": "APRÈS (correctifs livrés)", "recalcule": "APRÈS RECALCUL (cette morphologie)"}


def states_for(morph):
    return [s for s in ("avant", "apres", "recalcule") if (src / f"{s}_{morph}_coude_L_0_profil.png").exists()]


def board(joint, angles, out):
    rows = [(m, label, v, s) for m, label in MORPHS for v in ("profil", "trois_quarts") for s in states_for(m)]
    probe = Image.open(src / f"avant_defaut_{joint}_L_0_profil.png")
    w, h = probe.size
    image = Image.new("RGB", (len(angles) * w + 230, len(rows) * h + 22), "white")
    draw = ImageDraw.Draw(image)
    for c, a in enumerate(angles):
        draw.text((230 + c * w + 6, 5), f"{joint} {a}°", fill="black")
    for r, (m, label, v, s) in enumerate(rows):
        y = 22 + r * h
        draw.text((4, y + h // 2 - 18), f"{label}\n{v.replace('_', '-')}\n{LABELS[s]}", fill="black")
        for c, a in enumerate(angles):
            path = src / f"{s}_{m}_{joint}_L_{a}_{v}.png"
            if path.exists():
                image.paste(Image.open(path).convert("RGB"), (230 + c * w, y))
    image.save(out)
    print(out, image.size)


board("coude", [0, 45, 90, 120, 150], f"{prefix}_coude.png")
board("genou", [0, 45, 90, 135], f"{prefix}_genou.png")
cols = [("telephone_face", "téléphone : face"), ("telephone_profil", "téléphone : profil"), ("accroupi_profil", "accroupi : profil"), ("accroupi_trois_quarts", "accroupi : 3/4"),
        ("vetements_coude", "vêtements : coude 110°"), ("vetements_genou", "vêtements : genou 110°")]
rows = [(m, label, s) for m, label in MORPHS for s in states_for(m)]
probe = Image.open(src / "avant_defaut_telephone_face.png")
w, h = probe.size
image = Image.new("RGB", (len(cols) * w + 230, len(rows) * h + 22), "white")
draw = ImageDraw.Draw(image)
for c, (_, label) in enumerate(cols):
    draw.text((230 + c * w + 6, 5), label, fill="black")
for r, (m, label, s) in enumerate(rows):
    y = 22 + r * h
    draw.text((4, y + h // 2 - 12), f"{label}\n{LABELS[s]}", fill="black")
    for c, (name, _) in enumerate(cols):
        path = src / f"{s}_{m}_{name}.png"
        if path.exists():
            image.paste(Image.open(path).convert("RGB"), (230 + c * w, y))
image.save(f"{prefix}_poses.png")
print(f"{prefix}_poses.png", image.size)
