from pathlib import Path
import sys
import bpy
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from experimental_age_transfer import coordinates
bpy.ops.human_modeling.create();body=bpy.context.object;k=body.data.shape_keys;b=coordinates(k.key_blocks[0])
for name in ('HM · anatomical_bony_surface','HM · anatomical_muscle_surface'):
    delta=coordinates(k.key_blocks[name])-b
    print(name,'max m',np.linalg.norm(delta,axis=1).max(),'affected',np.count_nonzero(np.linalg.norm(delta,axis=1)>1e-6),flush=True)
