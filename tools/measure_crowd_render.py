"""Mesure du temps de rendu de la foule (Eevee et Cycles) pour dimensionner le court-métrage, dans un processus Blender isolé.

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/measure_crowd_render.py -- --n 50 [--out FICHIER.json] [--engines eevee,cycles] [--sizes 1080,2160] [--cycles-samples 32]

Pour chaque moteur et chaque hauteur d'image (1080 = 1920×1080, 2160 = 3840×2160) : durée d'un rendu (s) à la 1re image (compilation des shaders, construction BVH comprise) puis à la 2e image du même processus, et mémoire du processus
(Mo, pic). Scène : foule de `crowd.generate` (vêtements non appliqués), sol, soleil, caméra à ~20 m, objectif 50 mm. Cycles : CPU de cette machine, échantillons réduits (débruitage désactivé : mesure du coût brut) ; Eevee : GPU de cette machine.
Valeurs propres à CETTE machine ; elles servent d'ordre de grandeur pour dimensionner le court-métrage."""
import ctypes
import subprocess
import threading
from ctypes import wintypes
import json
from pathlib import Path
import sys
import time

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import crowd  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:]
N = int(ARGS[ARGS.index("--n") + 1])
OUT = ARGS[ARGS.index("--out") + 1] if "--out" in ARGS else None
ENGINES = (ARGS[ARGS.index("--engines") + 1] if "--engines" in ARGS else "eevee,cycles").split(",")
SIZES = [int(v) for v in (ARGS[ARGS.index("--sizes") + 1] if "--sizes" in ARGS else "1080,2160").split(",")]
LOD = "--lod" in ARGS and ARGS[ARGS.index("--lod") + 1] == "1"  # niveaux de détail selon la distance à la caméra (crowd.auto_lod) avant les rendus
CULL = "--cull" in ARGS and ARGS[ARGS.index("--cull") + 1] == "1"  # élimination hors caméra (crowd.cull) à l'image mesurée, après les niveaux de détail
DEVICE = ARGS[ARGS.index("--device") + 1] if "--device" in ARGS else "gpu"  # GPU par défaut ; le CPU n'est qu'un repli documenté
SAMPLES = int(ARGS[ARGS.index("--cycles-samples") + 1]) if "--cycles-samples" in ARGS else 32


