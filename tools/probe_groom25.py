"""Read the actual Blender 5.2 native asset interface before integration."""
from pathlib import Path
import sys,json,bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import extension
extension.register();bpy.ops.human_modeling.create();body=bpy.context.object
body.select_set(True);bpy.ops.object.curves_empty_hair_add();hair=bpy.context.object
group=hair.modifiers[0].node_group
out=ROOT/'validation/groom-25';out.mkdir(parents=True,exist_ok=True)
report={'bounds':[[min(v.co[i] for v in body.data.vertices),max(v.co[i] for v in body.data.vertices)] for i in range(3)],'eyes':[(o.name,list(o.location)) for o in body.children if o.type=='MESH'],'native_inputs':[(s.name,s.identifier,s.socket_type,str(getattr(getattr(hair.modifiers[0].properties.inputs,s.identifier),'value',None))) for s in group.interface.items_tree if s.item_type=='SOCKET' and s.in_out=='INPUT'],'modifiers':[(m.name,m.type) for m in body.modifiers]}
(out/'probe.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
