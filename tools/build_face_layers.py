"""Ajoute au groupe de nœuds « HL Human » des COUCHES DE VISAGE pilotées par de nouvelles entrées (premier client : le correctif d'ouverture de bouche `mouth_open`).

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/build_face_layers.py -- <human_nodes_entree.blend> <human_nodes_sortie.blend> <human_sockets_sortie.json> [--report r.json]

Fonctionnement : l'entrée est une COPIE ; le groupe reçoit une entrée flottante par commande (défaut 0, 0 à 1) et, pour chacune, une couche de sommets (attribut `b_f<n>`, supprimé en sortie par le motif `b*`)
ajoutée au décalage total juste avant `Set Position`. Les couches sont calculées ici, sur la cage du corps par défaut, par des règles géométriques qui sont les NÔTRES (aucun visage tiers).

`mouth_open` (0 = fermée, 1 = ouverte à 30°) : correctif ajouté AVANT le rig (la couche est exprimée dans le repère de repos : l'armature la fait tourner avec la mâchoire). Calculé ainsi :
1. cage ouverte à 30° (déformation linéaire par la mâchoire seule, mêmes poids que le rig) ;
2. CONVERGENCE des commissures : les coins et la peau voisine se rapprochent de la ligne médiane (4 % de la largeur de bouche au total, valeur de modélisation NON VÉRIFIÉE : aucune donnée publiée lue) ;
3. LISSAGE (Laplacien) du bord de la lèvre inférieure et du menton ouverts : supprime le « bec » et la marche sous la lèvre (même principe que le dépliage des croisements) ;
4. la différence est ramenée dans le repère de repos (rotation inverse pondérée par le poids de mâchoire).
Une entrée supplémentaire est écrite dans `human_sockets.json` (identifiant de socket lu dans le groupe)."""
import json
import math
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Matrix

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
ARGS = sys.argv[sys.argv.index("--") + 1:]
SOURCE, OUT, SOCKETS_OUT = Path(ARGS[0]).resolve(), Path(ARGS[1]).resolve(), Path(ARGS[2]).resolve()
REPORT = Path(ARGS[ARGS.index("--report") + 1]).resolve() if "--report" in ARGS else None
CONVERGENCE = 0.04  # fraction de la largeur de bouche (somme des deux côtés)
OPEN_DEGREES = 30.0

import extension as addon  # noqa: E402
from extension import human  # noqa: E402
from extension.animation import skeleton  # noqa: E402

addon.register()
bpy.ops.humanloom.create()
body = bpy.context.object
rig = skeleton.install(body)
mesh_body = body.data
points = skeleton.cage_points(body)
count = len(points)
group_jaw = body.vertex_groups[skeleton.JAW]
weight = np.zeros(count)
for vertex in mesh_body.vertices:
    for g in vertex.groups:
        if g.group == group_jaw.index:
            weight[vertex.index] = g.weight
hinge = np.array((body.matrix_world.inverted() @ rig.matrix_world @ rig.data.bones[skeleton.JAW].head_local)[:])
best = None
for sign in (1.0, -1.0):
    rotation = np.array(Matrix.Rotation(sign * math.radians(OPEN_DEGREES), 3, "X"))
    opened = points + weight[:, None] * ((points - hinge) @ rotation.T + hinge - points)
    drop = points[skeleton.JAW_CHIN, 2] - opened[skeleton.JAW_CHIN, 2]
    best = (drop, rotation, opened) if best is None or drop > best[0] else best
_, rotation, opened = best
neighbors = [set() for _ in range(count)]
for e in mesh_body.edges:
    a, b = e.vertices
    neighbors[a].add(b)
    neighbors[b].add(a)
slit = np.load(skeleton.JAW_FILE)
upper, lower = slit["slit_upper"], slit["slit_lower"]
slit_vertices = np.concatenate([upper, lower])
corner_x = float(np.abs(points[slit_vertices, 0]).max())
mouth_width = 2 * corner_x
slit_y = float(points[slit_vertices, 1].mean())
slit_z = float(points[slit_vertices, 2].mean())


