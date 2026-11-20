"""Measure body-volume range and test extremes/combinations across reference ages."""
import json
from pathlib import Path
import sys
import bpy
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from validate_age_dimensions import surface


def main():
    from bl_ext.user_default.human_modeling import geometry_quality as qa,anatomy,character_presets
    output=Path(sys.argv[sys.argv.index('--')+1]).resolve()
    bpy.ops.human_modeling.create();body=bpy.context.object;keys=body.data.shape_keys
    rows=[]
    for sex in (0.,.5,1.):
        keys.key_blocks['Morphologie'].value=sex
        for stage in (0.,1.,2.,3.):
            keys['human_modeling_age']=stage
            values=[]
            for amount in (-1.,-.5,0.,.5,1.):
                keys['hm_body_mass']=amount;keys.update_tag();bpy.context.view_layer.update()
                points,faces=surface(body)
                triangles=points[faces]
                volume=abs(float(np.einsum('ij,ij->i',triangles[:,0],np.cross(triangles[:,1],triangles[:,2])).sum()/6))
                level=float(points[:,2].min()+np.ptp(points[:,2])*.60)
                loops,actual=anatomy.section_loops(points,faces,level)
                central=[loop for loop in loops if anatomy.encloses_axis(loop)]
                assert len(central)==1,(sex,stage,amount,len(central))
                loop=central[0]
                circumference=float(np.linalg.norm(loop-np.roll(loop,1,axis=0),axis=1).sum())
                report=qa.report(body,bpy.context,include_eyes=True)
                row={'sex':sex,'stage':stage,'body_mass':amount,'volume_liters':volume*1000,
                     'section_60percent_cm':circumference*100,'section_level_m':actual,
                     'crossings':report['geometry']['intersections'].get('crossing_triangle_pairs'),
                     'eye_crossings':[e['crossing_triangle_pairs'] for e in report['eye_fit']['eyes']]}
                rows.append(row);values.append(volume)
                print('BODY_RANGE',sex,stage,amount,row['volume_liters'],row['section_60percent_cm'],row['crossings'],flush=True)
            assert np.all(np.diff(values)>0),(sex,stage,values)
            for mass,fat,muscle in ((1.,1.,1.),(1.,1.,-1.),(-1.,-1.,-1.)):
                keys['hm_body_mass']=mass;keys['hm_adiposity']=fat;keys['hm_corpulence']=fat;keys['hm_muscles']=muscle
                keys.update_tag();bpy.context.view_layer.update()
                report=qa.report(body,bpy.context,include_eyes=True)
                rows.append({'sex':sex,'stage':stage,'combination':[mass,fat,muscle],
                    'crossings':report['geometry']['intersections'].get('crossing_triangle_pairs'),
                    'regions':report['geometry']['intersections'].get('approximate_regions'),
                    'eye_crossings':[e['crossing_triangle_pairs'] for e in report['eye_fit']['eyes']]})
            for name in ('body_mass','adiposity','corpulence','muscles'):keys['hm_'+name]=0.
    output.write_text(json.dumps({'cases':rows,'scope':'Geometric envelope volume and section at relative height .60. Not body weight, body fat percentage or standardized clinical waist measurement.'},indent=2),encoding='utf-8')
    failures=[r for r in rows if r['crossings'] or any(r['eye_crossings'])]
    print('EXTENDED_RANGE_DONE',len(rows),'failures',failures,flush=True)
    assert not failures


if __name__=='__main__':main()
