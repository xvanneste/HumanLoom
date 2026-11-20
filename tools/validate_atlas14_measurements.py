"""Numerical fit on the evaluated render surface, separate from anatomical QA."""
import sys,json
from pathlib import Path
import bpy,numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from validate_age_dimensions import surface
from atlas_fit14 import section,perimeter
from semantic_torso14 import tagged,measure
from experimental_growth_field import endpoint
from bl_ext.user_default.human_modeling import anatomy

root=Path(__file__).resolve().parents[1]/'validation/proportions-14'
version=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else '07'
fit_data=json.loads((root/f'candidat-adulte-{version}.fit.json').read_text(encoding='utf-8'))
bpy.ops.human_modeling.create();body=bpy.context.object;keys=body.data.shape_keys
body.modifiers['Human Modeling · Surface'].levels=2;rows=[]
for sex in (0,1):
    keys.key_blocks['Morphologie'].value=sex
    for name,value in (('thin',-1.),('reference',0.),('fat',1.)):
        keys['hm_whole_body']=value;keys['hm_muscles']=0.;keys.update_tag();bpy.context.view_layer.update()
        record=next(r for r in fit_data['fits'] if r['sex']==sex and r.get('profile')==name)
        points,faces=surface(body);actual={n:perimeter(section(points,faces,record['levels'][n],anatomy)) for n in record['targets_m']}
        unsegmented=actual['chest']
        with tagged(body,endpoint(body,sex),record['levels']['chest'],anatomy) as tag:
            actual['chest']=measure(body,record['levels']['chest'],tag)
        error={n:actual[n]/target-1 for n,target in record['targets_m'].items()}
        rows.append({'sex':sex,'profile':name,'targets_m':record['targets_m'],'evaluated_m':actual,'relative_error':error,'unsegmented_chest_m':unsegmented})
        assert max(map(abs,error.values()))<.015,(sex,name,error)
(root/f'mesures-surface-{version}.json').write_text(json.dumps({'scope':'Numerical contour targets at provisional native levels; no claim of clinical anatomical equivalence. Technical tolerance 1.5 percent at subdivision two.','cases':rows},indent=2),encoding='utf-8')
print('ATLAS_EVALUATED_TARGETS_PASS',flush=True)
