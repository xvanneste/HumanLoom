"""Validate dense native interpolation and independence from object transforms."""
from pathlib import Path
import sys,json
import bpy,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
import hair_prototype20 as h20

bpy.ops.wm.open_mainfile(filepath=str(h20.OUT/'Prototype-cheveux-01.blend'))
body=next(o for o in bpy.context.scene.objects if o.get('human_modeling_body'))
hair=next(o for o in bpy.context.scene.objects if o.get('hm_hair_prototype'))
keys=body.data.shape_keys
source=np.array([p.position[:] for p in hair.data.points])
assert not bpy.data.libraries, 'Prototype must keep native node groups locally'
assert all(d.is_valid for d in keys.animation_data.drivers)
body.modifiers['Prototype · surface'].levels=2
rows=[]
reference_uv=None
for morph in (0.,.5,1.):
    for age in (0.,1.,2.,3.):
        keys.key_blocks['Morphologie'].value=morph
        keys['human_modeling_age']=age
        keys.update_tag()
        body.update_tag()
        points=h20.evaluated_points(hair).reshape((-1,8,3))
        assert len(points)>850 and np.isfinite(points).all()
        graph=bpy.context.evaluated_depsgraph_get()
        dense=hair.evaluated_get(graph).data
        uv=np.array([v.vector[:] for v in dense.attributes['surface_uv_coordinate'].data])
        if reference_uv is None:reference_uv=uv.copy()
        else:assert np.array_equal(reference_uv,uv), 'Morph changed root identities'
        evaluated=body.evaluated_get(graph)
        mesh=evaluated.to_mesh()
        try:
            bvh=BVHTree.FromPolygons([v.co[:] for v in mesh.vertices],[p.vertices[:] for p in mesh.polygons])
            distances=np.array([bvh.find_nearest(Vector(p))[3] for p in points[:,0]])
        finally:evaluated.to_mesh_clear()
        assert distances.max()<.001,(morph,age,distances.max())
        assert np.max(np.linalg.norm(points[:,-1]-points[:,0],axis=1))<.08
        rows.append({'morph':morph,'age_step':age,'subdivision':2,'viewport_strands':len(points),'max_root_distance_m':float(distances.max())})
        print('DENSE_HAIR20_CASE',rows[-1],flush=True)

keys.key_blocks['Morphologie'].value=0.
keys['human_modeling_age']=2.
keys.update_tag()
baseline=h20.evaluated_points(hair)
body.location=(1.4,-.4,.2)
body.rotation_euler=(0.,.3,.7)
body.scale=(1.15,1.15,1.15)
body.update_tag()
transformed=h20.evaluated_points(hair)
assert np.allclose(baseline,transformed,atol=2e-6), 'Parent transform changed local grooming'
assert np.allclose(np.array(body.matrix_world),np.array(hair.matrix_world),atol=1e-6)

profile=hair.modifiers['Prototype · épaisseur']
h20.set_input(profile,'Radius',.00015)
hair.update_tag();bpy.context.view_layer.update()
radius=np.array([v.value for v in hair.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.attributes['radius'].data])
assert radius.max()>.00014
assert np.allclose(transformed,h20.evaluated_points(hair),atol=2e-6)
h20.set_input(profile,'Radius',.000075)
hair.update_tag();bpy.context.view_layer.update()
radius_restored=np.array([v.value for v in hair.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.attributes['radius'].data])
assert radius_restored.max()<.000076
assert np.array_equal(source,np.array([p.position[:] for p in hair.data.points]))

report={'reopened':True,'native_groups_local':True,'dense_root_uv_unchanged_across_morphs':True,'parent_transform_preserved':True,'thickness_control_preserves_positions':True,'source_guides_unchanged':True,'cases':rows}
(h20.OUT/'validation-densite-01.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('DENSE_HAIR20_PASS',len(rows),flush=True)
