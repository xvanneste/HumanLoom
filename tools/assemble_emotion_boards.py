"""Assemble une planche PNG par émotion (Pillow) : python tools/assemble_emotion_boards.py DOSSIER_RENDUS DOSSIER_SORTIE emotion1,emotion2"""
from pathlib import Path
import sys

from PIL import Image, ImageDraw

src, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
morphs = ["neutre", "femme_jeune", "homme_age"]
views = [("face", "face"), ("trois_quarts", "3/4")]
levels = [0, 50, 100]
for emotion in sys.argv[3].split(","):
    first = Image.open(src / f"{emotion}_neutre_face_000.png")
    w, h = first.size
    board = Image.new("RGB", (len(levels) * w + 110, len(morphs) * len(views) * h + 24), "white")
    draw = ImageDraw.Draw(board)
    draw.text((4, 6), emotion, fill="black")
    for c, level in enumerate(levels):
        draw.text((110 + c * w + w // 2 - 15, 6), f"{level} %", fill="black")
    r = 0
    for m in morphs:
        for key, label in views:
            draw.text((4, 24 + r * h + h // 2), f"{m}\n{label}", fill="black")
            for c, level in enumerate(levels):
                board.paste(Image.open(src / f"{emotion}_{m}_{key}_{level:03d}.png").convert("RGB"), (110 + c * w, 24 + r * h))
            r += 1
    board.save(out / f"planche_{emotion}.png")
    print(out / f"planche_{emotion}.png", board.size)
