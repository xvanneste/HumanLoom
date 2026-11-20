"""Validate reversible relief, UV/topology, age gating, packed data and migration."""
import json
from pathlib import Path
import sys
import bpy
import numpy as np


def main():
    from bl_ext.user_default.human_modeling import character_presets,geometry_quality,skin_relief
    old_asset,output=[Path(p).resolve() for p in sys.argv[sys.argv.index('--')+1:]]
    bpy.ops.human_modeling.create();body=bpy.context.object;keys=body.data.shape_keys
    def points():
        keys.update_tag();bpy.context.view_layer.update()
        evaluated=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
        result=np.array([v.co[:] for v in mesh.vertices]);evaluated.to_mesh_clear();return result
    assert body.modifiers[0].type=='SUBSURF'
    assert body.modifiers[1].name==skin_relief.NAME
    assert body.modifiers[1].texture.image.packed_file
    records=[]
    for sex in (0.,.5,1.):
        keys.key_blocks['Morphologie'].value=sex
        for age in (0.,1.,2.,2.5,3.):
            keys['human_modeling_age']=age;keys['hm_skin_relief']=-1.
            neutral=points()
            for amount in (0.,1.):
                keys['hm_skin_relief']=amount;active=points()
                maximum=float(np.linalg.norm(active-neutral,axis=1).max())
                if age<=2:assert maximum==0.
                else:assert 0.<maximum<.0025
                report=geometry_quality.report(body,bpy.context,include_eyes=True)
                assert report['geometry']['intersections']['crossing_triangle_pairs']==0,(sex,age,amount)
                assert not any(e['crossing_triangle_pairs'] for e in report['eye_fit']['eyes'])
                records.append({'sex':sex,'stage':age,'relief':amount,'max_displacement_m':maximum,'crossings':0,'eye_crossings':0})
    with bpy.data.libraries.load(str(old_asset),link=False) as (_,target):target.collections=['Realistic Human Base']
    col=target.collections[0];bpy.context.scene.collection.children.link(col)
    old=next(o for o in col.objects if o.get('human_modeling_body'))
    bpy.context.view_layer.objects.active=old
    before=character_presets.capture(old)
    old_coords=np.array([v.co[:] for v in old.data.shape_keys.key_blocks[0].data])
    assert bpy.ops.human_modeling.add_proportions()=={'FINISHED'}
    assert character_presets.capture(old)==before
    assert np.array_equal(old_coords,np.array([v.co[:] for v in old.data.shape_keys.key_blocks[0].data]))
    assert old.modifiers.get(skin_relief.NAME)
    # Texture/image and strength drivers must remain valid after removing the import source.
    old.data.shape_keys['human_modeling_age']=3.
    old.data.shape_keys['hm_skin_relief']=.6
    old.data.shape_keys.update_tag();bpy.context.view_layer.update()
    assert all(d.is_valid for d in old.animation_data.drivers)
    name=old.name
    file=output/'Relief-verifie.blend';bpy.ops.wm.save_as_mainfile(filepath=str(file),compress=True)
    bpy.ops.wm.open_mainfile(filepath=str(file));old=bpy.data.objects[name]
    bpy.context.view_layer.update()
    assert old.modifiers[skin_relief.NAME].texture.image.packed_file
    assert all(d.is_valid for d in old.animation_data.drivers)
    (output/'validation-relief.json').write_text(json.dumps({'cases':records,'migration':True,'packed_image_after_reopen':True,
        'cage_preserved':True,'scope':'Finite geometry checks; artistic wrinkles, no validated biological amplitudes'},indent=2),encoding='utf-8')
    print('SKIN_RELIEF_PASS',len(records),flush=True)


if __name__=='__main__':main()
