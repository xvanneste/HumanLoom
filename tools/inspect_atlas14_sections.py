import sys,json
from pathlib import Path
import bpy,numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from validate_age_dimensions import surface
from atlas_fit14 import perimeter
from bl_ext.user_default.human_modeling import anatomy
root=Path(__file__).resolve().parents[1]/'validation/proportions-14'
fit=json.loads((root/'candidat-adulte-07.fit.json').read_text(encoding='utf-8'))
row=next(r for r in fit['fits'] if r['sex']==1 and r['profile']=='fat')
bpy.ops.human_modeling.create();b=bpy.context.object;k=b.data.shape_keys
k.key_blocks['Morphologie'].value=1.;k['hm_whole_body']=1.;k['hm_muscles']=0.;k.update_tag();bpy.context.view_layer.update()
for level in (0,1,2):
    b.modifiers['Human Modeling · Surface'].levels=level;bpy.context.view_layer.update()
    p,f=surface(b);loops,_=anatomy.section_loops(p,f,row['levels']['chest'])
    print('SECTION_TOPOLOGY',level,row['levels']['chest'],[(len(l),l.mean(0).tolist(),perimeter(l),anatomy.encloses_axis(l)) for l in loops],flush=True)
