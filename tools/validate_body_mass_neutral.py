"""Check all-age neutral equivalence with the previous release."""
from pathlib import Path
import json
import sys
import bpy
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from validate_age_dimensions import surface


def main():
    from bl_ext.user_default.human_modeling import character_presets
    old_asset,output=[Path(p).resolve() for p in sys.argv[sys.argv.index('--')+1:]]
    bpy.ops.human_modeling.create();current=bpy.context.object
    with bpy.data.libraries.load(str(old_asset),link=False) as (_,target):target.collections=['Realistic Human Base']
    collection=target.collections[0];bpy.context.scene.collection.children.link(collection)
    previous=next(o for o in collection.objects if o.get('human_modeling_body'))
    previous.modifiers.new('QA','SUBSURF').levels=1;previous.modifiers.move(len(previous.modifiers)-1,0)
    rows=[]
    for sex in (0.,.5,1.):
        for stage in (0.,.5,1.,1.5,2.,2.5,3.):
            for body in (current,previous):
                body.data.shape_keys.key_blocks['Morphologie'].value=sex
                body.data.shape_keys['human_modeling_age']=stage
                body.data.shape_keys.update_tag()
            bpy.context.view_layer.update()
            repair=current.data.shape_keys.key_blocks.get('Age · Adulte · Surface · Raccord interne')
            if repair:repair.mute=True
            current.data.shape_keys.update_tag();bpy.context.view_layer.update()
            difference=float(np.abs(surface(current)[0]-surface(previous)[0]).max())
            if repair:repair.mute=False
            current.data.shape_keys.update_tag();bpy.context.view_layer.update()
            assert difference<1e-7,(sex,stage,difference)
            rows.append({'sex':sex,'stage':stage,'max_coordinate_difference_m':difference,'scope':'New mass field at zero; separate adult inner-eyelid maintenance key temporarily muted for comparison'})
    state=character_presets.capture(current)
    state['controls']['body_mass']=.65
    state['age_stage']=1.
    path=output/'corpulence-et-age.json';character_presets.write(path,state)
    character_presets.apply(current,character_presets.read(path))
    assert character_presets.capture(current)==state
    bpy.context.view_layer.objects.active=previous
    before=character_presets.capture(previous)
    assert bpy.ops.human_modeling.add_proportions()=={'FINISHED'}
    assert character_presets.capture(previous)==before
    assert previous.data.shape_keys['hm_body_mass']==0.
    assert all(c.is_valid for c in previous.data.shape_keys.animation_data.drivers)
    output.joinpath('neutralite-et-migration.json').write_text(json.dumps({'neutral_cases':rows,'preset_roundtrip':True,'upgrade_preserves_settings':True},indent=2),encoding='utf-8')
    print('BODY_MASS_NEUTRALITY_PASS',len(rows),flush=True)


if __name__=='__main__':main()