def smooth(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


# 2. convergence des commissures : déplacement en x vers l'axe, gaussienne autour des deux coins, uniquement devant le plan de la fente (lèvres et joues, pas l'intérieur)
corner_ids = [slit_vertices[np.argmax(points[slit_vertices, 0])], slit_vertices[np.argmin(points[slit_vertices, 0])]]
delta = np.zeros((count, 3))
radius = 0.030
front = points[:, 1] < slit_y + 0.012
for corner_id in corner_ids:
    corner = opened[corner_id]  # position du coin bouche ouverte
    distance = np.linalg.norm(opened - corner, axis=1)
    falloff = np.exp(-(distance / radius) ** 2) * front
    delta[:, 0] += -np.sign(points[corner_id, 0]) * CONVERGENCE * mouth_width / 2 * falloff
# 3. lissage du bord de la lèvre inférieure et du menton, bouche ouverte
target = opened + delta
region = [v for v in range(count) if weight[v] > 0.6 and abs(points[v, 0]) < 0.016 and points[v, 1] < slit_y + 0.004 and slit_z - 0.075 < points[v, 2] < slit_z + 0.004]  # peau extérieure de la lèvre basse et du menton seulement (l'intérieur de la bouche est lié à la mâchoire autrement)
region_set = set(region)
for _ in range(8):
    updated = target.copy()
    for v in region:
        updated[v] = target[v] + 0.5 * (np.mean([target[n] for n in neighbors[v]], axis=0) - target[v])
    target = updated
delta_open = target - opened
norms = np.linalg.norm(delta_open, axis=1)
delta_open *= np.minimum(1.0, 0.006 / np.maximum(norms, 1e-12))[:, None]  # borne de sécurité : jamais plus de 6 mm de correctif
big = np.where(np.linalg.norm(delta_open, axis=1) > 0.004)[0]
print("DELTA >4 mm :", len(big), [(int(v), round(float(np.linalg.norm(delta_open[v])) * 1000, 1), round(float(weight[v]), 2), (points[v] * 1000).round(0).tolist()) for v in big[:8]])
# 4. retour dans le repère de repos : (w R^-1 + (1 - w) I) delta_open ; R^-1 v = v @ R pour une rotation
layer = (weight[:, None] * (delta_open @ rotation) + (1 - weight[:, None]) * delta_open).astype(np.float32)
moved = np.linalg.norm(layer, axis=1)
print("COUCHE mouth_open sommets touchés", int((moved > 1e-6).sum()), "déplacement max mm", round(float(moved.max()) * 1000, 2), "largeur de bouche mm", round(mouth_width * 1000, 1),
      "convergence mm (par côté)", round(CONVERGENCE * mouth_width / 2 * 1000, 2), "région lissée", len(region_set))

# --- édition d'une copie du groupe ---------------------------------------------------------------------------------------------------------------
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
for datablock in list(bpy.data.meshes) + list(bpy.data.node_groups):
    if datablock.name.startswith("HL Human"):
        (bpy.data.meshes if isinstance(datablock, bpy.types.Mesh) else bpy.data.node_groups).remove(datablock)
with bpy.data.libraries.load(str(SOURCE), link=False) as (_, target_blocks):
    target_blocks.node_groups = ["HL Human"]
    target_blocks.meshes = ["HL Human Base"]
group, mesh = target_blocks.node_groups[0], target_blocks.meshes[0]
assert group.name == "HL Human" and mesh.name == "HL Human Base"
assert "b_f0" not in mesh.attributes.keys(), "couches de visage déjà présentes"
item = group.interface.new_socket("mouth_open", in_out="INPUT", socket_type="NodeSocketFloat")
item.default_value, item.min_value, item.max_value = 0.0, 0.0, 1.0
group_in = next(n for n in group.nodes if n.bl_idname == "NodeGroupInput")
set_position = next(n for n in group.nodes if n.bl_idname == "GeometryNodeSetPosition")
offset_link = next(l for l in group.links if l.to_node == set_position and l.to_socket.identifier == set_position.inputs["Offset"].identifier)
total = offset_link.from_socket
group.links.remove(offset_link)
attribute = mesh.attributes.new("b_f0", "FLOAT_VECTOR", "POINT")
attribute.data.foreach_set("vector", layer.ravel())
named = group.nodes.new("GeometryNodeInputNamedAttribute")
named.data_type = "FLOAT_VECTOR"
named.inputs["Name"].default_value = "b_f0"
scale = group.nodes.new("ShaderNodeVectorMath")
scale.operation = "SCALE"
group.links.new(named.outputs["Attribute"], scale.inputs[0])
group.links.new(group_in.outputs["mouth_open"], scale.inputs[3])
add = group.nodes.new("ShaderNodeVectorMath")
add.operation = "ADD"
group.links.new(total, add.inputs[0])
group.links.new(scale.outputs[0], add.inputs[1])
group.links.new(add.outputs[0], set_position.inputs["Offset"])
mesh["hl_face_layers"] = json.dumps({"mouth_open": {"couche": "b_f0", "ouverture_degres": OPEN_DEGREES, "convergence_pourcent": CONVERGENCE * 100, "sommets": int((moved > 1e-6).sum()), "deplacement_max_mm": round(float(moved.max()) * 1000, 3)}})
identifier = next(i.identifier for i in group.interface.items_tree if i.item_type == "SOCKET" and i.in_out == "INPUT" and i.name == "mouth_open")
group["hl_face_layers"] = 1
group.use_fake_user = True
mesh.use_fake_user = True
OUT.parent.mkdir(parents=True, exist_ok=True)
bpy.data.libraries.write(str(OUT), {group, mesh}, compress=True)
sockets = json.loads((ROOT / "extension" / "data" / "human_sockets.json").read_text(encoding="utf-8"))
sockets["mouth_open"] = [identifier, 0.0, 0.0, 1.0]
SOCKETS_OUT.write_text(json.dumps(sockets, indent=1, ensure_ascii=False), encoding="utf-8")
report = {"identifiant": identifier, "sommets": int((moved > 1e-6).sum()), "deplacement_max_mm": round(float(moved.max()) * 1000, 3), "octets": OUT.stat().st_size}
if REPORT:
    REPORT.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
print("FACE_LAYERS_OK", json.dumps(report, ensure_ascii=False))
