"""Upgrade existing scene characters and save a sibling checkpoint in Blender 5.2."""
from datetime import datetime
import json
from pathlib import Path
import bpy
from bl_ext.user_default.human_modeling import character_presets,geometry_quality

assert bpy.app.version[:2]==(5,2)
root=Path(__file__).resolve().parents[1]
output=root/'validation/modelisation-10'
active=bpy.context.view_layer.objects.active
bodies=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.get('human_modeling_body') and o.data.shape_keys and 'Morphologie' in o.data.shape_keys.key_blocks]
records=[]
for body in bodies:
    bpy.context.view_layer.objects.active=body
    before=character_presets.capture(body)
    count=len(bpy.data.objects),len(bpy.data.meshes)
    if body.data.get('human_modeling_schema',0)<5:
        assert bpy.ops.human_modeling.add_proportions()=={'FINISHED'}
    body.data.shape_keys.update_tag();bpy.context.view_layer.update()
    assert character_presets.capture(body)==before
    assert count==(len(bpy.data.objects),len(bpy.data.meshes))
    assert all(d.is_valid for o in (body,*[c for c in body.children if c.type=='MESH' and c.data.shape_keys]) for d in o.data.shape_keys.animation_data.drivers)
    report=geometry_quality.report(body,bpy.context,include_eyes=True)
    records.append({'body':body.name,'schema':body.data['human_modeling_schema'],'settings_preserved':True,
        'geometry':report['geometry'],'eye_fit':report['eye_fit']})
bpy.context.view_layer.objects.active=active
(output/'session-migration.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
destination=output/'Session-modelisation-10.blend'
if destination.exists():destination=destination.with_stem(destination.stem+'-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
if bpy.context.area:bpy.context.area.type='VIEW_3D'
def save_checkpoint():
    bpy.ops.wm.save_as_mainfile(filepath=str(destination),compress=True)
    return None
bpy.app.timers.register(save_checkpoint,first_interval=.5)
print('Modelisation 0.10 disponible ; personnages et reglages conserves.')
