"""Met à l'échelle les commandes de visage par la TAILLE DE LA TÊTE selon l'âge (un enfant ne reçoit pas les déplacements d'un adulte) : patch d'une COPIE de `human_nodes.blend`.

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/build_face_scale.py -- <entree.blend> <sortie.blend>

Facteur d'échelle(âge) = interpolation linéaire par stades (0, 1, 2, 3) de la PROFONDEUR de tête mesurée sur NOTRE cage (sexe 0,5, tête = sommets à moins de 22 cm du sommet) rapportée à celle de l'âge 2 :
0,895 (âge 0), 0,955 (âge 1), 1,0 (âge 2), 1,0 (âge 3) (194,0 / 207,1 / 216,8 / 216,9 mm). C'est une mesure de NOTRE modèle, pas une donnée publiée. Chaque entrée de commande (`b_f*`) est multipliée
par ce facteur avant de multiplier sa couche."""
import json
from pathlib import Path
import sys

import bpy

ARGS = sys.argv[sys.argv.index("--") + 1:]
SOURCE, OUT = Path(ARGS[0]).resolve(), Path(ARGS[1]).resolve()
FACTORS = (0.895, 0.955, 1.0, 1.0)
for datablock in list(bpy.data.meshes) + list(bpy.data.node_groups):
    if datablock.name.startswith("HL Human"):
        (bpy.data.meshes if isinstance(datablock, bpy.types.Mesh) else bpy.data.node_groups).remove(datablock)
with bpy.data.libraries.load(str(SOURCE), link=False) as (_, blocks):
    blocks.node_groups = ["HL Human"]
    blocks.meshes = ["HL Human Base"]
group, mesh = blocks.node_groups[0], blocks.meshes[0]
assert group.name == "HL Human" and mesh.name == "HL Human Base"
assert not group.get("hl_face_scale"), "mise à l'échelle déjà appliquée"
group_in = next(n for n in group.nodes if n.bl_idname == "NodeGroupInput")
age = group_in.outputs["age"]


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


factor = None
for stage, value in enumerate(FACTORS):
    hat = math("MAXIMUM", math("SUBTRACT", 1.0, math("ABSOLUTE", math("SUBTRACT", age, float(stage)))), 0.0)
    term = math("MULTIPLY", hat, value)
    factor = term if factor is None else math("ADD", factor, term)
patched = 0
for node in list(group.nodes):
    if node.bl_idname != "ShaderNodeVectorMath" or node.operation != "SCALE":
        continue
    source = node.inputs[0].links[0].from_node if node.inputs[0].is_linked else None
    if source is None or source.bl_idname != "GeometryNodeInputNamedAttribute" or not str(source.inputs["Name"].default_value).startswith("b_f"):
        continue
    link = node.inputs[3].links[0]
    command = link.from_socket
    group.links.remove(link)
    group.links.new(math("MULTIPLY", command, factor), node.inputs[3])
    patched += 1
assert patched >= 18, patched
group["hl_face_scale"] = json.dumps({"stades_age": [0, 1, 2, 3], "facteurs": FACTORS, "source": "profondeur de tête de la cage native (mesure du modèle, sexe 0,5) rapportée à l'âge 2"})
group.use_fake_user = True
mesh.use_fake_user = True
OUT.parent.mkdir(parents=True, exist_ok=True)
bpy.data.libraries.write(str(OUT), {group, mesh}, compress=True)
print("FACE_SCALE_OK", patched, "couches mises à l'échelle")
