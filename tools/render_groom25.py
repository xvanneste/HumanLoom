"""Build a review scene through the public groom API, then render actual geometry."""
from pathlib import Path
import sys,json,math
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import extension as addon
from extension import groom
OUT=ROOT/'validation/groom-25';OUT.mkdir(parents=True,exist_ok=True)
addon.register()
for obj in tuple(bpy.context.scene.objects):bpy.data.objects.remove(obj,do_unlink=True)
bpy.ops.human_modeling.create();body=bpy.context.object
body.data.shape_keys.key_blocks['Morphologie'].value=1.;body.data.shape_keys.update_tag()
body.modifiers['Human Modeling · Surface'].levels=2
for region in ('SCALP','BROWS','BEARD','MOUSTACHE','CHEST','ABDOMEN','BACK','ARMS','LEGS'):
    groom.build(body,region,groom.defaults(region))
    print('GROOM25_REVIEW_LAYER',region,flush=True)
skin=bpy.data.materials.new('HumanLoom · argile de revue');skin.use_nodes=True
skin.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.38,.42,.46,1)
skin.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.65
for obj in (body,*body.children):
    if obj.type=='MESH':obj.data.materials.clear();obj.data.materials.append(skin)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=True
scene.render.resolution_x=850;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.world.use_nodes=True;scene.world.node_tree.nodes.get('Background').inputs[0].default_value=(.16,.19,.23,1)
scene.world.node_tree.nodes.get('Background').inputs[1].default_value=.4
for loc,power,size in (((2,-3,4),170,3),((-2,-1,2.5),100,2),((0,2,3),200,2)):
    data=bpy.data.lights.new('Revue groom','AREA');data.energy=power;data.shape='DISK';data.size=size
    obj=bpy.data.objects.new(data.name,data);scene.collection.objects.link(obj);obj.location=loc;obj.rotation_euler=(Vector((0,0,1.3))-obj.location).to_track_quat('-Z','Y').to_euler()
camera=bpy.data.objects.new('Camera de revue',bpy.data.cameras.new('Groom orthographique'));scene.collection.objects.link(camera);scene.camera=camera;camera.data.type='ORTHO'
rows=[]
def render(name,yaw=0,scale=.52,z=1.55):
    target=Vector((0,-.025,z));direction=Vector((math.sin(math.radians(yaw)),-math.cos(math.radians(yaw)),.05))
    camera.location=target+direction*3;camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=scale
    scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True);rows.append(name)
    (OUT/'rendus.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
render('Adulte-pilosite-face');render('Adulte-pilosite-profil',90);render('Adulte-pilosite-dos',180)
render('Adulte-pilosite-corps',0,1.95,.86);render('Adulte-pilosite-corps-dos',180,1.95,.86)
render('Sourcils-barbe-moustache',0,.30,1.55)
body.hl_groom_region='SCALP'
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'HumanLoom-groom-revue.blend'),compress=True)
for amount,label in ((0.,'lisse'),(.25,'ondule'),(.5,'boucle'),(.75,'frise'),(1.,'crepu')):
    cfg=groom.defaults('SCALP');cfg.update(nature=amount,length=.10,viewport=.25)
    groom.build(body,'SCALP',cfg);render('Nature-'+label,25,.57,1.57)
# Long hair on the other morphology, keeping scalp attachment and guide direction.
for obj in body.children:
    if obj.get('hl_groom_region') not in (None,'SCALP','BROWS'):obj.hide_render=True
body.data.shape_keys.key_blocks['Morphologie'].value=0.;body.data.shape_keys.update_tag()
cfg=groom.defaults('SCALP');cfg.update(length=.30,nature=0.,style='PARTED')
groom.build(body,'SCALP',cfg)
render('Cheveux-longs-face',0,.85,1.40);render('Cheveux-longs-profil',90,.85,1.40);render('Cheveux-longs-dos',180,.85,1.40)
print('GROOM25_RENDER_DONE',len(rows),flush=True)
