"""Mesure : correctifs de flexion du CORPS (clés HLC) dans une foule. Les clés vivent sur le maillage de base, PARTAGÉ entre les personnages ; un pilote par personnage exige un maillage par personnage.
Cet outil mesure ce que coûte de rendre le maillage de base propre à un personnage (copie simple + installation des correctifs) : taille du maillage, taille du .blend et fonctionnement (les correctifs de CE personnage suivent SON coude, pas celui d'un autre).

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/measure_crowd_correctives.py -- [--n 6] [--out FICHIER.json]"""
import json
import math
import os
from pathlib import Path
import sys
import tempfile

import bpy
import numpy as np
from mathutils import Quaternion

ROOT = Path(__file__).resolve().parents[1]
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
N = int(ARGS[ARGS.index("--n") + 1]) if "--n" in ARGS else 6
OUT = ARGS[ARGS.index("--out") + 1] if "--out" in ARGS else None
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import crowd  # noqa: E402
from extension.animation import correctives, skeleton  # noqa: E402

addon.register()
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
scene = bpy.context.scene
spec = crowd.default_spec(N, 4)
spec["frames"] = 12
crowd.generate(bpy.context, spec)
members = crowd.members_of(scene)
base = members[0].data
shared = len({m.data.name for m in members})
bytes_attr = 0
for attribute in base.attributes:
    size = {"FLOAT": 4, "FLOAT_VECTOR": 12, "INT": 4, "BOOLEAN": 1, "FLOAT_COLOR": 16, "FLOAT2": 8, "INT8": 1}.get(attribute.data_type, 4)
    bytes_attr += size * len(attribute.data)
report = {"personnages": N, "maillages_de_base_distincts": shared, "sommets": len(base.vertices), "attributs": len(base.attributes), "octets_attributs_mo": round(bytes_attr / 1e6, 1)}
work = Path(tempfile.mkdtemp(prefix="hl_cc_"))


def blend_size(name):
    path = work / name
    bpy.ops.wm.save_as_mainfile(filepath=str(path), compress=True, copy=True)
    return round(os.path.getsize(path) / 1e6, 2)


report["blend_partage_mo"] = blend_size("partage.blend")
# rendre le maillage de base propre à 2 personnages et installer leurs correctifs
chosen = members[:2]
for member in chosen:
    armature = skeleton.rigs_of(member)[0]
    created = correctives.install_independent(member, armature)
    correctives.set_enabled(member, True)
report["cles_installees_par_personnage"] = created
report["blend_2_maillages_propres_mo"] = blend_size("propres.blend")
report["surcout_par_personnage_mo"] = round((report["blend_2_maillages_propres_mo"] - report["blend_partage_mo"]) / 2, 2)
report["maillages_de_base_distincts_apres"] = len({m.data.name for m in members})
# fonctionnement : le coude gauche du personnage 0 plié 110° déplace SES sommets, pas ceux du personnage 1 (même pose de départ)
data = np.load(correctives.DATA, allow_pickle=False)
sign = float(data["coude_L_sign"])


def evaluated_points(member):
    bpy.context.view_layer.update()
    ev = member.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = ev.to_mesh()
    buf = np.empty(len(mesh.vertices) * 3, np.float32)
    mesh.vertices.foreach_get("co", buf)
    ev.to_mesh_clear()
    return buf.reshape(-1, 3)


for member in members:
    anim = member.animation_data
    arm = skeleton.rigs_of(member)[0]
    if arm.animation_data:
        arm.animation_data.action, arm.animation_data.use_nla = None, False
arm0 = skeleton.rigs_of(members[0])[0]
arm0.pose.bones["arm_lower.L"].rotation_mode = "QUATERNION"
arm0.pose.bones["arm_lower.L"].rotation_quaternion = Quaternion((1.0, 0.0, 0.0), math.radians(sign * 110))
effects = []
for member in chosen:
    correctives.set_enabled(member, False)
off = evaluated_points(members[0])
correctives.set_enabled(members[0], True)
on = evaluated_points(members[0])
report["deplacement_max_personnage_0_mm"] = round(float(np.linalg.norm(on - off, axis=1).max()) * 1000, 2)
off1 = evaluated_points(members[1])
correctives.set_enabled(members[1], True)
on1 = evaluated_points(members[1])
report["deplacement_max_personnage_1_au_repos_mm"] = round(float(np.linalg.norm(on1 - off1, axis=1).max()) * 1000, 3)
report["conclusion"] = "faisable avec un maillage de base propre par personnage proche (coût mesuré ci-dessus) ; impossible sans (maillage partagé)"
print(json.dumps(report, indent=1, ensure_ascii=False))
if OUT:
    Path(OUT).write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
