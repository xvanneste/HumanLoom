"""Bounded all-age regression chunks; checkpoint every case for crash diagnosis."""
import hashlib
import json
from pathlib import Path
import sys
import bpy
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'extension'))
import geometry_quality
from proportions import CONTROLS
sys.path.insert(0,str(Path(__file__).resolve().parent))
from validate_age_dimensions import surface
from validate_age_eye_fit import crossings


def main():
    args=sys.argv[sys.argv.index('--')+1:]
    asset,output=[Path(p).resolve() for p in args[:2]]
    sex=float(args[2]); stage=float(args[3])
    with bpy.data.libraries.load(str(asset),link=False) as (_,t):t.collections=['Realistic Human Base']
    col=t.collections[0];bpy.context.scene.collection.children.link(col)
    body=next(o for o in col.objects if o.get('human_modeling_body'))
    body.modifiers.new('QA surface','SUBSURF').levels=1
    body.modifiers.move(len(body.modifiers)-1,0)
    keys=body.data.shape_keys;keys.key_blocks['Morphologie'].value=sex;keys['human_modeling_age']=stage
    records=[]
    def check(label, values, eye_test=False):
        for identifier,_ in CONTROLS:keys['hm_'+identifier]=values.get(identifier,0.)
        keys.update_tag();bpy.context.view_layer.update()
        data=geometry_quality.report(body,bpy.context)['geometry']
        record={'label':label,'settings':values,'crossings':data['intersections'].get('crossing_triangle_pairs'),
                'zero_area_faces':data['zero_area_faces'],'non_manifold_edges':data['non_manifold_edges']}
        if eye_test:
            bp,bf=surface(body)
            record['eye_crossings']=[crossings(bp,bf,*surface(eye))['crossing_pairs'] for eye in body.children]
        records.append(record)
        output.write_text(json.dumps({'sex':sex,'stage':stage,'cases':records},indent=2),encoding='utf-8')
        print('CASE',sex,stage,label,record['crossings'],record.get('eye_crossings'),flush=True)
    check('neutral',{},True)
    for identifier,_ in CONTROLS:
        for amount in (-1.,1.):
            check(identifier+str(amount),{identifier:amount},identifier in {'head_width','head_height','eye_spacing','eye_height','eyelid_aperture','facial_asymmetry','adiposity','fat_face'})
    for fat in (-1.,1.):
        for muscle in (-1.,1.):
            check('fat/muscle',{'corpulence':fat,'adiposity':fat,'muscles':muscle,'muscle_definition':1.})
    rng=np.random.default_rng(1026)
    for i in range(8):
        check('combination-'+str(i),{identifier:float(rng.uniform(-.65,.65)) for identifier,_ in CONTROLS},True)
    failures=[r for r in records if r['crossings']!=0 or r['zero_area_faces']!=0 or r['non_manifold_edges']!=0 or any(r.get('eye_crossings',[]))]
    print('BATCH_DONE',len(records),'FAILURES',len(failures),flush=True)
    assert not failures,failures


if __name__=='__main__':main()
