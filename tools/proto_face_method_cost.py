"""Prototype jetable (lot F0, conception du visage) : COÛT D'ÉVALUATION de trois méthodes pour piloter ~52 commandes de visage sur la cage native (10 582 sommets).

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/proto_face_method_cost.py -- [--controls 52] [--region 1800] [--runs 30]

S : clés de forme (52 clés relatives, décalages sur ~1 800 sommets) ; N : groupe de nœuds avec 52 couches (attributs vectoriels nommés, un facteur par commande, Set Position) ;
B : armature de 40 os de visage (4 influences par sommet, ~1 800 sommets pondérés). Mesure : médiane / p90 de 30 changements de valeurs (évaluation du graphe de dépendances, maillage évalué lu),
dans le même processus, un seul objet évalué à la fois. Décalages et poids ALÉATOIRES : on mesure le coût, pas la qualité. Résultats imprimés (`MESURE ...`)."""
from pathlib import Path
import statistics
import sys
import time

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension.animation import skeleton  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
CONTROLS = int(ARGS[ARGS.index("--controls") + 1]) if "--controls" in ARGS else 52
REGION = int(ARGS[ARGS.index("--region") + 1]) if "--region" in ARGS else 1800
RUNS = int(ARGS[ARGS.index("--runs") + 1]) if "--runs" in ARGS else 30
rng = np.random.default_rng(7)

addon.register()
bpy.ops.humanloom.create()
source = bpy.context.object
points = skeleton.cage_points(source)
polygons = [tuple(p.vertices) for p in source.data.polygons]
face = np.where((points[:, 2] > points[:, 2].max() - 0.24) & (points[:, 1] < points[:, 1][points[:, 2] > points[:, 2].max() - 0.24].mean()))[0]
face = rng.choice(face, size=min(REGION, len(face)), replace=False)
print("MESURE sommets", len(points), "zone du visage", len(face), "commandes", CONTROLS)
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)


def make_object(name):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([tuple(p) for p in points], [], polygons)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def time_it(change, obj, label):
    obj.hide_viewport = False
    for other in bpy.data.objects:
        if other is not obj and other.type == "MESH":
            other.hide_viewport = True
    samples, changed, previous = [], 0, None
    for _ in range(RUNS):
        change()
        start = time.perf_counter()
        evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = evaluated.to_mesh()
        buffer = np.empty(len(mesh.vertices) * 3, np.float32)
        mesh.vertices.foreach_get("co", buffer)
        evaluated.to_mesh_clear()
        samples.append((time.perf_counter() - start) * 1000)
        if previous is not None and not np.allclose(previous, buffer):
            changed += 1
        previous = buffer
    samples.sort()
    print("MESURE", label, "résultats_différents", f"{changed}/{RUNS - 1}", "médiane_ms", round(statistics.median(samples), 2), "p90_ms", round(samples[int(0.9 * len(samples)) - 1], 2))


# référence : aucun modificateur
base = make_object("base")
time_it(lambda: base.update_tag(), base, "référence_sans_modificateur")

# S : clés de forme
shaped = make_object("shape_keys")
shaped.shape_key_add(name="Basis")
keys = []
for i in range(CONTROLS):
    key = shaped.shape_key_add(name=f"k{i}", from_mix=False)
    offset = np.zeros((len(points), 3))
    offset[face] = rng.normal(0, 0.002, (len(face), 3))
    key.data.foreach_set("co", (points + offset).ravel())
    keys.append(key)


def change_shape():
    for key in rng.choice(keys, 6, replace=False):
        key.value = float(rng.random())


time_it(change_shape, shaped, f"S_clés_de_forme_{CONTROLS}")

# N : groupe de nœuds, une couche vectorielle par commande
nodal = make_object("nodes")
for i in range(CONTROLS):
    attribute = nodal.data.attributes.new(f"f{i}", "FLOAT_VECTOR", "POINT")
    layer = np.zeros((len(points), 3), np.float32)
    layer[face] = rng.normal(0, 0.002, (len(face), 3))
    attribute.data.foreach_set("vector", layer.ravel())
