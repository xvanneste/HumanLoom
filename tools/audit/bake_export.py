"""T-X4 — « Bake pour export » : applique l'identité (groupe de nœuds) dans le maillage de base en conservant une expression (shape key), puis exporte FBX/glTF et relit.
Lecture seule sur le dépôt ; sorties dans le dossier donné. Usage :
blender --background --factory-startup --python tools/audit/bake_export.py -- <dossier_sortie>
"""
import bpy, sys, json, os
import numpy as np
from pathlib import Path
OUT = Path(sys.argv[-1]); OUT.mkdir(parents=True, exist_ok=True)
ROOT = Path(__file__).resolve().parents[2]
bpy.ops.wm.open_mainfile(filepath=str(ROOT / "extension" / "data" / "realistic.blend"))
src = bpy.data.objects["Corps"]; k = src.data.shape_keys
nv = len(src.data.vertices)
R = {}


def co(x):
    a = np.empty(nv * 3, np.float32); x.data.foreach_get("co", a); return a


base = co(k.reference_key)
cands = []
for kb in k.key_blocks:
    if kb == k.reference_key:
        continue
    d = co(kb) - co(kb.relative_key)
    if np.abs(d).max() > 1e-4:
        cands.append((kb.name, d))
    if len(cands) >= 4:
        break
R["cles_utilisees"] = [n for n, _ in cands]
mesh = src.data.copy(); mesh.name = "bake_mesh"
obj = bpy.data.objects.new("bake_body", mesh); bpy.context.scene.collection.objects.link(obj)
obj.shape_key_clear()
mesh.vertices.foreach_set("co", base); mesh.update()
for i, (_, d) in enumerate(cands):
    a = mesh.attributes.new("d" + str(i), "FLOAT_VECTOR", "POINT"); a.data.foreach_set("vector", d)
g = bpy.data.node_groups.new("MiniId", "GeometryNodeTree")
g.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
g.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
for i in range(len(cands)):
    g.interface.new_socket("W" + str(i), in_out="INPUT", socket_type="NodeSocketFloat")
gi = g.nodes.new("NodeGroupInput"); go = g.nodes.new("NodeGroupOutput"); sp = g.nodes.new("GeometryNodeSetPosition")
g.links.new(gi.outputs[0], sp.inputs["Geometry"]); acc = None
for i in range(len(cands)):
    na = g.nodes.new("GeometryNodeInputNamedAttribute"); na.data_type = "FLOAT_VECTOR"; na.inputs["Name"].default_value = "d" + str(i)
    sc = g.nodes.new("ShaderNodeVectorMath"); sc.operation = "SCALE"
    g.links.new(na.outputs["Attribute"], sc.inputs[0]); g.links.new(gi.outputs[i + 1], sc.inputs[3])
    if acc is None:
        acc = sc.outputs[0]
    else:
        ad = g.nodes.new("ShaderNodeVectorMath"); ad.operation = "ADD"
        g.links.new(acc, ad.inputs[0]); g.links.new(sc.outputs[0], ad.inputs[1]); acc = ad.outputs[0]
g.links.new(acc, sp.inputs["Offset"])
rm = g.nodes.new("GeometryNodeRemoveAttribute"); rm.inputs["Pattern Mode"].default_value = "Wildcard"; rm.inputs["Name"].default_value = "d*"
g.links.new(sp.outputs["Geometry"], rm.inputs["Geometry"]); g.links.new(rm.outputs["Geometry"], go.inputs[0])
md = obj.modifiers.new("HL Human", "NODES"); md.node_group = g
ids = [s.identifier for s in g.interface.items_tree if s.item_type == "SOCKET" and s.in_out == "INPUT" and s.name.startswith("W")]
W = [0.9, -0.6, 0.8, 0.5]
for i, sid in enumerate(ids):
    getattr(md.properties.inputs, sid).value = W[i]


def ev():
    obj.update_tag(); bpy.context.view_layer.update()
    e = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()); me = e.to_mesh()
    a = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", a); e.to_mesh_clear(); return a


