"""Technical horizontal sections, explicitly distinct from clinical girths."""
import sys
from pathlib import Path
import json
import bpy
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from validate_age_dimensions import surface
from bl_ext.user_default.human_modeling import anatomy

output=Path(sys.argv[sys.argv.index('--')+1]).resolve()
bpy.ops.human_modeling.create();body=bpy.context.object;keys=body.data.shape_keys
rows=[]
for sex in (0.,1.):
    keys.key_blocks['Morphologie'].value=sex
    for amount in (-1.,0.,1.):
        keys['hm_whole_body']=amount;keys.update_tag();bpy.context.view_layer.update()
        p,f=surface(body);height=np.ptp(p[:,2]);floor=p[:,2].min();values={}
        for region,relative,part in (('thorax',.76,'trunk'),('abdomen',.60,'trunk'),('bassin',.49,'trunk'),('bras',.70,'arm'),('avant_bras',.60,'arm'),('cuisse',.36,'leg'),('mollet',.18,'leg'),('cou',.865,'trunk')):
            loops,level=anatomy.section_loops(p,f,float(floor+height*relative))
            if part=='trunk':choices=[l for l in loops if anatomy.encloses_axis(l)]
            else:choices=[l for l in loops if l[:,0].mean()>height*(.10 if part=='arm' else .015)]
            assert choices,(region,sex,amount)
            loop=max(choices,key=lambda l:float(l[:,0].mean()) if part=='arm' else len(l))
            values[region]=float(np.linalg.norm(loop-np.roll(loop,1,axis=0),axis=1).sum()*100)
        rows.append({'sex':sex,'whole_body':amount,'perimeter_cm':values})
    subset=rows[-3:]
    for region in subset[0]['perimeter_cm']:
        sequence=[r['perimeter_cm'][region] for r in subset]
        assert sequence[0]<sequence[1]<sequence[2],(sex,region,sequence)
output.write_text(json.dumps({'scope':'Horizontal mesh-section perimeters at fixed relative heights, not standardized clinical circumferences or tissue composition. Arm sections are oblique to the limb axis.','cases':rows},indent=2),encoding='utf-8')
print('REGIONAL_SECTIONS_MONOTONIC_PASS',flush=True)
