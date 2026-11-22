"""Écrit `extension/data/human_sockets.json` depuis le groupe « HL Human » de `extension/data/human_nodes.blend`.

À relancer après chaque régénération du groupe (`build_human_nodes.py`). `validate_human_nodes.py` vérifie que le JSON
correspond au groupe. Raison : `human.sockets()` est appelé à l'enregistrement de l'extension, où `bpy.data` est restreint
(on ne peut pas y ouvrir de .blend) ; le JSON évite aussi de lire 18 Mo à chaque démarrage de Blender.

Usage : blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/build_human_sockets.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from extension import human

found = human.read_sockets_from_group()
human.SOCKETS_PATH.write_text(json.dumps({name: list(values) for name, values in found.items()}, ensure_ascii=False, indent=1), encoding="utf-8")
print("HUMAN_SOCKETS", len(found), human.SOCKETS_PATH)