# expression : déplacement local sur la bouche, en shape key du maillage de base
obj.shape_key_add(name="Basis", from_mix=False)
expr = obj.shape_key_add(name="Smile", from_mix=False)
pts = np.array([v.co[:] for v in mesh.vertices])
mask = (np.abs(pts[:, 0]) < 0.06) & (pts[:, 2] > 1.50) & (pts[:, 2] < 1.60) & (pts[:, 1] < 0.0)
delta = np.zeros_like(pts); delta[mask] = [0.0, -0.004, 0.006]
expr.data.foreach_set("co", (pts + delta).reshape(-1)); mesh.update()
expr.value = 1.0
R["sommets_touches_par_expression"] = int(mask.sum())
ref_full = ev()                               # identité + expression, évalué
# --- BAKE : identité dans la base, expression conservée (delta additif) ---
expr.value = 0.0
ident = ev()                                  # identité seule (ce que doit devenir la nouvelle base)
shift = (ident - pts.reshape(-1))
basis = obj.data.shape_keys.key_blocks["Basis"]
basis.data.foreach_set("co", ident)           # nouvelle base
expr.data.foreach_set("co", ident + delta.reshape(-1))   # delta d'expression inchangé
obj.modifiers.remove(md)
for i in range(len(cands)):
    obj.data.attributes.remove(obj.data.attributes["d" + str(i)])
mesh.vertices.foreach_set("co", ident); mesh.update()
expr.value = 1.0
obj.update_tag(); bpy.context.view_layer.update()
after = ev()
R["bake_equivalence_max_mm"] = round(float(np.abs(after - ref_full).max()) * 1000, 6)
R["modificateurs_restants"] = [m.type for m in obj.modifiers]
R["attributs_d_restants"] = [a.name for a in obj.data.attributes if a.name.startswith("d")]
# --- exports ---
for o in list(bpy.data.objects):
    if o != obj:
        bpy.data.objects.remove(o, do_unlink=True)
bpy.ops.object.select_all(action="DESELECT"); obj.select_set(True); bpy.context.view_layer.objects.active = obj
res = {}
p = str(OUT / "bake.fbx")
bpy.ops.export_scene.fbx(filepath=p, use_selection=True, use_mesh_modifiers=False, object_types={"MESH"})
res["fbx_Mo"] = round(os.path.getsize(p) / 1e6, 2)
p2 = str(OUT / "bake.glb")
bpy.ops.export_scene.gltf(filepath=p2, use_selection=True, export_apply=False, export_morph=True)
res["glb_Mo"] = round(os.path.getsize(p2) / 1e6, 2)
R["exports"] = res
# --- réimport et comparaison ---
for tag, imp in (("fbx", lambda: bpy.ops.wm.fbx_import(filepath=str(OUT / "bake.fbx"))), ("glb", lambda: bpy.ops.import_scene.gltf(filepath=str(OUT / "bake.glb")))):
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    try:
        imp()
        m = [o for o in bpy.data.objects if o.type == "MESH"][0]
        sk = m.data.shape_keys
        info = {"sommets": len(m.data.vertices), "shape_keys": [b.name for b in sk.key_blocks] if sk else []}
        if sk and len(sk.key_blocks) > 1:
            kb = sk.key_blocks[-1]; kb.value = 0.0
            m.update_tag(); bpy.context.view_layer.update()
            a0 = np.array([v.co[:] for v in m.data.vertices]).reshape(-1)
            b1 = np.array([v.co[:] for v in kb.data]).reshape(-1)
            # identité conservée dans la base (comparée à `ident`, tolérance : axes/échelle de l'import)
            info["delta_expression_max_mm_apres_import"] = round(float(np.abs(b1 - a0).max()) * 1000, 3)
        R["reimport_" + tag] = info
    except Exception as e:
        R["reimport_" + tag] = "ERR " + str(e)[:200]
(OUT / "bake_export.json").write_text(json.dumps(R, indent=1, ensure_ascii=False), encoding="utf-8")
print("BAKE_DONE")
