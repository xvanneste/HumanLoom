from pathlib import Path
import sys,json
import bpy,numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
import hair_prototype20 as h20
from hair_nature21 import nature

out=h20.ROOT/'validation/nature-cheveux-21'
bpy.ops.wm.open_mainfile(filepath=str(out/'Prototype-nature-cheveux-02.blend'))
variants=[o for o in bpy.context.scene.objects if 'hm_hair_nature' in o]
assert len(variants)==5 and not bpy.data.libraries
rows=[]
for hair in variants:
    data=hair.data
    n=len(data.points)//len(data.curves)
    positions=np.array([p.position[:] for p in data.points]).reshape((-1,n,3))
    lengths=np.linalg.norm(np.diff(positions,axis=1),axis=2).sum(axis=1)
    expected=nature(hair['hm_hair_nature'])
    assert np.max(abs(lengths/expected.length_m-1))<.001
    curvature=np.array([p.value for p in data.attributes['hm_rest_curvature_m_inv'].data])
    assert np.allclose(curvature,expected.curvature_m_inv)
    assert np.isfinite(h20.evaluated_points(hair)).all()
    rows.append({'name':hair.name,'nature':hair['hm_hair_nature'],'guides':len(data.curves),'max_contour_error_fraction':float(np.max(abs(lengths/expected.length_m-1)))})
assert all(o.data.surface is variants[0].data.surface for o in variants)
assert sum(not o.hide_render for o in variants)==1
(out/'reouverture-natures.json').write_text(json.dumps({'variants':rows,'native_groups_local':True,'surface_preserved':True,'pass':True},indent=2),encoding='utf-8')
print('NATURE21_REOPEN_PASS',len(rows),flush=True)
