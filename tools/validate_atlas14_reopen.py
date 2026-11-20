"""Verify the editable research scene without promoting it to a release."""
from pathlib import Path
import json,bpy,sys
from bl_ext.user_default.human_modeling import character_presets,skin_relief
version=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else '07'
root=Path(__file__).resolve().parents[1]/f'validation/proportions-14/revue-travail-{version}'
bpy.ops.wm.open_mainfile(filepath=str(root/'Morphologies-corporelles.blend'))
bodies=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.get('human_modeling_body') and o.data.shape_keys and 'Morphologie' in o.data.shape_keys.key_blocks]
assert len(bodies)==8
rows=[]
for body in bodies:
    state=character_presets.capture(body)
    assert state==character_presets.read(root/(body.name+'.json'))
    assert len(state['controls'])==48
    assert 'hm_anatomy_candidate' in body
    assert all(d.is_valid for d in body.data.shape_keys.animation_data.drivers)
    assert body.modifiers[skin_relief.NAME].texture.image.packed_file
    rows.append({'body':body.name,'research_candidate':True,'controls':48,'preset_preserved':True,'drivers_valid':True,'packed_texture':True})
(root.parent/f'reouverture-candidat-{version}.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print('RESEARCH_CANDIDATE_REOPEN_PASS',flush=True)
