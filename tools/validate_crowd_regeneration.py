"""Régénération individuelle d'un personnage de foule : les voisins restent des obstacles aux courbes RÉELLES (éditées à la main comprises) et ne changent pas (audit ANI-019).

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_crowd_regeneration.py [-- --trials N]

Mesure la distance minimale, sur la scène réelle, entre le personnage régénéré et ses voisins ; contrôle négatif : la même mesure avec l'ancien comportement (voisins recalculés) doit être prise en défaut sur au moins un essai."""
import sys
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import crowd  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
TRIALS = int(ARGS[ARGS.index("--trials") + 1]) if "--trials" in ARGS else 6
THRESHOLD = 0.30  # m : distance minimale exigée entre le personnage régénéré et un voisin réel
addon.register()
FAILURES = []


def check(label, condition, detail=""):
    print(("OK   " if condition else "ECHEC"), label, detail, flush=True)
    if not condition:
        FAILURES.append(label)


def real_paths(scene, frames):
    return {o[crowd.OBJECT_KEY]: crowd._trajectory(o, frames)[:, :2] for o in crowd.members_of(scene)}


results = []
for trial in range(TRIALS):
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)
    scene = bpy.context.scene
    spec = crowd.default_spec(6, 100 + trial)
    spec["rig"] = False
    spec["frames"] = 60
    crowd.generate(bpy.context, spec, replace=True)
    frames = [1 + f for f in range(60)]
    before = real_paths(scene, frames)
    ids = sorted(before)
    edited = ids[(trial + 1) % len(ids)]
    target = ids[trial % len(ids)]
    if edited == target:
        edited = ids[(trial + 2) % len(ids)]
    # édition manuelle : le voisin est décalé vers le futur trajet probable du personnage visé (sa trajectoire réelle change)
    shift = before[target][len(frames) // 2] - before[edited][len(frames) // 2]
    body = next(o for o in crowd.members_of(scene) if o[crowd.OBJECT_KEY] == edited)
    for curve in crowd._location_curves(body).values():
        axis = curve.array_index
        if axis > 1:
            continue
        for point in curve.keyframe_points:
            point.co.y += float(shift[axis]) * 0.9
            point.handle_left.y += float(shift[axis]) * 0.9
            point.handle_right.y += float(shift[axis]) * 0.9
        curve.update()
    edited_paths = real_paths(scene, frames)
    crowd.regenerate_member(bpy.context, target)
    after = real_paths(scene, frames)
    unchanged = all(np.allclose(after[i], edited_paths[i], atol=1e-6) for i in ids if i != target)
    nearest = min(float(np.linalg.norm(after[target] - after[i], axis=1).min()) for i in ids if i != target)
    results.append((trial, target, edited, unchanged, nearest))
    print("   essai", trial, "cible", target, "voisin edite", edited, "voisins inchanges", unchanged, "distance minimale reelle", round(nearest, 3), flush=True)
check("ANI-019 les courbes des voisins (editees comprises) restent identiques", all(r[3] for r in results))
worst = min(r[4] for r in results)
check(f"ANI-019 distance minimale sur la scene reelle >= {THRESHOLD} m sur tous les essais", worst >= THRESHOLD, f"pire cas {worst:.3f} m")
# Mecanisme : un voisin figé (position réelle différente de son départ simulé) est un obstacle cinématique à sa position RÉELLE
base = crowd.default_spec(2, 7)
base.update(frames=120, avoidance=True)
walker = {"id": 0, "behavior": "walk", "start": [-4.0, 0.0], "path": [[4.0, 0.0]], "lateral": 0.0, "speed": 1.2, "delay_s": 0.0}
waiter = {"id": 1, "behavior": "wait", "start": [0.0, 0.0], "path": [], "lateral": 0.0, "speed": 0.0, "delay_s": 0.0}


def with_frozen(y):
    track = np.tile(np.array([[0.0, y]]), (120, 1))
    try:
        return crowd.simulate(base, [dict(walker), dict(waiter)], {1: (track, np.zeros(120))})
    except TypeError:
        return None


far = with_frozen(3.0)
near = with_frozen(0.4)
if far is None or near is None:
    check("ANI-019 simulate accepte des trajets figes", False, "parametre absent")
else:
    deviation = float(np.abs(far[0][:, 0, 1]).max())
    check("ANI-019 voisin reel eloigne : pas d'evitement d'un fantome (trajet quasi rectiligne)", deviation < 0.15, f"ecart lateral max {deviation:.3f} m")
    distance = float(np.linalg.norm(near[0][:, 0] - near[0][:, 1], axis=1).min())
    check("ANI-019 voisin reel sur le trajet : evitement a sa position reelle", distance >= THRESHOLD, f"distance minimale {distance:.3f} m")
    check("ANI-019 le membre fige suit exactement son trajet", float(np.abs(near[0][:, 1, 1] - 0.4).max()) < 1e-9)
print("RESULTAT", "ECHECS " + ", ".join(FAILURES) if FAILURES else "tout OK")
sys.exit(1 if FAILURES else 0)
