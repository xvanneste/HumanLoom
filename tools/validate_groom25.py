"""Integration checks in the actual Blender 5.2 runtime, with a portable scene."""
from pathlib import Path
import sys,json,time,hashlib
import bpy,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import extension as addon
from extension import groom
assert bpy.app.background and bpy.app.version[:2]==(5,2)
OUT=ROOT/'validation/groom-25';OUT.mkdir(parents=True,exist_ok=True)
addon.register()
for o in tuple(bpy.context.scene.objects):bpy.data.objects.remove(o,do_unlink=True)
bpy.ops.human_modeling.create();body=bpy.context.object
body.modifiers['Human Modeling · Surface'].levels=2
source=np.array([v.co[:] for v in body.data.vertices]);rows=[];hairs=[]
for region in groom.LABELS:
    cfg=groom.defaults(region);cfg['guides']=60;cfg['viewport']=.08
    start=time.perf_counter();hair=groom.build(body,region,cfg);hairs.append(hair)
    bpy.context.view_layer.update();ev=hair.evaluated_get(bpy.context.evaluated_depsgraph_get())
    count=len(ev.data.curves)
    assert count>0,region
    p=np.array([v.position[:] for v in ev.data.points]);assert np.isfinite(p).all()
    assert hair.data.surface==body and hair.parent==body
    assert sum(m.name.startswith('HumanLoom · suivi') for m in hair.modifiers)==1
    assert not hair.particle_systems
    rows.append({'region':region,'guides':len(hair.data.curves),'evaluated_curves':count,'points':len(p),'build_s':round(time.perf_counter()-start,3)})
    print('GROOM25_REGION',rows[-1],flush=True)
assert np.array_equal(source,np.array([v.co[:] for v in body.data.vertices]))
keys=body.data.shape_keys;cases=[]
# Disable interpolation to verify the actual source guide roots and source edits.
for h in hairs:h.modifiers['HumanLoom · densité'].show_viewport=False
original=[hashlib.sha256(np.array([v.position[:] for v in h.data.points]).tobytes()).hexdigest() for h in hairs]
for morph,age,bulk in ((0.,2.,0.),(1.,2.,0.),(.5,2.,1.),(0.,0.,0.),(1.,1.,-.8),(1.,3.,.8)):
    keys.key_blocks['Morphologie'].value=morph;keys['human_modeling_age']=age;keys['hm_whole_body']=bulk;keys.update_tag();body.update_tag();bpy.context.view_layer.update()
    deps=bpy.context.evaluated_depsgraph_get();ev=body.evaluated_get(deps);mesh=ev.to_mesh()
    bvh=BVHTree.FromPolygons([v.co[:] for v in mesh.vertices],[p.vertices[:] for p in mesh.polygons]);ev.to_mesh_clear()
    for hair in hairs:
        data=hair.evaluated_get(deps).data
        root=[data.points[c.first_point_index].position[:] for c in data.curves]
        distances=[bvh.find_nearest(Vector(p))[3] for p in root]
        assert max(distances)<.006,(hair.name,morph,age,max(distances))
        cases.append({'region':hair['hl_groom_region'],'morph':morph,'age':age,'bulk':bulk,'root_max_mm':max(distances)*1000})
    print('GROOM25_FOLLOW',morph,age,bulk,flush=True)
for h,digest in zip(hairs,original):assert hashlib.sha256(np.array([v.position[:] for v in h.data.points]).tobytes()).hexdigest()==digest
keys.key_blocks['Morphologie'].value=1.;keys['human_modeling_age']=2.;keys['hm_whole_body']=0.;keys.update_tag()
for hair in hairs:hair.modifiers['HumanLoom · densité'].show_viewport=True
# Idempotent replacement and invalid inputs without replacing an existing layer.
old=groom.find(body,'BROWS');cfg=groom.state(old.hl_groom);new=groom.build(body,'BROWS',cfg)
assert len([o for o in body.children if o.get('hl_groom_region')=='BROWS'])==1
try:groom.build(body,'BROWS',{**cfg,'nature':float('nan')})
except ValueError:pass
else:raise AssertionError('NaN accepted')
assert groom.find(body,'BROWS')==new
for nature in (0.,.25,.5,.75,1.):
    for length in (.003,.06,.30):
        p=groom.fiber(length,nature);contour=np.linalg.norm(np.diff(p,axis=0),axis=1).sum()
        assert abs(contour/length-1)<.003,(nature,length,contour)
report={'blender':bpy.app.version_string,'regions':rows,'follow_cases':cases,'source_geometry_unchanged':True,'editable_guides_preserved':True,'replacement_idempotent':True,'invalid_input_preserves_layer':True}
(OUT/'validation-integration.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
bpy.ops.object.make_local(type='ALL');bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'HumanLoom-groom-validation.blend'),compress=True)
print('GROOM25_PASS',len(rows),len(cases),flush=True)
