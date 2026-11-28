"""Mesure de la simulation de tissu (robes) DANS UNE FOULE (lot E) : stabilité, coût par robe et par image, cuisson, taille du cache emballé, nettoyage à l'effacement de la foule.

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/measure_crowd_cloth.py -- --n 6 [--frames 40] [--out FICHIER.json]

Foule de `crowd.generate` dont chaque personnage porte une robe (variante « outfit »), clips de marche synthétiques ; la simulation (solveur XPBD expérimental de Blender 5.2) est activée sur chaque robe.
Écrit : durée d'évaluation moyenne par image (ms) corps seuls puis avec N robes simulées (donc le coût par robe), stabilité (valeurs non finies, pas maximal par image), durée de cuisson par robe, tailles du .blend avec et sans cache
cuit, résidus après `crowd.clear` (objets, collections « HL Colliders »). Valeurs propres à CETTE machine. Aucune donnée tierce."""
import json
from pathlib import Path
import sys
import tempfile
import time

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import cloth_sim, crowd, garments  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:]
N = int(ARGS[ARGS.index("--n") + 1])
FRAMES = int(ARGS[ARGS.index("--frames") + 1]) if "--frames" in ARGS else 40
OUT = ARGS[ARGS.index("--out") + 1] if "--out" in ARGS else None

addon.register()
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
scene = bpy.context.scene
spec = crowd.default_spec(N, 5)
spec["frames"] = FRAMES
spec["variants"] = {"outfit": [["robe_mi_longue"], ["robe_courte"], ["robe_longue"]]}
t0 = time.perf_counter()
crowd.generate(bpy.context, spec)
generation = time.perf_counter() - t0
scene.frame_start, scene.frame_end = 1, FRAMES
bodies = crowd.members_of(scene)
dresses = [g for b in bodies for g in garments.garments_of(b) if "Epinglage" in g.vertex_groups]


def evaluation_ms(frames=range(4, 24, 4)):
    times = []
    for f in frames:
        scene.frame_set(f)
        started = time.perf_counter()
        scene.frame_set(f + 1)
        bpy.context.view_layer.update()
        times.append((time.perf_counter() - started) * 1000.0)
    return float(np.median(times))


def run_pass():
    """Positions des robes RELATIVES à l'origine de leur personnage (le déplacement d'ensemble de la marche est retiré), une ligne par image ; durées par image (ms)."""
    scene.frame_set(1)
    bpy.context.view_layer.update()
    rows, durations = [], []
    for f in range(1, FRAMES + 1):
        started = time.perf_counter()
        scene.frame_set(f)
        bpy.context.view_layer.update()
        rows.append([cloth_sim.positions(d) - np.array(d.parent.matrix_world.translation[:]) for d in dresses])
        durations.append((time.perf_counter() - started) * 1000.0)
    return [np.array([r[i] for r in rows]) for i in range(len(dresses))], durations


without = evaluation_ms()
control, _ = run_pass()  # référence : les robes suivent seulement l'armature (sans simulation)
control_steps = max(float(np.linalg.norm(np.diff(a, axis=0), axis=-1).max()) for a in control)
enabled = 0
start = time.perf_counter()
errors = []
for dress in dresses:
    try:
        cloth_sim.enable(dress)
        enabled += 1
    except Exception as error:  # noqa: BLE001 : on veut la liste des échecs, pas un arrêt
        errors.append(str(error)[:120])
enable_s = time.perf_counter() - start
arrays, times = run_pass()
steps = [np.linalg.norm(np.diff(a, axis=0), axis=-1) for a in arrays]
row = {"personnages": N, "robes": len(dresses), "robes_activees": enabled, "echecs_activation": errors[:3], "generation_s": round(generation, 1), "activation_s": round(enable_s, 1),
       "evaluation_ms_sans_tissu": round(without, 1), "evaluation_ms_par_image_avec_tissu_mediane": round(float(np.median(times[1:])), 1),
       "cout_par_robe_et_par_image_ms": round((float(np.median(times[1:])) - without) / max(len(dresses), 1), 1),
       "stabilite": {"valeurs_non_finies": bool(any(not np.isfinite(a).all() for a in arrays)), "pas_max_relatif_par_image_m": round(float(max(s.max() for s in steps)), 3),
                     "pas_max_relatif_sans_simulation_m": round(control_steps, 3), "robes_avec_pas_relatif_sup_0_3_m": int(sum(1 for s in steps if s.max() > 0.3))}}
directory = Path(tempfile.mkdtemp(prefix="hl_crowd_cloth_"))
bpy.ops.wm.save_as_mainfile(filepath=str(directory / "avant_cuisson.blend"), compress=True)
row["blend_avant_cuisson_mo"] = round((directory / "avant_cuisson.blend").stat().st_size / 2 ** 20, 1)
bake_times = []
for dress in dresses:
    result = cloth_sim.bake(dress, 1, FRAMES)
    bake_times.append(result["duree_s"])
bpy.ops.wm.save_as_mainfile(filepath=str(directory / "apres_cuisson.blend"), compress=True)
row["blend_apres_cuisson_mo"] = round((directory / "apres_cuisson.blend").stat().st_size / 2 ** 20, 1)
row["cuisson_par_robe_s"] = {"moyenne": round(float(np.mean(bake_times)), 2), "max": round(float(max(bake_times)), 2), "images": FRAMES}
row["cache_cuit_par_robe_mo"] = round((row["blend_apres_cuisson_mo"] - row["blend_avant_cuisson_mo"]) / max(len(dresses), 1), 2)
row["evaluation_ms_par_image_avec_cache_cuit"] = round(evaluation_ms(), 1)
objects_before_clear = len(bpy.data.objects)
try:
    crowd.clear(scene)
    refusal = None
except ValueError as error:
    refusal = str(error)[:160]
for dress in dresses:
    cloth_sim.disable(dress)
try:
    crowd.clear(scene)
    clear_error = None
except Exception as error:  # noqa: BLE001
    clear_error = f"{type(error).__name__}: {str(error)[:140]}"
leftovers = {"objets": len(bpy.data.objects), "collections_colliders": sum(1 for c in bpy.data.collections if c.name.startswith(cloth_sim.COLLECTION)), "robes": sum(1 for o in bpy.data.objects if o.get(garments.MARKER))}
row["effacement"] = {"refus_avec_tissu_actif": refusal, "erreur_apres_desactivation": clear_error, "objets_avant": objects_before_clear, "residus_apres_desactivation": leftovers}
print("TISSU", json.dumps(row, ensure_ascii=False))
if OUT:
    Path(OUT).write_text(json.dumps(row, indent=1, ensure_ascii=False), encoding="utf-8")
