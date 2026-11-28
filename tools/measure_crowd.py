"""Mesure de performance de la foule (lots C1/C2) pour un effectif donné, dans un processus Blender isolé (la mémoire n'est mesurée que si le processus est neuf).

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/measure_crowd.py -- --n 50 [--out FICHIER.json] [--frames 120]

Écrit un JSON : temps de génération (s), mémoire du processus (Mo) avant/après, taille du .blend (Mo), temps d'évaluation moyen par image (ms) sans puis avec niveaux de détail automatiques, triangles évalués.
La caméra est placée à 30 m du centre de l'aire (12 m de demi-côté). Aucune donnée tierce ; clips synthétiques."""
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import sys
import tempfile
import time

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import crowd  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:]
N = int(ARGS[ARGS.index("--n") + 1])
OUT = ARGS[ARGS.index("--out") + 1] if "--out" in ARGS else None
OUTFIT = "--outfit" in ARGS and ARGS[ARGS.index("--outfit") + 1] == "1"  # vêtements dans la foule (variante « outfit » : t-shirt + jean, avec chaussures ou robe)
FRAMES = int(ARGS[ARGS.index("--frames") + 1]) if "--frames" in ARGS else 120


def memory_mb():
    """Mémoire résidente du processus (Mo) : API Windows (psapi), sans dépendance."""
    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
    counters = Counters()
    counters.cb = ctypes.sizeof(Counters)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.K32GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    kernel.K32GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb)
    return counters.WorkingSetSize / 2 ** 20


def evaluation_ms(scene, frames=(10, 40, 70, 100)):
    times = []
    for f in frames:
        scene.frame_set(f)
        start = time.perf_counter()
        scene.frame_set(f + 1)
        bpy.context.view_layer.update()
        times.append((time.perf_counter() - start) * 1000.0)
    return sum(times) / len(times)


def triangles(scene):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    total = 0
    for body in crowd.members_of(scene):
        evaluated = body.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        mesh.calc_loop_triangles()
        total += len(mesh.loop_triangles)
        evaluated.to_mesh_clear()
    return total


addon.register()
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
scene = bpy.context.scene
memory_before = memory_mb()
spec = crowd.default_spec(N, 12)
spec["frames"] = FRAMES
spec["zones"] = [{"kind": "sidewalk", "rect": [-12.0, 8.0, 12.0, 11.0]}, {"kind": "sidewalk", "rect": [-12.0, -11.0, 12.0, -8.0]}, {"kind": "crossing", "rect": [-1.5, -8.0, 1.5, 8.0]}]
spec["behaviors"] = {"walk": 5.0, "run": 1.0, "wait": 2.0, "chat": 2.0, "jump": 0.3, "cross": 1.5}
if OUTFIT:
    spec["variants"] = {"outfit": [["t_shirt", "jean"], ["t_shirt", "jean", "chaussures"], ["robe_courte"]]}
start = time.perf_counter()
summary = crowd.generate(bpy.context, spec)
generation = time.perf_counter() - start
camera_data = bpy.data.cameras.new("cam")
camera = bpy.data.objects.new("cam", camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
camera.location = (0.0, -30.0, 1.7)
bpy.context.view_layer.update()
memory_after = memory_mb()
row = {"vetements": OUTFIT, "personnages": N, "generation_s": round(generation, 1), "generation_par_personnage_s": round(generation / N, 2), "memoire_avant_mo": round(memory_before), "memoire_apres_mo": round(memory_after),
       "diversite_min": round(summary["diversite"].get("distance_min", 0.0), 3), "comportements": summary["comportements"], "images": FRAMES}
path = Path(tempfile.mkdtemp(prefix="hl_perf_")) / "foule.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(path), compress=True)
row["taille_blend_mo"] = round(path.stat().st_size / 2 ** 20, 1)
row["triangles_sans_lod"] = triangles(scene)
row["evaluation_ms_par_image_sans_lod"] = round(evaluation_ms(scene), 1)
levels = crowd.auto_lod(scene)
row["niveaux_lod"] = {str(k): sum(1 for v in levels.values() if v == k) for k in (0, 1, 2, 3)}
row["triangles_avec_lod"] = triangles(scene)
row["evaluation_ms_par_image_avec_lod"] = round(evaluation_ms(scene), 1)
row["memoire_apres_lod_mo"] = round(memory_mb())
print("PERF", json.dumps(row, ensure_ascii=False))
if OUT:
    Path(OUT).write_text(json.dumps(row, indent=1, ensure_ascii=False), encoding="utf-8")
