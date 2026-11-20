"""Age presets, published stature fits, UV identity, migration and persistence."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import bpy
import numpy as np


def main():
    from bl_ext.user_default.human_modeling import age_shapes,character_presets as presets,geometry_quality as qa,measurements
    from bl_ext.user_default.human_modeling.proportions import CONTROLS,CURRENT_SCHEMA
    old_asset,output=[Path(p).resolve() for p in sys.argv[sys.argv.index('--')+1:]]
    bpy.ops.human_modeling.create();body=bpy.context.object;keys=body.data.shape_keys
    initial=presets.capture(body);records=[]
    from bl_ext.user_default.human_modeling import body_profiles
    for identifier in body_profiles.PROFILES:
        keys['hm_nose_width']=.2
        assert bpy.ops.human_modeling.body_profile(profile=identifier)=={'FINISHED'}
        assert keys['hm_nose_width']==.2
        keys.update_tag();bpy.context.view_layer.update()
        assert qa.report(body,bpy.context)['geometry']['intersections']['crossing_triangle_pairs']==0,identifier
    presets.apply(body,initial)
    for sex in ('F','M'):
        keys.key_blocks['Morphologie'].value=0. if sex=='F' else 1.
        for stage in range(4):
            body.scale=(1.,1.,1.)
            assert bpy.ops.human_modeling.age_reference(stage=stage)=={'FINISHED'}
            bpy.context.view_layer.update()
            ref=age_shapes.stature_reference(body,sex)
            assert bpy.ops.human_modeling.calibrate_age_height(sex=sex)=={'FINISHED'}
            bpy.context.view_layer.update()
            measured=measurements.measure(body,bpy.context)['height_m']
            assert abs(measured-ref['height_cm']/100)<1e-5,(stage,sex,measured)
            records.append({'sex':sex,'stage':stage,'measured_m':measured,'reference':ref})
    # Interpolated stages must not pretend to have a published chronological norm.
    keys['human_modeling_age']=.5
    try:age_shapes.stature_reference(body,'F')
    except ValueError:pass
    else:raise AssertionError('Interpolated age accepted as published reference')
    state=presets.capture(body)
    path=output/'age-et-volumes.json';presets.write(path,state)
    keys['human_modeling_age']=2.
    presets.apply(body,presets.read(path));assert presets.capture(body)==state
    old_json=copy.deepcopy(initial);old_json.pop('age_stage')
    assert presets.validate(old_json)['age_stage']==2.
    for bad in (True,4.,-1.,float('nan')):
        invalid=copy.deepcopy(initial);invalid['age_stage']=bad
        try:presets.validate(invalid)
        except ValueError:pass
        else:raise AssertionError('Invalid age accepted')
    presets.apply(body,initial)
    with bpy.data.libraries.load(str(old_asset),link=False) as (_,t):t.collections=['Realistic Human Base']
    col=t.collections[0];bpy.context.scene.collection.children.link(col)
    old=next(o for o in col.objects if o.get('human_modeling_body'))
    def uv(mesh):
        values=np.empty(len(mesh.uv_layers.active.data)*2)
        mesh.uv_layers.active.data.foreach_get('uv',values)
        return values
    assert np.array_equal(uv(old.data),uv(body.data))
    assert len(old.data.vertices)==len(body.data.vertices)
    assert [p.vertices[:] for p in old.data.polygons]==[p.vertices[:] for p in body.data.polygons]
    old.data.shape_keys['hm_waist']=.25
    before=presets.capture(old)
    bpy.context.view_layer.objects.active=old
    count=len(bpy.data.objects),len(bpy.data.meshes)
    assert bpy.ops.human_modeling.add_proportions()=={'FINISHED'}
    old.data.shape_keys.update_tag();bpy.context.view_layer.update()
    assert count==(len(bpy.data.objects),len(bpy.data.meshes))
    assert presets.capture(old)==before
    assert old.data['human_modeling_schema']==CURRENT_SCHEMA
    assert all(d.is_valid for o in (old,*old.children) if o.data.shape_keys for d in o.data.shape_keys.animation_data.drivers)
    bpy.ops.human_modeling.age_reference(stage=1)
    old.data.shape_keys['hm_adiposity']=.7
    old.data.shape_keys['hm_facial_asymmetry']=.3
    old.data.shape_keys.update_tag();bpy.context.view_layer.update()
    before=presets.capture(old);name=old.name
    file=output/'Modelisation-10-verifiee.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(file),compress=True)
    bpy.ops.wm.open_mainfile(filepath=str(file))
    old=bpy.data.objects[name];bpy.context.view_layer.update()
    assert presets.capture(old)==before
    assert all(d.is_valid for o in (old,*old.children) if o.data.shape_keys for d in o.data.shape_keys.animation_data.drivers)
    (output/'validation-workflow.json').write_text(json.dumps({'calibrated_statures':records,'controls':len(CONTROLS),
        'uv_sha256':hashlib.sha256(uv(old.data).astype('<f8').tobytes()).hexdigest(),
        'uv_and_topology_preserved':True,'age_presets':True,'legacy_migration':True,'reopen':True},indent=2),encoding='utf-8')
    print('MODELING_WORKFLOW_PASS',flush=True)


if __name__=='__main__':main()
