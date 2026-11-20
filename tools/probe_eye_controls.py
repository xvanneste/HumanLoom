"""Compare socket fit while changing the head and eyelids."""
import json
from pathlib import Path
import sys
import bpy
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from validate_age_dimensions import surface
from validate_age_eye_fit import crossings
asset,output=[Path(p).resolve() for p in sys.argv[sys.argv.index('--')+1:]]
with bpy.data.libraries.load(str(asset),link=False) as (_,t):t.collections=['Realistic Human Base']
col=t.collections[0];bpy.context.scene.collection.children.link(col)
body=next(o for o in col.objects if o.get('human_modeling_body'))
body.modifiers.new('QA','SUBSURF').levels=1
keys=body.data.shape_keys;rows=[]
controls=['head_width','head_height','eye_spacing','eye_height','eyelid_aperture','facial_asymmetry']
for sex,stage in ((0,0),(1,3),(0,2),(1,1)):
    keys.key_blocks['Morphologie'].value=float(sex);keys['human_modeling_age']=float(stage)
    for label in ['neutral']+controls:
        for amount in ((0.,) if label=='neutral' else (-1.,1.)):
            for name in controls:keys['hm_'+name]=amount if name==label else 0.
            keys.update_tag();bpy.context.view_layer.update();bp,bf=surface(body)
            counts=[]
            for eye in body.children:
                ep,ef=surface(eye);center=(ep.max(axis=0)+ep.min(axis=0))/2
                proposed=(ep-center)*.92+center+np.array((0,-.0015,0))
                counts.append(crossings(bp,bf,proposed,ef)['crossing_pairs'])
            rows.append({'sex':sex,'stage':stage,'control':label,'amount':amount,'crossings':counts})
            print('EYE_PROBE',sex,stage,label,amount,counts,flush=True)
output.write_text(json.dumps(rows,indent=2),encoding='utf-8')
