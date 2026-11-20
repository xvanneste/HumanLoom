"""Check native hair following on saved editable bodies, without changing the file."""
from pathlib import Path
import sys, json, hashlib
import bpy, numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0, str(Path(__file__).resolve().parent))
import hair_prototype20 as hair20

bpy.ops.wm.open_mainfile(filepath=str(hair20.OUT/'Prototype-cheveux-01.blend'))
body = next(obj for obj in bpy.context.scene.objects if obj.get('human_modeling_body'))
hair = next(obj for obj in bpy.context.scene.objects if obj.get('hm_hair_prototype'))
hair.modifiers['Prototype · densité'].show_viewport = False
keys = body.data.shape_keys
original = np.array([p.position[:] for p in hair.data.points])
guide_hash = hashlib.sha256(original.tobytes()).hexdigest()
reference = hair20.evaluated_points(hair).reshape((-1,8,3))[:,0].copy()
rows = []
for morph in (0., .5, 1.):
    for age in (0., 1., 2., 3.):
        for subdivision in (0, 1, 2):
            keys.key_blocks['Morphologie'].value = morph
            keys['human_modeling_age'] = age
            keys.update_tag()
            body.modifiers['Prototype · surface'].levels = subdivision
            body.update_tag()
            bpy.context.view_layer.update()
            points = hair20.evaluated_points(hair).reshape((-1,8,3))
            assert np.isfinite(points).all()
            assert points.shape == (850,8,3)
            graph = bpy.context.evaluated_depsgraph_get()
            evaluated = body.evaluated_get(graph)
            mesh = evaluated.to_mesh()
            try:
                bvh = BVHTree.FromPolygons([v.co[:] for v in mesh.vertices],[p.vertices[:] for p in mesh.polygons])
                distances = np.array([bvh.find_nearest(Vector(point))[3] for point in points[:,0]])
                signed = []
                for point in points[:,1:].reshape((-1,3)):
                    hit, normal, _, distance = bvh.find_nearest(Vector(point))
                    if distance > .001 and (Vector(point)-hit).dot(normal) < 0:
                        signed.append(distance)
            finally:
                evaluated.to_mesh_clear()
            rows.append({'morph':morph,'age_step':age,'subdivision':subdivision,'root_max_distance_m':float(distances.max()),'root_p95_distance_m':float(np.percentile(distances,95)),'points_inside_beyond_1mm':len(signed),'max_root_movement_m':float(np.linalg.norm(points[:,0]-reference,axis=1).max())})
            print('HAIR20_CASE',rows[-1],flush=True)
assert np.array_equal(original,np.array([p.position[:] for p in hair.data.points]))
assert not body.particle_systems and not hair.particle_systems
assert all(row['root_max_distance_m'] < .001 for row in rows), 'Hair attachment exceeds 1 mm'
assert max(row['max_root_movement_m'] for row in rows) > .3, 'The hair must follow the age shapes'
keys.key_blocks['Morphologie'].value = 0.
keys['human_modeling_age'] = 2.
body.modifiers['Prototype · surface'].levels = 1
keys.update_tag()
hair.modifiers['Prototype · densité'].show_viewport = True
dense = hair20.evaluated_points(hair)
assert len(dense) > len(original)
assert np.ptp(dense[:,2]) < .35, 'Unbounded strand lengths after interpolation'
dense_count = len(dense)//8
hair20.set_input(hair.modifiers['Prototype · longueur'],'Length Factor',.5)
hair.update_tag()
shortened = hair20.evaluated_points(hair).reshape((-1,8,3))
full = dense.reshape((-1,8,3))
assert np.allclose(full[:,0],shortened[:,0],atol=2e-6)
ratio = np.linalg.norm(shortened[:,-1]-shortened[:,0],axis=1)/np.maximum(np.linalg.norm(full[:,-1]-full[:,0],axis=1),1e-9)
assert .48 < np.median(ratio) < .53
hair20.set_input(hair.modifiers['Prototype · longueur'],'Length Factor',1.)
hair.update_tag()
assert np.allclose(dense,hair20.evaluated_points(hair),atol=2e-6)
report={'blender':bpy.app.version_string,'source_guides_sha256':guide_hash,'guide_points_unchanged':True,'curves':850,'points_per_curve':8,'native_dynamics':True,'physics_simulation_tested':False,'cases':rows,'dense_viewport_curves':dense_count,'length_control_median_ratio':float(np.median(ratio)),'length_control_root_preservation':True,'dense_reproducible_after_reset':True}
(hair20.OUT/'validation-attache-01.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('HAIR20_VALIDATION_PASS',len(rows),flush=True)
