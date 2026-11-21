"""T-C12 (partiel) — HumanLoom peut-il ajouter un groupe de nœuds au menu Ajouter du graphe Geometry Nodes ? Test d'enregistrement seulement (pas de rendu d'interface).
Usage : blender --background --factory-startup --python tools/audit/tc12_menu.py -- <sortie.json>"""
import bpy, sys, json
from pathlib import Path
OUT = Path(sys.argv[-1]); R = {}
R["menus_node_add"] = sorted(n for n in dir(bpy.types) if n.startswith("NODE_MT_") and "add" in n.lower())[:40]
R["menus_geometry"] = sorted(n for n in dir(bpy.types) if n.startswith("NODE_MT_") and "geometry" in n.lower())[:60]
g = bpy.data.node_groups.new("HL Test", "GeometryNodeTree")
g.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
g.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
g.use_fake_user = True


class HL_OT_add_group(bpy.types.Operator):
    bl_idname = "node.hl_add_group"; bl_label = "Humain"
    def execute(self, ctx):
        return {"FINISHED"}


def draw(self, ctx):
    self.layout.separator()
    self.layout.operator("node.hl_add_group", text="HumanLoom")


tried = {}
bpy.utils.register_class(HL_OT_add_group)
for name in ("NODE_MT_geometry_node_add_all", "NODE_MT_add"):
    cls = getattr(bpy.types, name, None)
    if cls is None:
        tried[name] = "absent"; continue
    try:
        cls.append(draw); tried[name] = "append OK"
        cls.remove(draw)
    except Exception as e:
        tried[name] = "ERR " + str(e)[:150]
R["append_menu"] = tried
# assets de groupes de nœuds : marquer en asset
try:
    g.asset_mark(); R["asset_mark"] = "OK"
    R["asset_catalogue_API"] = hasattr(g.asset_data, "catalog_id")
except Exception as e:
    R["asset_mark"] = "ERR " + str(e)[:150]
OUT.write_text(json.dumps(R, indent=1, ensure_ascii=False), encoding="utf-8"); print("TC12_DONE")
