"""Check extended body volumes at intermediate ages and morphology mixtures."""
import json
from pathlib import Path
import sys
import bpy


def main():
    from bl_ext.user_default.human_modeling import geometry_quality as qa
    output=Path(sys.argv[sys.argv.index('--')+1]).resolve()
    bpy.ops.human_modeling.create();body=bpy.context.object;keys=body.data.shape_keys
    records=[]
    for sex in (0.,.5,1.):
        keys.key_blocks['Morphologie'].value=sex
        for age in (.5,1.5,2.5):
            keys['human_modeling_age']=age
            for mass,fat in ((-1.,0.),(1.,0.),(1.,1.)):
                keys['hm_body_mass']=mass;keys['hm_adiposity']=fat;keys['hm_corpulence']=fat
                keys.update_tag();bpy.context.view_layer.update()
                data=qa.report(body,bpy.context,include_eyes=True)
                record={'sex':sex,'stage':age,'mass':mass,'fat':fat,
                        'crossings':data['geometry']['intersections'].get('crossing_triangle_pairs'),
                        'eye_crossings':[e['crossing_triangle_pairs'] for e in data['eye_fit']['eyes']]}
                records.append(record);print('MASS_TRANSITION',record,flush=True)
    output.write_text(json.dumps(records,indent=2),encoding='utf-8')
    assert not [r for r in records if r['crossings'] or any(r['eye_crossings'])]


if __name__=='__main__':main()
