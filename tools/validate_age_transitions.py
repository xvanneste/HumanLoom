"""Verify age/morphology transitions, UV identity and unchanged adult controls."""
import json
from pathlib import Path
import sys
import bpy
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'extension'))
import geometry_quality as qa

asset,previous,output=[Path(p).resolve() for p in sys.argv[sys.argv.index('--')+1:]]
bodies=[]
for path in (asset,previous):
    with bpy.data.libraries.load(str(path),link=False) as (_,t):t.collections=['Realistic Human Base']
    col=t.collections[0];bpy.context.scene.collection.children.link(col)
    obj=next(o for o in col.objects if o.get('human_modeling_body'))
    obj.modifiers.new('QA','SUBSURF').levels=1;bodies.append(obj)
    obj.modifiers.move(len(obj.modifiers)-1,0)
body,old=bodies;rows=[]
for sex in (0.,.5,1.):
    for obj in bodies:obj.data.shape_keys.key_blocks['Morphologie'].value=sex
    for stage in (0.,.5,1.,1.5,2.,2.5,3.):
        for obj in bodies:
            obj.data.shape_keys['human_modeling_age']=stage;obj.data.shape_keys.update_tag()
        bpy.context.view_layer.update()
        report=qa.report(body,bpy.context,include_eyes=True)
        geometry=report['geometry'];eyes=report['eye_fit']
        row={'sex':sex,'stage':stage,'crossings':geometry['intersections']['crossing_triangle_pairs'],
             'eye_crossings':[e['crossing_triangle_pairs'] for e in eyes['eyes']]}
        if stage<=2:
            row['unchanged_from_previous']=geometry['geometry_sha256']==qa.report(old,bpy.context,check_intersections=False)['geometry']['geometry_sha256']
            assert row['unchanged_from_previous'],row
        rows.append(row)
        print('TRANSITION',row,flush=True)
output.write_text(json.dumps(rows,indent=2),encoding='utf-8')
assert not [r for r in rows if r['crossings'] or any(r['eye_crossings'])]
print('TRANSITIONS_PASS',flush=True)
