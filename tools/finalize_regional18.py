from pathlib import Path
import sys,json
import bpy
root=Path(__file__).resolve().parents[1]
source=root/'validation/muscles-regionaux-18/candidat-04.blend'
with bpy.data.libraries.load(str(source),link=False) as (_,t):t.collections=['Realistic Human Base']
col=t.collections[0];body=next(o for o in col.objects if o.get('human_modeling_body'))
body.data['human_modeling_schema']=9
body['hm_regional_muscles_version']='0.14.0'
if 'hm_regional_muscles_candidate' in body:del body['hm_regional_muscles_candidate']
body.data.shape_keys['hm_muscles']=0.
body.data.shape_keys['hm_whole_body']=0.
body.data.shape_keys['human_modeling_age']=2.
for mod in body.modifiers:mod.show_viewport=True
bpy.data.libraries.write(str(root/'extension/data/realistic.blend'),{col,body.data,*(o.data for o in body.children)},fake_user=True,compress=True)
print('REGIONAL18_ASSET_SCHEMA9_READY',flush=True)
