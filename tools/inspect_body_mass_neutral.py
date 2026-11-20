import sys
from pathlib import Path
import json
import bpy
from bl_ext.user_default.human_modeling import ASSET_PATH
bpy.ops.human_modeling.create();body=bpy.context.object;keys=body.data.shape_keys
keys.key_blocks['Morphologie'].value=0.;keys['human_modeling_age']=0.;keys['hm_body_mass']=0.
keys.update_tag();bpy.context.view_layer.update()
data={'asset':str(ASSET_PATH),'nonzero_properties':{k:keys[k] for k in keys.keys() if k.startswith('hm_') and keys[k]!=0},
      'mass_keys':[{ 'key':k.name,'value':k.value,'driver':next((d.driver.expression for d in keys.animation_data.drivers if d.data_path==k.path_from_id('value')),None)} for k in keys.key_blocks if 'body_mass' in k.name],
      'age_keys':{k.name:k.value for k in keys.key_blocks if k.name in ('Enfant','Enfant · morphologie','Adolescent','Senior')}}
print(json.dumps(data,indent=2),flush=True)
