"""Carte des plis NOUVEAUX sur une pose d'épaule (rouge = sommet d'un triangle replié par rapport au repos), vues de 3/4 avant, arrière et dessus : où sont les défauts de la peau linéaire ?

  blender --background --factory-startup --offline-mode --python-exit-code 0 --python tools/render_fold_map.py -- DOSSIER [--elev 80] [--clav 35] [--plane frontal|sagittal]"""
import math
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import proto_shoulder_correctives as P  # noqa: E402
import rig_metrics as M  # noqa: E402

ARGS = P.ARGS
ELEV = float(ARGS[ARGS.index("--elev") + 1]) if "--elev" in ARGS else 80.0
CLAV = float(ARGS[ARGS.index("--clav") + 1]) if "--clav" in ARGS else 35.0
PLANE = ARGS[ARGS.index("--plane") + 1] if "--plane" in ARGS else "frontal"
scene = P.Scene("defaut")
arm, cl = "arm_upper.L", "clavicle.L"


def tail(n):
    return np.array((scene.rig.matrix_world @ scene.rig.pose.bones[n].tail)[:])


def sign(b, axis, metric):
    sc = {}
    for s in (1.0, -1.0):
        scene.pose({b: P.rot(axis, 40 * s)})
        sc[s] = metric()
    scene.pose({})
    return 1.0 if sc[1.0] <= sc[-1.0] else -1.0


sg = sign(arm, 0, lambda: float(tail(arm)[1]))
fr = sign(arm, 2, lambda: -float(tail(arm)[2]))
cv = {}
for axis in (0, 2):
    for s in (1.0, -1.0):
        scene.pose({cl: P.rot(axis, 20 * s)})
        cv[(axis, s)] = float(np.array((scene.rig.matrix_world @ scene.rig.pose.bones[arm].head)[:])[2])
scene.pose({})
cax, csg = max(cv, key=cv.get)
pose = {arm: P.rot(2, fr * ELEV) if PLANE == "frontal" else P.rot(0, sg * ELEV), cl: P.rot(cax, csg * CLAV)}
if "--pose" in ARGS:  # pose réelle sauvegardée par measure_library_shoulder.py
    data = np.load(ARGS[ARGS.index("--pose") + 1], allow_pickle=False)
    for b in scene.rig.pose.bones:
        b.rotation_mode = "QUATERNION"
    for i, nme in enumerate(data["names"]):
        pb = scene.rig.pose.bones[str(nme)]
        pb.rotation_quaternion = tuple(data["quat"][i])
        pb.location = tuple(data["loc"][i])
    bpy.context.view_layer.update()
    PLANE, ELEV, CLAV = "reelle", 0, 0
else:
    scene.pose(pose)
pts = P.evaluate_cage(scene.body)
tris = scene.tris
pm = {}
for t, tri in enumerate(tris):
    for k in range(3):
        pm.setdefault((min(tri[k], tri[(k + 1) % 3]), max(tri[k], tri[(k + 1) % 3])), []).append(t)
pairs = np.array([v for v in pm.values() if len(v) == 2])
rn, _ = M.tri_normals(scene.rest, tris)
pn, _ = M.tri_normals(pts, tris)
rest_d = np.einsum("ij,ij->i", rn[pairs[:, 0]], rn[pairs[:, 1]])
pose_d = np.einsum("ij,ij->i", pn[pairs[:, 0]], pn[pairs[:, 1]])
folded = np.unique(pairs[(pose_d < 0) & (rest_d >= 0)].ravel())
bad_vertices = np.unique(tris[folded].ravel())
print("plis nouveaux (triangles)", len(folded), "sommets", len(bad_vertices))
mesh = bpy.data.meshes.new("fold")
mesh.from_pydata([tuple(p) for p in pts], [], [tuple(p.vertices) for p in scene.body.data.polygons])
colors = np.tile([0.78, 0.66, 0.58, 1.0], (len(pts), 1))
colors[bad_vertices] = [0.9, 0.05, 0.05, 1.0]
attr = mesh.color_attributes.new("c", "FLOAT_COLOR", "POINT")
attr.data.foreach_set("color", colors.ravel())
obj = bpy.data.objects.new("fold", mesh)
bpy.context.scene.collection.objects.link(obj)
for o in bpy.data.objects:
    if o.type in ("MESH", "ARMATURE") and o is not obj:
        o.hide_render = True
sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sc.render.resolution_x = sc.render.resolution_y = 360
sc.display.shading.light = "STUDIO"
sc.display.shading.color_type = "VERTEX"
sc.world = sc.world or bpy.data.worlds.new("w")
sc.world.color = (1, 1, 1)
cam_data = bpy.data.cameras.new("cam")
cam_data.type = "ORTHO"
cam_data.ortho_scale = 0.9
cam = bpy.data.objects.new("cam", cam_data)
sc.collection.objects.link(cam)
sc.camera = cam
centre = np.array((scene.rig.matrix_world @ scene.rig.pose.bones[arm].head)[:]) + np.array([0.0, 0.0, 0.05])
OUT = P.OUT
OUT.mkdir(parents=True, exist_ok=True)
for name, direction in (("avant34", (0.7, -0.7, 0.2)), ("arriere34", (0.7, 0.7, 0.2)), ("dessus", (0.1, -0.1, 1.0))):
    d = Vector(direction).normalized()
    cam.location = Vector(centre) + d * 3.0
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = str(OUT / f"plis_{PLANE}_{int(ELEV)}_{int(CLAV)}_{name}.png")
    bpy.ops.render.render(write_still=True)
