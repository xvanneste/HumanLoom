"""Offline checks at subdivision two, with an explicit larger triangle budget."""
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
    bpy.ops.human_modeling.create();body=bpy.context.object
    body.modifiers['Human Modeling · Surface'].levels=2
    keys=body.data.shape_keys;keys['human_modeling_age']=3.;keys['hm_skin_relief']=1.
    rows=[]
    for sex in (0.,.5,1.):
        keys.key_blocks['Morphologie'].value=sex;keys.update_tag();bpy.context.view_layer.update()
        for amount in (-1.,0.,1.):
            keys['hm_skin_relief']=amount;keys.update_tag();bpy.context.view_layer.update()
            points,faces=surface(body)
            result=qa.intersections(points,faces,triangle_budget=400000)
            eyes=[crossings(points,faces,*surface(eye))['crossing_pairs'] for eye in body.children]
            pairs=result.get('sample_triangle_pairs',[])
            centers=[points[faces[pair].reshape(-1)].mean(axis=0).tolist() for pair in pairs[:30]]
            row={'sex':sex,'relief':amount,'subdivision':2,'triangles':len(faces),'crossings':result.get('crossing_triangle_pairs'),
                 'eye_crossings':eyes,'offline_triangle_budget':400000,'regions':result.get('approximate_regions'),
                 'crossing_centers':centers}
            rows.append(row);print('RENDER_SURFACE',sex,amount,row['crossings'],row['regions'],flush=True)
        keys['hm_skin_relief']=1.
        for control in ('head_width','head_height','eye_spacing','eye_height','eyelid_aperture','facial_asymmetry'):
            for amount in (-1.,1.):
                keys['hm_'+control]=amount;keys.update_tag();bpy.context.view_layer.update()
                points,faces=surface(body)
                result=qa.intersections(points,faces,triangle_budget=400000)
                eyes=[crossings(points,faces,*surface(eye))['crossing_pairs'] for eye in body.children]
                row={'sex':sex,'control':control,'amount':amount,'subdivision':2,
                     'crossings':result.get('crossing_triangle_pairs'),'eye_crossings':eyes,'regions':result.get('approximate_regions')}
                rows.append(row);print('RENDER_CONTROL',row,flush=True)
            keys['hm_'+control]=0.
    output.write_text(json.dumps(rows,indent=2),encoding='utf-8')
    assert not [row for row in rows if row['crossings'] or any(row['eye_crossings'])]


if __name__=='__main__':main()
