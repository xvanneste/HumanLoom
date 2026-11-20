"""Verify mathematical invariants, independently of Blender solver tuning."""
from pathlib import Path
import sys,json
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from hair_nature21 import nature,sample_rest,section_properties,RestFiber

out=Path(__file__).resolve().parents[1]/'validation/nature-cheveux-21'
out.mkdir(exist_ok=True)
rows=[]
for amount in np.linspace(0,1,21):
    f=nature(float(amount))
    p=sample_rest(f)
    edges=np.diff(p,axis=0)
    measured=np.linalg.norm(edges,axis=1).sum()
    assert np.isfinite(p).all() and np.array_equal(p[0],np.zeros(3))
    assert abs(measured/f.length_m-1)<.001
    usable=np.linspace(0,f.length_m,len(p))[1:-1] > f.root_straight_m+.001
    e1=edges[:-1][usable];e2=edges[1:][usable]
    k=2*np.linalg.norm(np.cross(e1,e2),axis=1)/(np.linalg.norm(e1,axis=1)*np.linalg.norm(e2,axis=1)*np.linalg.norm(e1+e2,axis=1))
    assert abs(np.median(k)-f.curvature_m_inv)<max(.05,f.curvature_m_inv*.002)
    mirror=sample_rest(nature(float(amount),handedness=-1.))
    assert np.allclose(p*np.array([-1,1,1]),mirror,atol=1e-11)
    rows.append({'nature':float(amount),'curvature_m_inv':f.curvature_m_inv,'material_twist_m_inv':f.material_twist_m_inv,'control_points':len(p),'contour_length_m':float(measured),'root_tip_distance_m':float(np.linalg.norm(p[-1])),'measured_median_curvature_m_inv':float(np.median(k))})

a=section_properties(70e-6,1.,3e9,.3,1300.)
b=section_properties(140e-6,1.,3e9,.3,1300.)
assert np.isclose(b['bending_rigidity_1_nm2']/a['bending_rigidity_1_nm2'],16)
assert np.isclose(b['mass_per_length_kg_m']/a['mass_per_length_kg_m'],4)
e=section_properties(70e-6,2.,3e9,.3,1300.)
assert np.isclose(e['area_m2'],a['area_m2'])
assert np.isclose(e['bending_rigidity_2_nm2']/e['bending_rigidity_1_nm2'],4)
for bad in (-.1,1.1,float('nan')):
    try:nature(bad)
    except ValueError:pass
    else:raise AssertionError('Invalid nature accepted')
report={'scope':'geometric and homogeneous rod math, not biological or XPBD calibration','nature_cases':rows,'diameter_scaling_pass':True,'ellipse_anisotropy_pass':True,'invalid_input_rejected':True}
(out/'validation-mathematique.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('NATURE21_MATH_PASS',len(rows),flush=True)
