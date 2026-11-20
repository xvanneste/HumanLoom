import sys
from pathlib import Path
import bpy
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from validate_age_dimensions import surface
from bl_ext.user_default.human_modeling import geometry_quality as qa
bpy.ops.human_modeling.create();body=bpy.context.object;keys=body.data.shape_keys
body.modifiers['Human Modeling · Surface'].levels=2
keys.key_blocks['Morphologie'].value=0.
for amount in (-1.,0.,1.):
    keys['hm_body_mass']=amount;keys.update_tag();bpy.context.view_layer.update()
    p,f=surface(body);data=qa.intersections(p,f,triangle_budget=400000)
    pairs=np.array(data['sample_triangle_pairs'],dtype=int)
    if len(pairs):
        coords=p[f[pairs.ravel()]].reshape(-1,3)
        print('REGION',amount,'bounds',coords.min(0).tolist(),coords.max(0).tolist(),'center',coords.mean(0).tolist(),flush=True)
    print('INTERSECTIONS',amount,data,flush=True)
