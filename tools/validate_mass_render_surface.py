"""Offline subdivision-two validation of the new mass control."""
import json
from pathlib import Path
import sys
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
from validate_age_dimensions import surface
from validate_age_eye_fit import crossings


def main():
    from bl_ext.user_default.human_modeling import geometry_quality as qa
    output=Path(sys.argv[sys.argv.index('--')+1]).resolve()
    bpy.ops.human_modeling.create();body=bpy.context.object;keys=body.data.shape_keys
    body.modifiers['Human Modeling · Surface'].levels=2
    records=[]
    for sex in (0.,1.):
        keys.key_blocks['Morphologie'].value=sex
        for stage in (0.,1.,2.,3.):
            keys['human_modeling_age']=stage
            for mass,fat in ((-1.,0.),(1.,0.),(1.,1.)):
                keys['hm_body_mass']=mass;keys['hm_adiposity']=fat;keys['hm_corpulence']=fat
                keys.update_tag();bpy.context.view_layer.update()
                points,faces=surface(body)
                data=qa.intersections(points,faces,triangle_budget=400000)
                eyes=[crossings(points,faces,*surface(eye))['crossing_pairs'] for eye in body.children]
                record={'sex':sex,'stage':stage,'mass':mass,'fat':fat,'subdivision':2,
                        'crossings':data.get('crossing_triangle_pairs'),'eye_crossings':eyes}
                records.append(record);print('MASS_RENDER',record,flush=True)
    output.write_text(json.dumps(records,indent=2),encoding='utf-8')
    assert not [r for r in records if r['crossings'] or any(r['eye_crossings'])]


if __name__=='__main__':main()
