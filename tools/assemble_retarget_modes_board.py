"""Assemble la planche avant/après du retargeting (Pillow) : python tools/assemble_retarget_modes_board.py DOSSIER_RENDUS SORTIE.png"""
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw

src, out = Path(sys.argv[1]), Path(sys.argv[2])
actions = json.loads((src / "actions.json").read_text(encoding="utf-8"))
first = Image.open(next(src.glob("*_0.png")))
w, h = first.size
modes = [("bras_jambes", "ancien : IK bras + jambes"), ("jambes", "nouveau : IK des jambes seules")]
board = Image.new("RGB", (3 * w + 200, len(actions) * len(modes) * h + 24), "white")
draw = ImageDraw.Draw(board)
for c, text in enumerate(("25 %", "50 %", "75 %")):
    draw.text((200 + c * w + w // 2 - 15, 6), text, fill="black")
r = 0
for label in actions:
    for mode, mode_text in modes:
        draw.text((4, 24 + r * h + h // 2 - 10), f"{label}\n{mode_text}", fill="black")
        for k in range(3):
            board.paste(Image.open(src / f"{label}_{mode}_{k}.png").convert("RGB"), (200 + k * w, 24 + r * h))
        r += 1
board.save(out)
print(out, board.size)
