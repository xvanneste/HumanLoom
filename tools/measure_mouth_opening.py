"""Mesures de l'ouverture de la bouche (lot F0) : largeur de bouche (commissure à commissure), hauteur et rapport hauteur/largeur de l'orifice, exposition des incisives hautes par rapport au bord
de la lèvre supérieure, courbure de la coupe de profil, à 0 / 10 / 20 / 30° et sur 3 morphologies.

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/measure_mouth_opening.py -- [--out FICHIER.json]

Mesures de NOTRE modèle (aucune valeur publiée n'est comparée ici : aucune n'a été lue). `exposition` > 0 : le bord incisif dépasse SOUS le bord de la lèvre haute (dent visible) ;
`angle_vif_profil` : plus grand changement de direction (degrés) entre deux segments consécutifs de la coupe médiane du menton et de la lèvre inférieure."""
import json
import math
from pathlib import Path
import sys

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import human  # noqa: E402
from extension.animation import dental, skeleton  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = ARGS[ARGS.index("--out") + 1] if "--out" in ARGS else None
addon.register()
MORPHOLOGIES = {"neutre": {}, "homme_age": {"sex": 0.0, "age": 3.0}, "femme_jeune": {"sex": 1.0, "age": 1.0}}
data = np.load(skeleton.JAW_FILE, allow_pickle=False)
upper_ids, lower_ids = data["slit_upper"], data["slit_lower"]


def cage(body):
    saved = [(m, m.show_viewport) for m in body.modifiers]
    for m in body.modifiers:
        m.show_viewport = m.name in (human.MODIFIER_NAME, skeleton.MODIFIER_NAME)
    human.touch(body)
    bpy.context.view_layer.update()
    evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    points = np.array([v.co[:] for v in mesh.vertices])
    evaluated.to_mesh_clear()
    for m, state in saved:
        m.show_viewport = state
    return points


rows = {}
for label, values in MORPHOLOGIES.items():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.humanloom.create()
    body = bpy.context.object
    for name, value in values.items():
        human.set_value(body, name, value)
    rig = skeleton.install(body)
    pose = rig.pose.bones[skeleton.JAW]
    pose.rotation_mode = "XYZ"
    rest = cage(body)
    sign = None
    result = {}
    for angle in (0, 10, 20, 30):
        if sign is None:
            best = None
            for s in (1.0, -1.0):
                pose.rotation_euler = (s * math.radians(20), 0, 0)
                z = cage(body)[skeleton.JAW_CHIN, 2]
                best = (z, s) if best is None or z < best[0] else best
            sign = best[1]
        pose.rotation_euler = (sign * math.radians(angle), 0, 0)
        points = cage(body)
        corners_x = [np.abs(points[np.concatenate([upper_ids, lower_ids]), 0]).max()]
        upper_z = points[upper_ids, 2]
        lower_z = points[lower_ids, 2]
        centre = np.argmin(np.abs(points[upper_ids, 0]))
        height = float(points[upper_ids[centre], 2] - points[lower_ids[np.argmin(np.abs(points[lower_ids, 0]))], 2]) * 1000
        width = float(2 * corners_x[0]) * 1000
        upper_edge = float(points[upper_ids[centre], 2])
        bpy.context.view_layer.update()
        incisor = next(o for o in dental.parts_of(body) if o.name == "HL Dents hautes")
        teeth_z = np.array([(incisor.matrix_world @ v.co).z for v in incisor.data.vertices[:164 - 2]])  # incisive centrale (côté +x)
        exposure = (upper_edge - float(teeth_z.min())) * 1000
        # courbure : coupe médiane de la lèvre basse au menton (sommets |x| < 1,5 mm, z sous la fente, y avant)
        median = np.where((np.abs(points[:, 0]) < 0.0015) & (points[:, 2] < upper_edge) & (points[:, 2] > points[skeleton.JAW_CHIN, 2] - 0.02) & (points[:, 1] < points[upper_ids[centre], 1] - 0.002))[0]  # peau extérieure seulement (devant la fente)
        order = median[np.argsort(-points[median, 2])]
        path = points[order][:, 1:3]
        steps = np.diff(path, axis=0)
        steps = steps[np.linalg.norm(steps, axis=1) > 1e-4]
        turns = [math.degrees(math.acos(np.clip(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)), -1, 1))) for a, b in zip(steps[:-1], steps[1:])]
        result[angle] = {"largeur_bouche_mm": round(width, 2), "hauteur_orifice_mm": round(height, 2), "hauteur_sur_largeur": round(height / width, 3) if width else None,
                         "exposition_incisives_mm": round(exposure, 2), "angle_vif_profil_deg": round(max(turns), 1) if turns else None}
    pose.rotation_euler = (0, 0, 0)
    rows[label] = result
    for angle, r in result.items():
        print("MESURE", label, f"{angle}°", r)
if OUT:
    Path(OUT).write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
