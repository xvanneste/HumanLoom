"""Prove neutral preservation and retention of released nonadult controls."""
from pathlib import Path
import sys,json
import bpy,numpy as np
root=Path(__file__).resolve().parents[1]
def load(path):
    with bpy.data.libraries.load(str(path),link=False) as (_,t):t.collections=['Realistic Human Base']
    bpy.context.scene.collection.children.link(t.collections[0])
    obj=next(o for o in t.collections[0].objects if o.get('human_modeling_body'))
    for mod in obj.modifiers:mod.show_viewport=False
    return obj
current=load(root/'validation/muscles-regionaux-18/candidat-04.blend')
neutral=load(root/'validation/proportions-14/candidat-adulte-15.blend')
legacy=load(root/'validation/proportions-14/extension-13/data/realistic.blend')
def points(obj):
    obj.data.shape_keys.update_tag();bpy.context.view_layer.update();evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
    try:return np.array([v.co[:] for v in mesh.vertices])
    finally:evaluated.to_mesh_clear()
rows=[]
for sex in (0.,.5,1.):
    for obj in (current,neutral,legacy):obj.data.shape_keys.key_blocks['Morphologie'].value=sex
    for stage in (0.,.5,1.,1.5,2.,2.5,3.):
        for obj in (current,neutral):
            keys=obj.data.shape_keys;keys['human_modeling_age']=stage;keys['hm_whole_body']=0.;keys['hm_muscles']=0.
        error=float(abs(points(current)-points(neutral)).max());assert error<1e-6,error
        rows.append({'sex':sex,'stage':stage,'neutral_error_m':error})
    for stage in (0.,1.,3.):
        for bulk,muscle in ((-1.,-1.),(-1.,1.),(1.,-1.),(1.,1.)):
            for obj in (current,legacy):
                keys=obj.data.shape_keys;keys['human_modeling_age']=stage;keys['hm_whole_body']=bulk;keys['hm_muscles']=muscle
            error=float(abs(points(current)-points(legacy)).max());assert error<1e-6,(sex,stage,bulk,muscle,error)
            rows.append({'sex':sex,'stage':stage,'whole_body':bulk,'muscle':muscle,'legacy_error_m':error})
(root/'validation/muscles-regionaux-18/compatibilite-04.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print('REGIONAL_NEUTRAL_AND_LEGACY_COMPAT_PASS',len(rows),flush=True)