tree = bpy.data.node_groups.new("face_proto", "GeometryNodeTree")
tree.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
tree.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
sockets = [tree.interface.new_socket(f"c{i}", in_out="INPUT", socket_type="NodeSocketFloat") for i in range(CONTROLS)]
group_in = tree.nodes.new("NodeGroupInput")
group_out = tree.nodes.new("NodeGroupOutput")
set_position = tree.nodes.new("GeometryNodeSetPosition")
tree.links.new(group_in.outputs[0], set_position.inputs["Geometry"])
accumulated = None
for i in range(CONTROLS):
    named = tree.nodes.new("GeometryNodeInputNamedAttribute")
    named.data_type = "FLOAT_VECTOR"
    named.inputs["Name"].default_value = f"f{i}"
    scale = tree.nodes.new("ShaderNodeVectorMath")
    scale.operation = "SCALE"
    tree.links.new(named.outputs["Attribute"], scale.inputs[0])
    tree.links.new(group_in.outputs[1 + i], scale.inputs[3])
    if accumulated is None:
        accumulated = scale.outputs[0]
    else:
        add = tree.nodes.new("ShaderNodeVectorMath")
        add.operation = "ADD"
        tree.links.new(accumulated, add.inputs[0])
        tree.links.new(scale.outputs[0], add.inputs[1])
        accumulated = add.outputs[0]
tree.links.new(accumulated, set_position.inputs["Offset"])
remove = tree.nodes.new("GeometryNodeRemoveAttribute")
remove.inputs["Pattern Mode"].default_value = "Wildcard"
remove.inputs["Name"].default_value = "f*"
tree.links.new(set_position.outputs["Geometry"], remove.inputs["Geometry"])
tree.links.new(remove.outputs["Geometry"], group_out.inputs[0])
modifier = nodal.modifiers.new("face", "NODES")
modifier.node_group = tree
identifiers = [s.identifier for s in sockets]


def change_nodes():
    for i in rng.choice(CONTROLS, 6, replace=False):
        getattr(modifier.properties.inputs, identifiers[int(i)]).value = float(rng.random())
    nodal.update_tag()


time_it(change_nodes, nodal, f"N_nœuds_{CONTROLS}_couches")

# B : os de visage
rigged = make_object("bones")
armature_data = bpy.data.armatures.new("rig")
armature = bpy.data.objects.new("rig", armature_data)
bpy.context.scene.collection.objects.link(armature)
bpy.context.view_layer.objects.active = armature
bpy.ops.object.mode_set(mode="EDIT")
center = points[face].mean(0)
count = 40
for i in range(count):
    bone = armature_data.edit_bones.new(f"f{i}")
    head = points[face[i * len(face) // count]]
    bone.head, bone.tail = tuple(head), tuple(head + np.array([0, -0.01, 0]))
bpy.ops.object.mode_set(mode="OBJECT")
for i in range(count):
    group = rigged.vertex_groups.new(name=f"f{i}")
for vertex in face:
    chosen = rng.choice(count, 4, replace=False)
    weights = rng.random(4)
    weights /= weights.sum()
    for c, w in zip(chosen, weights):
        rigged.vertex_groups[int(c)].add([int(vertex)], float(w), "REPLACE")
modifier = rigged.modifiers.new("arm", "ARMATURE")
modifier.object = armature


def change_bones():
    for i in rng.choice(count, 6, replace=False):
        pose = armature.pose.bones[f"f{int(i)}"]
        pose.rotation_mode = "XYZ"
        pose.rotation_euler = tuple(rng.normal(0, 0.2, 3))
        pose.location = tuple(rng.normal(0, 0.002, 3))


time_it(change_bones, rigged, f"B_os_de_visage_{count}")
print("PROTO_OK")
