"""Reopen delivered checkpoints and verify editable keys and packed relief."""
from pathlib import Path
import json
import bpy
from bl_ext.user_default.human_modeling import character_presets,skin_relief
root=Path(__file__).resolve().parents[1]/'validation/morphologie-globale-13'
records=[]
for relative,expected in (('Session-modelisation-13.blend',2),('revue-livraison-04/Morphologies-corporelles.blend',8)):
    bpy.ops.wm.open_mainfile(filepath=str(root/relative))
    bodies=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.get('human_modeling_body') and o.data.shape_keys and 'Morphologie' in o.data.shape_keys.key_blocks]
    assert len(bodies)==expected,(relative,len(bodies))
    for body in bodies:
        assert body.data['human_modeling_schema']==8
        assert len(character_presets.capture(body)['controls'])==48
        assert all(d.is_valid for d in body.data.shape_keys.animation_data.drivers)
        assert body.modifiers[skin_relief.NAME].texture.image.packed_file
    records.append({'file':relative,'editable_bodies':len(bodies),'controls':48,'drivers_valid':True,'packed_textures':True})
(root/'reouverture-livraison.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
print('DELIVERY13_REOPEN_PASS',flush=True)

