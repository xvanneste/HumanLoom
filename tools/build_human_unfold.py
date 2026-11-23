"""Ajoute au groupe de nœuds « HL Human » une COUCHE DE DÉPLIAGE qui lève les croisements de triangles de la tête (paupières, commissures : I-49) pour les couples (sexe, âge) où ils apparaissent.

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/build_human_unfold.py -- <human_nodes_entree.blend> <human_nodes_sortie.blend> [--report rapport.json]

Principe (faisabilité mesurée par `tools/proto_unfold_head_crossings.py` : 0 croisement après lissage local, déplacement maximal 2,9 mm) :
- pour chacun des 5 sexes (0 ; 0,25 ; 0,5 ; 0,75 ; 1) x 7 âges (0 à 3 par 0,5) où la cage (contrôles à 0) a des croisements dans la tête, les sommets concernés et leurs 2 anneaux voisins sont lissés
  (Laplacien, λ = 0,5, une itération à la fois jusqu'au premier état sans croisement) ; la différence lissé - original est une couche vectorielle de sommets ;
- ces couches sont combinées dans le groupe par des « chapeaux » en sexe (pas 0,25) et en âge (pas 0,5) : correction = somme sur la grille de chapeau(sexe) x chapeau(âge) x couche ; elle s'ajoute au décalage
  total juste avant `Set Position` ; les couches sont supprimées en sortie comme les autres (`b*`).
- le fichier de sortie est une COPIE : l'entrée n'est jamais modifiée. Refuse de s'appliquer deux fois."""
import hashlib
import json
from pathlib import Path
import sys

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
ARGS = sys.argv[sys.argv.index("--") + 1:]
SOURCE, OUT = Path(ARGS[0]).resolve(), Path(ARGS[1]).resolve()
REPORT = Path(ARGS[ARGS.index("--report") + 1]).resolve() if "--report" in ARGS else None
SEXES = (0.0, 0.25, 0.5, 0.75, 1.0)
AGES = (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0)
RINGS = int(ARGS[ARGS.index("--rings") + 1]) if "--rings" in ARGS else 2  # anneaux voisins ajoutés autour des sommets des triangles qui se croisent

import extension as addon  # noqa: E402
from extension import geometry_quality, human  # noqa: E402
from extension.animation import skeleton  # noqa: E402

addon.register()
bpy.ops.humanloom.create()
body = bpy.context.object
mesh_body = body.data
mesh_body.calc_loop_triangles()
triangles = np.array([t.vertices[:] for t in mesh_body.loop_triangles])
neighbors = [set() for _ in range(len(mesh_body.vertices))]
for e in mesh_body.edges:
    a, b = e.vertices
    neighbors[a].add(b)
    neighbors[b].add(a)


def head_pairs(points):
    result = geometry_quality.intersections(points, triangles)
    return [p for p in result["sample_triangle_pairs"] if points[triangles[list(p)].reshape(-1)].mean(0)[2] > 1.3]


def cage(sex, age):
    for name in human.sockets():
        if name not in ("sex", "age"):
            human.set_value(body, name, 0.0)
    human.set_value(body, "sex", sex)
    human.set_value(body, "age", age)
    return skeleton.cage_points(body)


layers = {}  # (i, j) -> (N, 3) float32
for i, sex in enumerate(SEXES):
    for j, age in enumerate(AGES):
        points = cage(sex, age)
        pairs = head_pairs(points)
        if not pairs:
            continue
        region = {int(v) for p in pairs for t in p for v in triangles[t]}
        for _ in range(RINGS):
            region |= {n for v in list(region) for n in neighbors[v]}
        region = sorted(region)
        moved = points.copy()
        for iteration in range(1, 61):  # une itération à la fois : on s'arrête dès le premier état sans croisement (déplacement minimal)
            updated = moved.copy()
            for v in region:
                updated[v] = moved[v] + 0.5 * (np.mean([moved[n] for n in neighbors[v]], axis=0) - moved[v])
            moved = updated
            if not head_pairs(moved):
                break
        # les sommets des triangles quasi dégénérés (< 0,1 mm²) sont ramenés à leur position d'origine tant que cela ne recrée aucun croisement : les déplacer fait basculer ces triangles
        # sous les contrôles extrêmes (nose_bridge -1 à sexe 0 âge 1,5 : un triangle de 0,008 mm²)
        tiny = np.where(0.5 * np.linalg.norm(np.cross(points[triangles[:, 1]] - points[triangles[:, 0]], points[triangles[:, 2]] - points[triangles[:, 0]]), axis=1) < 1e-7)[0]
        for v in sorted({int(v) for t in tiny for v in triangles[t]} & set(region)):
            kept = moved[v].copy()
            moved[v] = points[v]
            if head_pairs(moved):
                moved[v] = kept
        remaining = len(head_pairs(moved))
        assert remaining == 0, (sex, age, remaining)
        layers[(i, j)] = (moved - points).astype(np.float32)
        print("COUCHE", sex, age, "croisements", len(pairs), "-> 0", "déplacement max mm", round(float(np.linalg.norm(layers[(i, j)], axis=1).max()) * 1000, 2))
assert layers, "aucun croisement : rien à corriger"
union = sorted({int(v) for layer in layers.values() for v in np.nonzero(np.abs(layer).sum(1) > 0)[0]})
max_mm = max(float(np.linalg.norm(layer, axis=1).max()) for layer in layers.values()) * 1000

