"""Cycle de vie des tâches d'animation (audit ANI-023) : changement de fichier ou désactivation de l'extension pendant un import ou des vignettes : aucun minuteur orphelin, aucune exception de rappel, message explicite.

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_animation_lifecycle.py"""
import sys
import tempfile
import threading
import time
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension.animation import ui  # noqa: E402

addon.register()
FAILURES = []


def check(label, condition, detail=""):
    print(("OK   " if condition else "ECHEC"), label, detail, flush=True)
    if not condition:
        FAILURES.append(label)


def start_fake_import(duration=1.5):
    release = threading.Event()
    thread = threading.Thread(target=lambda: release.wait(duration), daemon=True)
    thread.start()
    ui._state["thread"] = thread
    ui._state["import_result"] = {}
    ui._state["import_message"] = "Import en cours…"
    bpy.app.timers.register(ui.poll_import, first_interval=0.5)
    return release


release = start_fake_import()
check("ANI-023 depart : minuteur d'import actif", bpy.app.timers.is_registered(ui.poll_import))
path = str(Path(tempfile.mkdtemp(prefix="hl_life_")) / "autre.blend")
bpy.ops.wm.save_as_mainfile(filepath=path)
bpy.ops.wm.open_mainfile(filepath=path)  # load_pre se déclenche
check("ANI-023 changement de fichier : minuteur d'import retire", not bpy.app.timers.is_registered(ui.poll_import))
check("ANI-023 changement de fichier : etat d'import remis a zero avec message", ui._state["thread"] is None and "interrompu" in ui._state["import_message"].lower(), ui._state["import_message"])
release.set()
time.sleep(0.2)
check("ANI-023 fin tardive du fil : aucune exception, aucun minuteur recree", not bpy.app.timers.is_registered(ui.poll_import))
release = start_fake_import()
addon.unregister()
check("ANI-023 desactivation : minuteur d'import retire", not bpy.app.timers.is_registered(ui.poll_import))
check("ANI-023 desactivation : aucun minuteur de vignettes", not bpy.app.timers.is_registered(ui._poll_thumbnail_revision))
release.set()
print("RESULTAT", "ECHECS " + ", ".join(FAILURES) if FAILURES else "tout OK")
sys.exit(1 if FAILURES else 0)
