"""Assemble la planche de l'épaule (Pillow) : python tools/assemble_shoulder_board.py DOSSIER_RENDUS PREFIXE_SORTIE [morph]

Une ligne par (plan, vue), une colonne par angle ; une planche par variante présente (actuel, rythme)."""
from pathlib import Path
import sys

from PIL import Image, ImageDraw

src, prefix = Path(sys.argv[1]), sys.argv[2]
morph = sys.argv[3] if len(sys.argv) > 3 else "defaut"
ANGLES = [0, 45, 90, 135, 180]
VIEWS = ["face", "profil", "trois_quarts", "aisselle"]
for variant in ("actuel", "rythme"):
    if not (src / f"{variant}_{morph}_frontal_0_face.png").exists():
        continue
    probe = Image.open(src / f"{variant}_{morph}_frontal_0_face.png")
    w, h = probe.size
    rows = [(plane, view) for plane in ("frontal", "sagittal") for view in VIEWS]
    image = Image.new("RGB", (len(ANGLES) * w + 150, len(rows) * h + 22), "white")
    draw = ImageDraw.Draw(image)
    for c, a in enumerate(ANGLES):
        draw.text((150 + c * w + 6, 5), f"élévation {a}°", fill="black")
    for r, (plane, view) in enumerate(rows):
        y = 22 + r * h
        draw.text((4, y + h // 2 - 8), f"{plane}\n{view.replace('_', '-')}", fill="black")
        for c, a in enumerate(ANGLES):
            path = src / f"{variant}_{morph}_{plane}_{a}_{view}.png"
            if path.exists():
                image.paste(Image.open(path).convert("RGB"), (150 + c * w, y))
    out = f"{prefix}_{variant}.png"
    image.save(out)
    print(out, image.size)
