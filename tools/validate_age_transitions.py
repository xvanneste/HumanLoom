"""Verify age/morphology transitions, no crossings and a neutral shape equal to the frozen reference of the current asset (D-19).

Reference: tools/data/neutral_reference.json (tools/make_neutral_reference.py)."""
import json
from pathlib import Path
import sys
import bpy
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'extension'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
import geometry_quality as qa
import neutral_reference as neutral

asset,output=[Path(p).resolve() for p in sys.argv[sys.argv.index('--')+1:]]
reference=neutral.load()
with bpy.data.libraries.load(str(asset),link=False) as (_,t):t.collections=['Realistic Human Base']
col=t.collections[0];bpy.context.scene.collection.children.link(col)
body=next(o for o in col.objects if o.get('human_modeling_body'))
body.modifiers.new('QA','SUBSURF').levels=1
body.modifiers.move(len(body.modifiers)-1,0)
rows=[]
for sex in (0.,.5,1.):
    for stage in (0.,.5,1.,1.5,2.,2.5,3.):
        neutral.set_state(body,sex,stage)
        bpy.context.view_layer.update()
        report=qa.report(body,bpy.context,include_eyes=True)
        geometry=report['geometry'];eyes=report['eye_fit']
        row={'sex':sex,'stage':stage,'crossings':geometry['intersections']['crossing_triangle_pairs'],
             'eye_crossings':[e['crossing_triangle_pairs'] for e in eyes['eyes']]}
        row['max_difference_to_reference_m']=neutral.check(body,reference,sex,stage)
        rows.append(row)
        print('TRANSITION',row,flush=True)
output.write_text(json.dumps(rows,indent=2),encoding='utf-8')
assert not [r for r in rows if r['crossings'] or any(r['eye_crossings'])]
print('TRANSITIONS_PASS',flush=True)
