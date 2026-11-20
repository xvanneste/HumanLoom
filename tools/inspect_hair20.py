from pathlib import Path
import bpy,json,numpy as np
p=Path('C:/Users/xvann/OneDrive/Documents/ChatGPT/BlenderDev')
with bpy.data.libraries.load(str(p/'extension/data/realistic.blend'),link=False) as (s,d):d.collections=['Realistic Human Base']
bpy.context.scene.collection.children.link(d.collections[0]);b=next(o for o in d.collections[0].objects if o.get('human_modeling_body'))
a=np.array([v.co[:] for v in b.data.vertices]);hi=a[:,2].max();print('BOUNDS',a.min(0),a.max(0))
for dz in [.04,.08,.12,.16,.20,.24]:
 q=a[a[:,2]>hi-dz]; print('HEAD',dz,q.min(0),q.max(0))
b.select_set(True);bpy.context.view_layer.objects.active=b;bpy.ops.object.curves_empty_hair_add();h=bpy.context.object
print('CURVES_METHODS',h.data.add_curves.__doc__)
for m in h.modifiers:
 print('MOD',m.name,m.type,[(p.identifier,p.type) for p in m.bl_rna.properties]); print('MODDIR',[n for n in dir(m) if 'input' in n or 'setting' in n or 'property' in n])
 for it in m.node_group.interface.items_tree:
  if it.item_type=='SOCKET' and it.in_out=='INPUT' and it.name=='Mode':print('MODE',it.identifier,str(it.default_value), 'PROPS',m.properties, 'RNA',[(p.identifier,p.type) for p in m.properties.bl_rna.properties],'INPUTS',m.properties.inputs,[(p.identifier,p.type) for p in m.properties.inputs.bl_rna.properties],'VALUE',[(p.identifier,p.type) for p in getattr(m.properties.inputs,it.identifier).bl_rna.properties])
print('ATTRS',[(a.name,a.data_type,a.domain) for a in h.data.attributes])
print('RECURSIVE')
for g in bpy.data.node_groups:
 if any(n.bl_idname=='GeometryNodeInputNamedAttribute' for n in g.nodes):
  if any(s in g.name.lower() for s in ['surface','hair','attach','deform']):print(g.name,[(n.bl_idname,n.inputs['Name'].default_value) for n in g.nodes if n.bl_idname=='GeometryNodeInputNamedAttribute'])

