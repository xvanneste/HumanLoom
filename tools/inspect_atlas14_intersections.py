from pathlib import Path
import sys
import bpy,numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from validate_age_dimensions import surface
from bl_ext.user_default.human_modeling import geometry_quality as qa
bpy.ops.human_modeling.create();b=bpy.context.object;k=b.data.shape_keys
k.key_blocks['Morphologie'].value=0.;k['hm_whole_body']=1.;k['hm_muscles']=1.
b.modifiers['Human Modeling · Surface'].levels=2;k.update_tag();bpy.context.view_layer.update()
p,f=surface(b);report=qa.intersections(p,f,triangle_budget=400000)
pairs=np.array(report['sample_triangle_pairs'],dtype=int)
if len(pairs):
    c=p[f[pairs.ravel()]].reshape(-1,3)
    print('COLLISION_REGION',c.min(0).tolist(),c.max(0).tolist(),c.mean(0).tolist(),flush=True)
print('COLLISION_COUNT',report['crossing_triangle_pairs'],flush=True)
