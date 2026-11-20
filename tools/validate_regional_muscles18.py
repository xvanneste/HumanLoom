"""Functional saturation and targeted regional/age-transition geometry checks."""
from pathlib import Path
import sys,json
import bpy,numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from regional_muscle_fields18 import REGIONS
from validate_age_dimensions import surface
from validate_age_eye_fit import crossings
from bl_ext.user_default.human_modeling import geometry_quality as qa

args=sys.argv[sys.argv.index('--')+1:];output=Path(args[0]).resolve();mode=args[1]
bpy.ops.human_modeling.create();body=bpy.context.object;keys=body.data.shape_keys
body.modifiers['Human Modeling · Surface'].levels=2;rows=[];behavior=[]
sexes=(float(args[2]),) if len(args)>2 else (0.,.5,1.)
if len(args)>2 and output.exists():
    previous=json.loads(output.read_text(encoding='utf-8'));rows=previous['cases'];behavior=previous['behavior']
# Evaluated coordinates are float32: additive cancelling keys can differ by
# one ULP even when the mathematical displacement is zero (observed 0.12 µm).
roundoff=8*np.finfo(np.float32).eps
def update():keys.update_tag();bpy.context.view_layer.update()
def reset():
    keys['hm_whole_body']=0.;keys['hm_muscles']=0.
    for r in REGIONS:keys['hm_muscles_'+r]=0.
def record(tag):
    update();p,f=surface(body);result=qa.intersections(p,f,triangle_budget=400000)
    eyes=[crossings(p,f,*surface(eye))['crossing_pairs'] for eye in body.children]
    row={**tag,'crossings':result['crossing_triangle_pairs'],'regions':result['approximate_regions'],'eye_crossings':eyes};rows.append(row)
    output.write_text(json.dumps({'cases':rows,'behavior':behavior},indent=2),encoding='utf-8');print('REGIONAL_QA',row,flush=True)
for sex in sexes:
    keys.key_blocks['Morphologie'].value=sex;reset();keys['human_modeling_age']=2.
    if mode=='regional':
        for overall in (-1.,1.):
            reset();keys['hm_muscles']=overall;update();base,_=surface(body)
            for r in REGIONS:keys['hm_muscles_'+r]=overall
            update();saturated,_=surface(body);error=float(abs(base-saturated).max());assert error<roundoff,error
            behavior.append({'sex':sex,'global':overall,'saturated_regional_error_m':error})
        reset();keys['hm_muscles']=1.
        for r in REGIONS:keys['hm_muscles_'+r]=-1.
        update();cancelled,_=surface(body);reset();update();neutral,_=surface(body)
        error=float(abs(cancelled-neutral).max());assert error<roundoff,error
        behavior.append({'sex':sex,'all_regions_cancel_global_error_m':error})
        for region in REGIONS:
            for amount in (-1.,1.):
                reset();keys['hm_muscles_'+region]=amount;record({'sex':sex,'stage':2.,'region':region,'amount':amount})
    elif mode=='transitions':
        for stage in (1.5,2.5):
            for bulk,muscle in ((-1.,-1.),(-1.,1.),(1.,-1.),(1.,1.)):
                reset();keys['human_modeling_age']=stage;keys['hm_whole_body']=bulk;keys['hm_muscles']=muscle
                record({'sex':sex,'stage':stage,'whole_body':bulk,'muscle':muscle})
    elif mode=='profiles':
        from bl_ext.user_default.human_modeling import body_profiles
        for identifier in body_profiles.PROFILES:
            assert bpy.ops.human_modeling.body_profile(profile=identifier)=={'FINISHED'}
            record({'sex':sex,'stage':2.,'profile':identifier})
    else:raise ValueError(mode)
failures=[r for r in rows if r['crossings'] or any(r['eye_crossings'])]
print('REGIONAL_QA_DONE',len(rows),'FAILURES',len(failures),flush=True)
assert not failures,failures