# --- édition d'une copie du groupe -----------------------------------------------------------------------------------------------------------------
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
for datablock in list(bpy.data.meshes) + list(bpy.data.node_groups):  # libérer les noms « HL Human » / « HL Human Base » (sinon la copie chargée serait renommée .001)
    if datablock.name.startswith("HL Human"):
        (bpy.data.meshes if isinstance(datablock, bpy.types.Mesh) else bpy.data.node_groups).remove(datablock)
with bpy.data.libraries.load(str(SOURCE), link=False) as (_, target):
    target.node_groups = ["HL Human"]
    target.meshes = ["HL Human Base"]
group, mesh = target.node_groups[0], target.meshes[0]
assert group.name == "HL Human" and mesh.name == "HL Human Base", (group.name, mesh.name)
assert not any(a.startswith("b_u") for a in mesh.attributes.keys()), "couche de dépliage déjà présente"
group_in = next(n for n in group.nodes if n.bl_idname == "NodeGroupInput")
set_position = next(n for n in group.nodes if n.bl_idname == "GeometryNodeSetPosition")
offset_link = next(l for l in group.links if l.to_node == set_position and l.to_socket.identifier == set_position.inputs["Offset"].identifier)
total_offset = offset_link.from_socket
group.links.remove(offset_link)
sex_socket, age_socket = group_in.outputs["sex"], group_in.outputs["age"]


def math(op, a, b=None):
    node = group.nodes.new("ShaderNodeMath")
    node.operation = op
    for index, value in enumerate((a, b)):
        if value is None:
            continue
        if isinstance(value, (int, float)):
            node.inputs[index].default_value = float(value)
        else:
            group.links.new(value, node.inputs[index])
    return node.outputs[0]


def hat(value_socket, center, half):
    return math("MAXIMUM", math("SUBTRACT", 1.0, math("MULTIPLY", math("ABSOLUTE", math("SUBTRACT", value_socket, center)), 1.0 / half)), 0.0)


sex_hats = {i: hat(sex_socket, SEXES[i], 0.25) for i in sorted({i for i, _ in layers})}
age_hats = {j: hat(age_socket, AGES[j], 0.5) for j in sorted({j for _, j in layers})}
correction = None
for n, ((i, j), layer) in enumerate(sorted(layers.items())):
    attribute = mesh.attributes.new(f"b_u{n}", "FLOAT_VECTOR", "POINT")
    attribute.data.foreach_set("vector", layer.ravel())
    named = group.nodes.new("GeometryNodeInputNamedAttribute")
    named.data_type = "FLOAT_VECTOR"
    named.inputs["Name"].default_value = f"b_u{n}"
    scale = group.nodes.new("ShaderNodeVectorMath")
    scale.operation = "SCALE"
    group.links.new(named.outputs["Attribute"], scale.inputs[0])
    group.links.new(math("MULTIPLY", sex_hats[i], age_hats[j]), scale.inputs[3])
    if correction is None:
        correction = scale.outputs[0]
    else:
        add = group.nodes.new("ShaderNodeVectorMath")
        add.operation = "ADD"
        group.links.new(correction, add.inputs[0])
        group.links.new(scale.outputs[0], add.inputs[1])
        correction = add.outputs[0]
final = group.nodes.new("ShaderNodeVectorMath")
final.operation = "ADD"
group.links.new(total_offset, final.inputs[0])
group.links.new(correction, final.inputs[1])
group.links.new(final.outputs[0], set_position.inputs["Offset"])
mesh["hl_unfold"] = json.dumps({"vertices": union, "grille_sexe": SEXES, "grille_age": AGES, "couches": len(layers), "deplacement_max_mm": round(max_mm, 3)})


def graph_fingerprint(tree):
    rows = []
    for node in sorted(tree.nodes, key=lambda n: n.name):
        defaults = []
        for socket in node.inputs:
            if not socket.is_linked and hasattr(socket, "default_value"):
                value = socket.default_value
                if isinstance(value, str):
                    pass
                elif isinstance(value, (int, float)):
                    value = round(float(value), 6)
                else:
                    try:
                        value = [round(float(x), 6) for x in value]
                    except (TypeError, ValueError):
                        value = str(value)
                defaults.append((socket.identifier, value))
        rows.append([node.name, node.bl_idname, getattr(node, "operation", ""), getattr(node, "data_type", ""), defaults])
    links = sorted((l.from_node.name, l.from_socket.identifier, l.to_node.name, l.to_socket.identifier) for l in tree.links)
    interface = [(s.name, s.in_out, s.socket_type, round(getattr(s, "default_value", 0) or 0, 6) if s.socket_type == "NodeSocketFloat" else 0) for s in tree.interface.items_tree]
    return hashlib.sha256(json.dumps([rows, links, interface], default=str, sort_keys=True).encode()).hexdigest()


group["hl_graph_fingerprint"] = graph_fingerprint(group)
group["hl_unfold"] = 1
group.use_fake_user = True
mesh.use_fake_user = True
OUT.parent.mkdir(parents=True, exist_ok=True)
bpy.data.libraries.write(str(OUT), {group, mesh}, compress=True)
report = {"couches": len(layers), "sommets_corriges": len(union), "deplacement_max_mm": round(max_mm, 3), "octets": OUT.stat().st_size, "noeuds": len(group.nodes)}
if REPORT:
    REPORT.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
print("UNFOLD_OK", json.dumps(report, ensure_ascii=False))
