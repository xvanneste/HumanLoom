"""Prove that only senior keys changed after the full non-senior matrix."""
import hashlib
import json
from pathlib import Path
import sys
import bpy
import numpy as np
paths=[Path(p).resolve() for p in sys.argv[sys.argv.index('--')+1:]]
snapshots=[]
for path in paths[:2]:
    with bpy.data.libraries.load(str(path),link=False) as (_,t):t.collections=['Realistic Human Base']
    col=t.collections[0]
    body=next(o for o in col.objects if o.get('human_modeling_body'))
    result={}
    for index,obj in enumerate((body,*sorted(body.children,key=lambda o:o.data.shape_keys.key_blocks[0].data[0].co.x))):
        keys=obj.data.shape_keys
        for key in keys.key_blocks:
            if 'Senior' in key.name:continue
            data=np.empty(len(key.data)*3);key.data.foreach_get('co',data)
            driver=next((c.driver for c in keys.animation_data.drivers if c.data_path==key.path_from_id('value')),None)
            result[str(index)+':'+key.name]=(hashlib.sha256(data.tobytes()).hexdigest(),driver.expression if driver else key.value)
    snapshots.append(result)
assert snapshots[0]==snapshots[1]
paths[2].write_text(json.dumps({'all_non_senior_keys_and_expressions_identical':True,'keys_compared':len(snapshots[0]),
    'source_assets':[str(p) for p in paths[:2]]},indent=2),encoding='utf-8')
print('NON_SENIOR_KEYS_IDENTICAL',len(snapshots[0]),flush=True)
