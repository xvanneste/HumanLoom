"""Extrait de `tools/data/realistic.blend` les données propres
dont l'humain natif a encore besoin : les deux yeux et le « porteur de relief » (maillage de base, groupe de sommets et
modificateur Displace de la peau avec son image). Écrit `extension/data/human_eyes.blend` (lot 5, étape « yeux autonomes »).

Usage : blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/build_human_eyes.py

Les yeux perdent leur parent et la cible de leurs pilotes (sinon `libraries.write` embarquerait le corps ancien et ses 462 clés) ;
`human._retarget_eye_drivers` les rebranche sur le modificateur de l'humain créé. `matrix_parent_inverse` est conservée."""
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools/data/realistic.blend"
OUT = ROOT / "extension/data/human_eyes.blend"
CARRIER = "HL Relief Source"

with bpy.data.libraries.load(str(SOURCE), link=False) as (_, target):
    target.objects = ["Corps", "Œil gauche", "Œil droit"]
body, *eyes = target.objects
for eye in eyes:
    inverse = eye.matrix_parent_inverse.copy()
    eye.parent = None
    eye.matrix_parent_inverse = inverse
    for fcurve in eye.data.shape_keys.animation_data.drivers:
        for variable in fcurve.driver.variables:
            for variable_target in variable.targets:
                variable_target.id = None

# Porteur de relief : géométrie de base sans clés de forme, groupe de sommets et Displace copiés tels quels.
#  Maillage reconstruit (une copie de `Corps` traîne ~12 Mo de données de clés de forme / propriétés) : sommets de base, faces, UV, groupe.
basis = body.data.shape_keys.key_blocks[0].data
mesh = bpy.data.meshes.new(CARRIER)
mesh.from_pydata([point.co[:] for point in basis], [], [tuple(polygon.vertices) for polygon in body.data.polygons])
for source_uv in body.data.uv_layers:
    layer = mesh.uv_layers.new(name=source_uv.name)
    layer.data.foreach_set("uv", [component for item in source_uv.data for component in item.uv])
carrier = bpy.data.objects.new(CARRIER, mesh)
for group in body.vertex_groups:
    target_group = carrier.vertex_groups.new(name=group.name)
    for vertex in body.data.vertices:
        for membership in vertex.groups:
            if membership.group == group.index and membership.weight:
                target_group.add([vertex.index], membership.weight, "REPLACE")
for modifier in body.modifiers:
    new = carrier.modifiers.new(modifier.name, modifier.type)
    for attribute in ("texture", "texture_coords", "uv_layer", "mid_level", "vertex_group", "strength", "direction"):
        if hasattr(modifier, attribute):
            setattr(new, attribute, getattr(modifier, attribute))
scene = bpy.context.scene
for obj in (carrier, *eyes):
    scene.collection.objects.link(obj)
    obj.use_fake_user = True
bpy.data.libraries.write(str(OUT), {carrier, mesh, *eyes, *(e.data for e in eyes)}, fake_user=True, compress=True)
report = {"source": str(SOURCE.relative_to(ROOT)), "sortie": str(OUT.relative_to(ROOT)), "octets": OUT.stat().st_size,
          "objets": [CARRIER] + [e.name for e in eyes], "sommets_porteur": len(mesh.vertices),
          "groupes": [g.name for g in carrier.vertex_groups], "modificateurs": [m.name for m in carrier.modifiers]}
print("HUMAN_EYES", json.dumps(report, ensure_ascii=False))
