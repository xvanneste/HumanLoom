"""Check that the new mass field leaves the neutral shape equal to the frozen reference of the current asset (D-19),
then preset round-trip and the upgrade of a previous-release file (extension-13 stays a migration fixture)."""
from pathlib import Path
import json
import sys
import bpy
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
import neutral_reference as neutral


def main():
    from bl_ext.user_default.human_modeling import character_presets
    old_asset,output=[Path(p).resolve() for p in sys.argv[sys.argv.index('--')+1:]]
    bpy.ops.human_modeling.create();current=bpy.context.object
    with bpy.data.libraries.load(str(old_asset),link=False) as (_,target):target.collections=['Realistic Human Base']
    collection=target.collections[0];bpy.context.scene.collection.children.link(collection)
    previous=next(o for o in collection.objects if o.get('human_modeling_body'))
    reference=neutral.load()
    rows=[]
    for sex in (0.,.5,1.):
        for stage in (0.,.5,1.,1.5,2.,2.5,3.):
            neutral.set_state(current,sex,stage)
            assert current.data.shape_keys['hm_body_mass']==0.
            difference=neutral.check(current,reference,sex,stage)
            rows.append({'sex':sex,'stage':stage,'max_coordinate_difference_m':difference,'scope':'Mass field at zero; cage compared with the frozen reference of the current asset (tools/data/neutral_reference.json)'})
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
