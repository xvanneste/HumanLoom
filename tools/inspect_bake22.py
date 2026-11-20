import bpy
for op in [bpy.ops.object.simulation_nodes_cache_bake,bpy.ops.object.simulation_nodes_cache_delete,bpy.ops.object.geometry_node_bake_single]:
 try:print(op.get_rna_type().identifier,[(p.identifier,p.type) for p in op.get_rna_type().properties])
 except Exception as e:print(str(e))
for name in ['NodesModifierBake','NodesModifier']:
 cls=getattr(bpy.types,name);print(name,[(p.identifier,p.type) for p in cls.bl_rna.properties])
