from pathlib import Path
import sys,json
import bpy,numpy as np
root=Path(__file__).resolve().parents[1]
from bl_ext.user_default.human_modeling import character_presets,add_smooth_preview
bpy.ops.human_modeling.create();fresh=bpy.context.object
with bpy.data.libraries.load(str(root/'validation/proportions-14/extension-13/data/realistic.blend'),link=False) as (_,t):t.collections=['Realistic Human Base']
bpy.context.scene.collection.children.link(t.collections[0]);old=next(o for o in t.collections[0].objects if o.get('human_modeling_body'))
add_smooth_preview(old)
old.data.shape_keys['hm_nose_width']=.35;old.data.shape_keys['hm_muscles_arms']=.4
old.data.shape_keys['hm_muscles']=.6;old.data.shape_keys['hm_whole_body']=.2
before=character_presets.capture(old)
for obj in tuple(bpy.context.selected_objects):obj.select_set(False)
old.select_set(True);bpy.context.view_layer.objects.active=old
assert bpy.ops.human_modeling.add_proportions()=={'FINISHED'}
assert old.data['human_modeling_schema']==9
assert character_presets.capture(old)==before
assert len(before['controls'])==48
def coords(obj):
    obj.data.shape_keys.update_tag();bpy.context.view_layer.update();evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
    try:return np.array([v.co[:] for v in mesh.vertices])
    finally:evaluated.to_mesh_clear()
rows=[]
for sex in (0.,.5,1.):
    for stage in (0.,1.,1.5,2.,2.5,3.):
        for obj in (old,fresh):
            keys=obj.data.shape_keys;keys.key_blocks['Morphologie'].value=sex;keys['human_modeling_age']=stage
            for name,value in before['controls'].items():keys['hm_'+name]=value
        a,b=coords(old),coords(fresh);error=float(abs(a-b).max())
        if error>=2e-6:
            different=[]
            for key in fresh.data.shape_keys.key_blocks:
                other=old.data.shape_keys.key_blocks.get(key.name)
                if other is None or abs(other.value-key.value)>1e-7:different.append((key.name,key.value,None if other is None else other.value))
            print('MIGRATION_DRIVER_DIFFERENCES',different,flush=True)
        assert error<2e-6,(sex,stage,error)
        rows.append({'sex':sex,'stage':stage,'upgraded_vs_new_maximum_error_m':error})
assert all(d.is_valid for d in old.data.shape_keys.animation_data.drivers)
out=root/'validation/muscles-regionaux-18';out.mkdir(exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'Migration-0.13-vers-0.14.blend'),compress=True)
old_name=old.name
bpy.ops.wm.open_mainfile(filepath=str(out/'Migration-0.13-vers-0.14.blend'))
upgraded=bpy.data.objects[old_name];assert upgraded.data.get('human_modeling_schema')==9
assert all(d.is_valid for d in upgraded.data.shape_keys.animation_data.drivers)
(out/'migration-0.14.json').write_text(json.dumps({'preset_preserved':True,'controls':48,'schema':9,'cases':rows,'reopen':'pass'},indent=2),encoding='utf-8')
print('REGIONAL_UPGRADE18_PASS',len(rows),flush=True)
