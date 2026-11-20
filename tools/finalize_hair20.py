"""Save an inspectable camera view and readable prototype node layouts."""
from pathlib import Path
import bpy

assert bpy.app.background and bpy.app.version[:2] == (5,2)
root=Path(__file__).resolve().parents[1]
path=root/'validation/cheveux-20/Prototype-cheveux-01.blend'
bpy.ops.wm.open_mainfile(filepath=str(path))
for group in bpy.data.node_groups:
    if not group.name.startswith('Prototype ·'):
        continue
    for node in group.nodes:
        if node.type=='GROUP_INPUT':node.location=(-520,120)
        elif node.type=='GROUP_OUTPUT':node.location=(240,120)
        elif node.bl_idname=='GeometryNodeInputNamedAttribute':node.location=(-520,-140)
        else:node.location=(-160,120)
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA'
hair=next(obj for obj in bpy.context.scene.objects if obj.get('hm_hair_prototype'))
for obj in bpy.context.selected_objects:obj.select_set(False)
hair.select_set(True)
bpy.context.view_layer.objects.active=hair
bpy.ops.wm.save_as_mainfile(filepath=str(path),compress=True)
print('HAIR20_FINALIZED',flush=True)
