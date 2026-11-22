"""PROTOTYPE JETABLE de mesure (D-30) : extrait de la tête de Rain v3.4 (CC-BY 4.0, Blender Studio) les nombres nécessaires aux mesures du visage.

Lecture seule : le .blend de Rain est ouvert avec l'exécution de scripts désactivée et n'est jamais enregistré ; la sortie (.npz) va dans un dossier
temporaire de l'utilisateur, jamais dans le dépôt. Ce n'est PAS un lot de production (aucune donnée de Rain n'entre dans l'extension).

  blender --background --factory-startup --offline-mode --disable-autoexec RAIN.blend --python tools/proto_face_extract_rain.py -- SORTIE.npz
"""
import sys

import bpy
import numpy as np

out = sys.argv[sys.argv.index("--") + 1]
arm = bpy.data.objects["RIG-rain"]
head = bpy.data.objects["GEO-rain-head"]
mesh = head.data
world = head.matrix_world
points = np.array([(world @ v.co)[:] for v in mesh.vertices], dtype=np.float64)
mesh.calc_loop_triangles()
triangles = np.array([t.vertices[:] for t in mesh.loop_triangles], dtype=np.int64)
edges = np.array([e.vertices[:] for e in mesh.edges], dtype=np.int64)
polygon_sizes = np.array([len(p.vertices) for p in mesh.polygons], dtype=np.int64)
edge_faces = np.zeros(len(mesh.edges), dtype=np.int64)
lookup = {tuple(sorted(e.vertices)): i for i, e in enumerate(mesh.edges)}
for polygon in mesh.polygons:
    ring = list(polygon.vertices)
    for a, b in zip(ring, ring[1:] + ring[:1]):
        edge_faces[lookup[tuple(sorted((a, b)))]] += 1

names = [g.name for g in head.vertex_groups]
vi, gi, wt = [], [], []
for v in mesh.vertices:
    for group in v.groups:
        if group.weight > 1e-6:
            vi.append(v.index)
            gi.append(group.group)
            wt.append(group.weight)

eyes = bpy.data.objects["GEO-rain-eyes"]
eye_points = np.array([(eyes.matrix_world @ v.co)[:] for v in eyes.data.vertices], dtype=np.float64)

face_bones = [b for b in arm.data.bones if any(c.name.startswith("Face") for c in b.collections)]
head_bone = arm.data.bones["DEF-Head"]
np.savez_compressed(
    out, points=points, triangles=triangles, edges=edges, edge_faces=edge_faces, polygon_sizes=polygon_sizes,
    group_names=np.array(names), vi=np.array(vi), gi=np.array(gi), wt=np.array(wt), eye_points=eye_points,
    bone_names=np.array([b.name for b in face_bones]), bone_head=np.array([(arm.matrix_world @ b.head_local)[:] for b in face_bones]),
    bone_tail=np.array([(arm.matrix_world @ b.tail_local)[:] for b in face_bones]), bone_deform=np.array([b.use_deform for b in face_bones]),
    head_bone=np.array((arm.matrix_world @ head_bone.head_local)[:]),
)
print("EXTRACT_OK", len(points), len(face_bones), len(vi))
