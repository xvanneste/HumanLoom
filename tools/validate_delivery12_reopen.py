"""Reopen delivered checkpoints and verify editable keys and packed relief."""
from pathlib import Path
import json
import bpy
from bl_ext.user_default.human_modeling import character_presets,skin_relief,proportions
# I-34 : le nombre de contrôles n'est plus codé en dur (47 attendus à la livraison 12, schéma 7) ;
# on compare à la déclaration courante. Les fichiers livrés restent au schéma 7 : les contrôles ajoutés depuis
# n'existent pas dans leurs clés de forme et sont lus à 0 par capture() (valeur neutre).
CONTROL_COUNT=len(proportions.CONTROLS)
root=Path(__file__).resolve().parents[1]/'validation/corpulences-12'
records=[]
for relative,expected in (('Session-modelisation-12.blend',2),('revue-livree-09/Morphologies-corporelles.blend',8)):
    bpy.ops.wm.open_mainfile(filepath=str(root/relative))
    bodies=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.get('human_modeling_body') and o.data.shape_keys and 'Morphologie' in o.data.shape_keys.key_blocks]
    assert len(bodies)==expected,(relative,len(bodies))
    for body in bodies:
        assert body.data['human_modeling_schema']==7
        captured=character_presets.capture(body)['controls']
        assert len(captured)==CONTROL_COUNT,(len(captured),CONTROL_COUNT)
        missing=[k for k in captured if proportions.property_name(k) not in body.data.shape_keys]
        assert all(captured[k]==0.0 for k in missing),missing  # contrôle absent du fichier livré => neutre
        assert all(d.is_valid for d in body.data.shape_keys.animation_data.drivers)
        assert body.modifiers[skin_relief.NAME].texture.image.packed_file
    records.append({'file':relative,'editable_bodies':len(bodies),'controls':CONTROL_COUNT,'controls_absent_du_fichier':len(missing),'drivers_valid':True,'packed_textures':True})
(root/'reouverture-livraison.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
print('DELIVERY12_REOPEN_PASS',flush=True)
