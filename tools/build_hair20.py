from pathlib import Path
import sys, json
import bpy
sys.path.insert(0, str(Path(__file__).resolve().parent))
import hair_prototype20 as hair20

body, hair = hair20.make_scene()
points = hair20.evaluated_points(hair)
print('HAIR_EVALUATED', points.shape, points.min(0), points.max(0), flush=True)
path = hair20.OUT/'Prototype-cheveux-01.blend'
bpy.ops.object.make_local(type='ALL')
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(path), compress=True)
for label, direction in [('face',(0,-1,.12)),('profil',(1,0,.12)),('trois-quarts',(.8,-1,.3)),('dos',(0,1,.15))]:
    hair20.frame_camera(bpy.context.scene, (0,-.045,1.49), .52, direction)
    bpy.context.scene.render.filepath = str(hair20.OUT/('cheveux-01-'+label+'.png'))
    bpy.ops.render.render(write_still=True)
hair20.frame_camera(bpy.context.scene, (0,-.04,.85), 1.95, (0,-1,.06))
bpy.context.scene.render.resolution_y = 1450
bpy.context.scene.render.filepath = str(hair20.OUT/'cheveux-01-corps-entier.png')
bpy.ops.render.render(write_still=True)
print('HAIR20_BUILD_DONE', flush=True)
