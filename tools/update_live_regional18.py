"""Reload the installed 5.2 update and migrate this scene after a saved copy."""
from pathlib import Path
import importlib,json,sys,tomllib
import bpy
assert bpy.app.version[:2]==(5,2)
root=Path(__file__).resolve().parents[1];out=root/'validation/muscles-regionaux-18'
original_scene=bpy.data.filepath
bpy.ops.wm.save_as_mainfile(filepath=str(out/'Session-avant-0.14.blend'),copy=True,compress=True)
package='bl_ext.user_default.human_modeling';addon=importlib.import_module(package);addon.unregister()
for suffix in ('proportions','anatomy','landmark_sets','measurements','character_presets','geometry_quality','surface_fix','body_profiles','age_shapes','skin_relief','muscle_upgrade'):
    name=package+'.'+suffix
    if name in sys.modules:importlib.reload(sys.modules[name])
    else:importlib.import_module(name)
addon=importlib.reload(addon);addon.register()
active=bpy.context.view_layer.objects.active;selected=list(bpy.context.selected_objects);rows=[]
for obj in tuple(bpy.context.scene.objects):
    if obj.type!='MESH' or not obj.get('human_modeling_body') or not obj.data.shape_keys:continue
    if obj.data.get('human_modeling_schema',0)>=9:continue
    before=addon.character_presets.capture(obj)
    with bpy.context.temp_override(object=obj,active_object=obj,selected_objects=[obj],selected_editable_objects=[obj]):
        result=bpy.ops.human_modeling.add_proportions()
    assert result=={'FINISHED'},(obj.name,result)
    assert addon.character_presets.capture(obj)==before
    rows.append({'name':obj.name,'schema':obj.data.get('human_modeling_schema'),'settings_preserved':True})
bpy.context.view_layer.objects.active=active
for obj in bpy.context.scene.objects:obj.select_set(obj in selected)
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(out/'Session-modelisation-14.blend'),compress=True)
version=tomllib.loads((Path(addon.__file__).parent/'blender_manifest.toml').read_text(encoding='utf-8'))['version']
(out/'session-installee-0.14.json').write_text(json.dumps({'blender':bpy.app.version_string,'extension_version':version,'module':addon.__file__,'previous_scene':original_scene,'scene':bpy.data.filepath,'upgraded':rows},indent=2),encoding='utf-8')
print('HUMAN_MODELING_LIVE_014_READY',version,len(rows))