def vram_used_mb():
    """VRAM utilisée (Mo) par nvidia-smi (tous processus : la mesure est faite sur une machine au repos)."""
    try:
        return int(subprocess.check_output(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"], text=True).strip().splitlines()[0])
    except Exception:
        return -1


class VramPeak:
    """Pic de VRAM pendant un bloc (échantillonnage 0,5 s)."""

    def __enter__(self):
        self.peak, self.stop = vram_used_mb(), False
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        return self

    def _run(self):
        while not self.stop:
            self.peak = max(self.peak, vram_used_mb())
            time.sleep(0.5)

    def __exit__(self, *exc):
        self.stop = True
        self.thread.join()


def enable_gpu():
    """Active le GPU Cycles de façon explicite (OptiX si disponible, sinon CUDA), désactive le CPU, journalise les périphériques ; échoue bruyamment si aucun GPU n'est trouvé."""
    preferences = bpy.context.preferences.addons["cycles"].preferences
    chosen = None
    for kind in ("OPTIX", "CUDA"):
        try:
            preferences.compute_device_type = kind
        except TypeError:
            continue
        preferences.get_devices()
        gpus = [d for d in preferences.devices if d.type == kind]
        if gpus:
            chosen = (kind, gpus)
            break
    if chosen is None:
        raise RuntimeError("Aucun GPU Cycles (OptiX/CUDA) trouvé : mesure GPU impossible.")
    kind, gpus = chosen
    for device in preferences.devices:
        device.use = device in gpus  # GPU seul : le CPU est décoché
    print("GPU", kind, [d.name for d in gpus], "CPU utilisé :", any(d.use for d in preferences.devices if d.type == "CPU"), flush=True)
    return kind, [d.name for d in gpus]


def memory_mb():
    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
    counters = Counters()
    counters.cb = ctypes.sizeof(Counters)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.K32GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    kernel.K32GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb)
    return counters.WorkingSetSize / 2 ** 20, counters.PeakWorkingSetSize / 2 ** 20


addon.register()
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
scene = bpy.context.scene
spec = crowd.default_spec(N, 12)
spec["frames"] = 60
spec["zones"] = [{"kind": "sidewalk", "rect": [-12.0, 8.0, 12.0, 11.0]}, {"kind": "sidewalk", "rect": [-12.0, -11.0, 12.0, -8.0]}, {"kind": "crossing", "rect": [-1.5, -8.0, 1.5, 8.0]}]
spec["behaviors"] = {"walk": 5.0, "run": 1.0, "wait": 2.0, "chat": 2.0, "jump": 0.3, "cross": 1.5}
t0 = time.perf_counter()
crowd.generate(bpy.context, spec)
generation = time.perf_counter() - t0
# sol, soleil, caméra
bpy.ops.mesh.primitive_plane_add(size=80.0, location=(0.0, 0.0, 0.0))
ground = bpy.context.object
ground.name = "sol_mesure"
light_data = bpy.data.lights.new("soleil", "SUN")
light_data.energy = 3.0
light = bpy.data.objects.new("soleil", light_data)
light.rotation_euler = (0.9, 0.3, 0.6)
scene.collection.objects.link(light)
camera_data = bpy.data.cameras.new("cam")
camera_data.lens = 50.0
camera = bpy.data.objects.new("cam", camera_data)
camera.location = (0.0, -22.0, 1.7)
camera.rotation_euler = (1.5708, 0.0, 0.0)
scene.collection.objects.link(camera)
scene.camera = camera
scene.frame_set(30)
bpy.context.view_layer.update()
rows = {"personnages": N, "generation_s": round(generation, 1)}
if LOD:
    levels = crowd.auto_lod(scene)
    rows["niveaux_lod"] = {str(k): sum(1 for v in levels.values() if v == k) for k in (0, 1, 2, 3)}
    bpy.context.view_layer.update()
    print("LOD", rows["niveaux_lod"], flush=True)
if CULL:
    summary = crowd.cull(scene, frame_range=(30, 30))
    rows["cull"] = {k: v for k, v in summary.items() if k != "jamais_visibles"}
    rows["cull"]["jamais_visibles"] = len(summary["jamais_visibles"])
    bpy.context.view_layer.update()
    print("CULL", json.dumps(rows["cull"], ensure_ascii=False), flush=True)
for engine in ENGINES:
    scene.render.engine = {"eevee": "BLENDER_EEVEE", "cycles": "CYCLES"}[engine]
    if engine == "cycles":
        rows["gpu"] = enable_gpu() if DEVICE == "gpu" else "CPU"
        scene.cycles.device = "GPU" if DEVICE == "gpu" else "CPU"
        scene.cycles.samples = SAMPLES
        scene.cycles.use_denoising = False
    for height in SIZES:
        scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = height * 16 // 9, height, 100
        times = []
        for k in range(2):
            t = time.perf_counter()
            try:
                with VramPeak() as vram:
                    bpy.ops.render.render(write_still=False)
                times.append(round(time.perf_counter() - t, 1))
            except Exception as error:  # moteur indisponible en arrière-plan sur cette machine
                times.append(f"ÉCHEC: {error}")
                break
        now, peak = memory_mb()
        rows[f"{engine}_{height}"] = {"1re_image_s": times[0], "2e_image_s": times[1] if len(times) > 1 else None, "memoire_mo": round(now), "pic_mo": round(peak), "vram_pic_mo": vram.peak}
        print("RENDU", N, engine, height, json.dumps(rows[f"{engine}_{height}"], ensure_ascii=False), flush=True)
if OUT:
    Path(OUT).write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
