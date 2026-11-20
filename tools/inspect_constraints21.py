from pathlib import Path
import bpy
p=Path('C:/Users/xvann/OneDrive/Documents/ChatGPT/BlenderDev/validation/cheveux-20/Prototype-cheveux-01.blend');bpy.ops.wm.open_mainfile(filepath=str(p))
for g in bpy.data.node_groups:
 if any(x in g.name.lower() for x in ['attach','pin','bind','static rod']):
  print('GROUP',g.name,'NODES',[(n.name,n.bl_idname) for n in g.nodes if n.type=='GROUP'])
  print('INTERFACE',[(i.name,getattr(i,'default_value',None)) for i in g.interface.items_tree if i.item_type=='SOCKET' and i.in_out=='INPUT'])
g=bpy.data.node_groups['Hair Dynamics']
for n in g.nodes:
 if n.type=='GROUP':print('DYN',n.name,n.node_tree.name,[(s.name,str(s.default_value)) for s in n.inputs if hasattr(s,'default_value') and not s.is_linked])
for n in g.nodes:
 if 'attach' in n.name.lower() or 'pin' in n.name.lower():
  print('ATTACHNODE',n.name)
  for link in g.links:
   if link.to_node==n or link.from_node==n:print('LINK',link.from_node.name,link.from_socket.name,'->',link.to_node.name,link.to_socket.name)

for name in ("Rod Stretch/Shear Constraint","Rod Bend/Twist Constraint","Curve Stretching Compliance"):
 g=bpy.data.node_groups[name];print("DETAIL",name)
 for n in g.nodes:
  print("NODE",n.name,n.bl_idname,[(s.name,str(s.default_value)) for s in n.inputs if hasattr(s,"default_value") and not s.is_linked])
 for l in g.links:print("L",l.from_node.name,l.from_socket.name,"->",l.to_node.name,l.to_socket.name)
