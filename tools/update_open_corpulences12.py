"""Upgrade the open Blender 5.2 scene and preserve a sibling checkpoint."""
from datetime import datetime
import json
from pathlib import Path
import bpy
from bl_ext.user_default.human_modeling import character_presets,geometry_quality,skin_relief

assert bpy.app.version[:2]==(5,2)
output=Path(__file__).resolve().parents[1]/'validation/corpulences-12'
active=bpy.context.view_layer.objects.active
bodies=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.get('human_modeling_body') and o.data.shape_keys and 'Morphologie' in o.data.shape_keys.key_blocks]
records=[]
for body in bodies:
    bpy.context.view_layer.objects.active=body
    before=character_presets.capture(body)
    if body.data.get('human_modeling_schema',0)<7:
        assert bpy.ops.human_modeling.add_proportions()=={'FINISHED'}
    body.data.shape_keys.update_tag();bpy.context.view_layer.update()
    assert character_presets.capture(body)==before
    assert body.modifiers.get(skin_relief.NAME)
    assert all(d.is_valid for d in body.animation_data.drivers)
    report=geometry_quality.report(body,bpy.context,include_eyes=True)
    records.append({'body':body.name,'schema':body.data['human_modeling_schema'],'settings_preserved':True,
                    'geometry':report['geometry'],'eye_fit':report['eye_fit'],'packed_texture':bool(body.modifiers[skin_relief.NAME].texture.image.packed_file)})
bpy.context.view_layer.objects.active=active
(output/'session-migration.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
destination=output/'Session-modelisation-12.blend'
if destination.exists():destination=destination.with_stem(destination.stem+'-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
if bpy.context.area:bpy.context.area.type='VIEW_3D'
def save_checkpoint():
    bpy.ops.wm.save_as_mainfile(filepath=str(destination),compress=True)
    return None
bpy.app.timers.register(save_checkpoint,first_interval=.5)
print('Corpulences 0.12 disponibles ; reglages conserves.')

