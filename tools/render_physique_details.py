"""Original Blender renders of anatomical surface changes, without textures."""
import sys
from pathlib import Path
import bpy
from mathutils import Vector

output=Path(sys.argv[sys.argv.index('--')+1]).resolve();output.mkdir(parents=True,exist_ok=True)
scene=bpy.context.scene
for obj in tuple(scene.objects):bpy.data.objects.remove(obj,do_unlink=True)
scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO'
scene.display.shading.color_type='SINGLE';scene.display.shading.single_color=(.55,.57,.60)
scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True
scene.display.shading.cavity_type='BOTH';scene.display.shading.curvature_ridge_factor=1.2
scene.display.shading.curvature_valley_factor=1.1
scene.render.resolution_x=2400;scene.render.resolution_y=1400;scene.render.resolution_percentage=100
camera=bpy.data.objects.new('Revue anatomique',bpy.data.cameras.new('Revue anatomique'));scene.collection.objects.link(camera);scene.camera=camera
camera.data.type='ORTHO';camera.data.ortho_scale=2.85
bodies=[]
for index,(fat,muscle) in enumerate(((-1.,-.7),(0.,0.),(-.35,1.))):
    scene.cursor.location=((index-1)*.95,0,0);bpy.ops.human_modeling.create();body=bpy.context.object
    body.data.shape_keys['hm_whole_body']=fat;body.data.shape_keys['hm_muscles']=muscle
    body.modifiers['Human Modeling · Surface'].levels=2
    bodies.append(body)
for sex,label in ((0.,'Féminine'),(1.,'Masculine')):
    for body in bodies:body.data.shape_keys.key_blocks['Morphologie'].value=sex;body.data.shape_keys.update_tag()
    bpy.context.view_layer.update()
    for y,angle in ((-10,'face'),(10,'dos')):
        camera.location=(0,y,1.27);camera.rotation_euler=(Vector((0,0,1.27))-camera.location).to_track_quat('-Z','Y').to_euler()
        scene.render.filepath=str(output/(label+'-'+angle+'.png'));bpy.ops.render.render(write_still=True)
print('ANATOMICAL_DETAILS_READY',flush=True)
