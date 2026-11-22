"""Read-only capability audit in an isolated Blender 5.2 background process."""
from pathlib import Path
import bpy
import json

assert bpy.app.version[:2] == (5, 2)
root = Path(__file__).resolve().parents[1]
out = root / 'validation/pilosite-19'
out.mkdir(exist_ok=True)
report = {'blender': bpy.app.version_string, 'build': bpy.app.build_hash.decode(), 'libraries': {}, 'nodes': {}, 'body': {}}
assets = Path(bpy.utils.system_resource('DATAFILES')) / 'assets/nodes'
for filename in ('procedural_hair_node_assets.blend', 'geometry_nodes_dynamics_assets.blend', 'geometry_nodes_essentials.blend'):
    with bpy.data.libraries.load(str(assets / filename), link=False) as (src, dst):
        names = list(src.node_groups)
        selected = [name for name in names if 'Rest' in name or name in ('Hair Dynamics', 'Interpolate Hair Curves', 'Generate Hair Curves', 'Attach Hair Curves', 'Set Hair Curve Profile', 'Clump Hair Curves', 'Frizz Hair Curves', 'Curl Hair Curves', 'Trim Hair Curves', 'Hair Curves Noise', 'Collider')]
        dst.node_groups = selected
    report['libraries'][filename] = {'groups_available': names, 'loaded': [group.name for group in dst.node_groups]}
    for group in dst.node_groups:
        report['nodes'][group.name] = {
            'interface': [{'name': item.name, 'identifier': item.identifier, 'direction': item.in_out, 'type': item.socket_type} for item in group.interface.items_tree if item.item_type == 'SOCKET'],
            'internal_nodes': sorted(set(node.bl_idname for node in group.nodes)),
            'nested_groups': sorted(set(node.node_tree.name for node in group.nodes if node.type == 'GROUP' and node.node_tree)),
        }
tree = bpy.data.node_groups.new('Audit capability only', 'GeometryNodeTree')
for name in ('GeometryNodeDeformCurvesOnSurface', 'GeometryNodeCaptureRestGeometry', 'GeometryNodeXPBDSolver'):
    try:
        node = tree.nodes.new(name)
        report['nodes'][name] = {'created': True, 'inputs': [s.name for s in node.inputs], 'outputs': [s.name for s in node.outputs]}
    except Exception as exc:
        report['nodes'][name] = {'created': False, 'error': str(exc)}
curves = bpy.data.hair_curves.new('Audit data only')
report['curves_properties'] = [prop.identifier for prop in curves.bl_rna.properties]
with bpy.data.libraries.load(str(root / 'tools/data/realistic.blend'), link=False) as (src, dst):
    dst.objects = list(src.objects)
for obj in dst.objects:
    if obj.type != 'MESH' or not obj.get('human_modeling_body'):
        continue
    report['body'][obj.name] = {
        'vertices': len(obj.data.vertices), 'polygons': len(obj.data.polygons),
        'uv_layers': [layer.name for layer in obj.data.uv_layers],
        'active_uv': obj.data.uv_layers.active.name if obj.data.uv_layers.active else None,
        'rest_position_enabled': obj.add_rest_position_attribute,
        'modifiers': [{'name': mod.name, 'type': mod.type, 'uv_smooth': getattr(mod, 'uv_smooth', None)} for mod in obj.modifiers],
    }
    bpy.context.scene.collection.objects.link(obj)
    for selected_obj in bpy.context.selected_objects:
        selected_obj.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    result = bpy.ops.object.curves_empty_hair_add()
    hair = bpy.context.object
    report['native_empty_hair'] = {
        'operator_result': sorted(result), 'type': hair.type,
        'surface_correct': hair.data.surface == obj,
        'surface_uv_map': hair.data.surface_uv_map,
        'body_rest_position_after': obj.add_rest_position_attribute,
        'body_stack_after': [{'name': mod.name, 'type': mod.type, 'group': mod.node_group.name if mod.type == 'NODES' and mod.node_group else None} for mod in obj.modifiers],
        'hair_stack': [{'name': mod.name, 'type': mod.type, 'group': mod.node_group.name if mod.type == 'NODES' and mod.node_group else None} for mod in hair.modifiers],
    }
(out / 'blender52-capacites.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
print('HAIR52_AUDIT', len(report['nodes']), 'groups/nodes, bodies', list(report['body']), flush=True)
