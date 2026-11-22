from pathlib import Path
import bpy,numpy as np
root=Path(__file__).resolve().parents[1]
with bpy.data.libraries.load(str(root/'tools/data/realistic.blend'),link=False) as (_,t):t.collections=['Realistic Human Base']
body=next(o for o in t.collections[0].objects if o.get('human_modeling_body'))
print('GROUPS',[g.name for g in body.vertex_groups],flush=True)
for name in ('Basis','Morphologie'):
    p=np.array([v.co[:] for v in body.data.shape_keys.key_blocks[name].data]);h=np.ptp(p[:,2])
    print(name,'height',h,'bounds',p.min(0),p.max(0),flush=True)
    for z in (.85,1.05,1.15,1.32,1.40):
        v=p[(np.abs(p[:,2]-z)<.012)&(p[:,0]>.10)]
        print('BAND',z,len(v),v.min(0).tolist() if len(v) else None,v.max(0).tolist() if len(v) else None,flush=True)
