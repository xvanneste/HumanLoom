"""Check anchor attachment and modeling axes on both native endpoints."""
from pathlib import Path
import sys,json
import bpy,numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from build_surface_atlas15 import position
from experimental_growth_field import endpoint
from surface_frames15 import derive

root=Path(__file__).resolve().parents[1];folder=root/'validation/atlas-15'
atlas=json.loads((folder/'atlas-candidat-01.json').read_text(encoding='utf-8'))
with bpy.data.libraries.load(str(root/'validation/proportions-14/extension-13/data/realistic.blend'),link=False) as (_,t):
    t.collections=['Realistic Human Base']
body=next(o for o in t.collections[0].objects if o.get('human_modeling_body'))
body.data.calc_loop_triangles();faces=np.array([t.vertices[:] for t in body.data.loop_triangles])
reports=[]
for sex in (0,1):
    points=endpoint(body,sex);p={name:position(points,a) for name,a in atlas['anchors'].items()}
    for name,a in atlas['anchors'].items():
        w=np.array(a['barycentric']);assert abs(w.sum()-1)<1e-8 and w.min()>-1e-7,name
    for side in ('l','r'):
        assert abs(p['iliocristale_'+side][0])<abs(p['radiale_'+side][0])*.8,'Pelvic landmark hit arm'
        assert abs(p['trochanterion_'+side][0])<abs(p['stylion_'+side][0])*.8,'Trochanter landmark hit wrist'
        assert p['acromion_'+side][2]>p['radiale_'+side][2]>p['stylion_'+side][2]
        assert p['iliocristale_'+side][2]>p['trochanterion_'+side][2]>p['midpatella_'+side][2]>p['lateral_malleolus_'+side][2]
    joints,report=derive(points,faces,atlas);report['sex']=sex
    report['landmark_positions_m']={k:v.tolist() for k,v in p.items()}
    reports.append(report)
(folder/'controle-axes-01.json').write_text(json.dumps({'technical_checks':'pass','anatomical_status':'Visual surface approximations; not clinical validation','endpoints':reports},indent=2),encoding='utf-8')
print('SURFACE_ATLAS_TECHNICAL_CHECKS_PASS',len(reports),flush=True)
