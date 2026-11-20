"""Close views of actual body-hair layers from the delivered review scene."""
from pathlib import Path
import sys,json,math,bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import extension
extension.register();out=ROOT/'validation/groom-25'
bpy.ops.wm.open_mainfile(filepath=str(out/'HumanLoom-groom-revue.blend'),load_ui=False)
scene=bpy.context.scene;camera=scene.camera;scene.cycles.samples=20
for name,target,scale,yaw in [('Poils-torse',(0,-.03,1.13),.65,0),('Poils-bras',(.27,-.02,1.05),.36,25),('Poils-jambes',(0,0,.39),.60,0)]:
    t=Vector(target);direction=Vector((math.sin(math.radians(yaw)),-math.cos(math.radians(yaw)),0))
    camera.location=t+direction*3;camera.rotation_euler=(t-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=scale
    scene.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
print('GROOM25_BODY_DETAILS_DONE',flush=True)
