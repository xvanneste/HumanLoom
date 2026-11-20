"""Regression for the curl transition; refresh its actual review render."""
from pathlib import Path
import sys,json,math,bpy,numpy as np
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import extension
from extension import groom
extension.register();out=ROOT/'validation/groom-25'
bpy.ops.wm.open_mainfile(filepath=str(out/'HumanLoom-groom-revue.blend'),load_ui=False)
body=next(o for o in bpy.context.scene.objects if o.get('human_modeling_body'))
roots,normals,*_=groom.sample(body,'SCALP',30,2026)
cfg=groom.defaults('SCALP');cfg.update(length=.10)
results=[]
for boundary in (.20,.25,.35):
    a=groom.make_positions(body,roots,normals,'SCALP',{**cfg,'nature':boundary-.0001})
    b=groom.make_positions(body,roots,normals,'SCALP',{**cfg,'nature':boundary+.0001})
    distance=float(np.max(np.linalg.norm(np.array([p[-1] for p in a])-np.array([p[-1] for p in b]),axis=1)))
    assert distance<.001,(boundary,distance)
    results.append({'boundary':boundary,'max_tip_change_m':distance,'parameter_step':.0002})
(out/'validation-continuity.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
cfg.update(nature=.25,viewport=.25);groom.build(body,'SCALP',cfg)
scene=bpy.context.scene;camera=scene.camera;target=Vector((0,-.025,1.57));yaw=math.radians(25)
direction=Vector((math.sin(yaw),-math.cos(yaw),.05))
camera.location=target+direction*3;camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=.57
scene.render.filepath=str(out/'Nature-ondule.png');bpy.ops.render.render(write_still=True)
print('GROOM25_CONTINUITY_PASS',results,flush=True)
