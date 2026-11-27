"""Sonde : lance un test de la bibliothèque en ignorant les actions que le lecteur STRICT (ANI-002) refuse (échelle non unitaire…) au lieu de planter — usage : --python tools/probe_library_lenient.py -- NOM_DU_TEST --library DOSSIER"""
import runpy
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from extension.animation import retarget, retarget_bpy  # noqa: E402

original = retarget_bpy.read_action


def lenient(action, source, *args, **kwargs):
    try:
        return original(action, source, *args, **kwargs)
    except ValueError as error:
        print("ACTION IGNOREE (lecteur strict) :", action.name, str(error)[:70], flush=True)
        n = len(source.names)
        return retarget.Motion(np.zeros((0, n, 3)), np.zeros((0, n, 4)), 30.0), 1


retarget_bpy.read_action = lenient
after = sys.argv[sys.argv.index("--") + 1:]
sys.argv = [sys.argv[0], "--"] + after[1:]
runpy.run_path(str(ROOT / "tools" / f"{after[0]}.py"), run_name="__main__")
