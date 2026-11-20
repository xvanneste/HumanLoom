"""Review stable surface anchors on both bodies from four orthographic views."""
from pathlib import Path
import sys,json,math,importlib
import bpy,numpy as np
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from build_surface_atlas15 import position
from experimental_growth_field import endpoint
from render_anatomy_review import path_object,material

root=Path(__file__).resolve().parents[1];out=root/'validation/atlas-15';out.mkdir(parents=True,exist_ok=True)
atlas=json.loads((out/'atlas-candidat-01.json').read_text(encoding='utf-8'))
addon=importlib.import_module('bl_ext.user_default.human_modeling');addon.ASSET_PATH=root/'validation/proportions-14/extension-13/data/realistic.blend'
scene=bpy.context.scene
for obj in tuple(scene.objects):bpy.data.objects.remove(obj,do_unlink=True)
scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL'
scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH'
scene.render.resolution_x=2200;scene.render.resolution_y=1800;scene.render.resolution_percentage=100
clay=material('Argile atlas',(.48,.50,.53));dot=material('Repères de surface',(.95,.45,.12));ink=material('Code des repères',(.95,.85,.55))
groups=[]
for sex in (0,1):
    bpy.ops.human_modeling.create();body=bpy.context.object;body.data.shape_keys.key_blocks['Morphologie'].value=sex;body.data.shape_keys.update_tag()
    for obj in (body,*body.children):
        if obj.type=='MESH':obj.data.materials.clear();obj.data.materials.append(clay)
    points=endpoint(body,sex);markers=[];texts=[]
    for name,anchor in atlas['anchors'].items():
        p=position(points,anchor)
        bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=8,radius=.004,location=p)
        marker=bpy.context.object;marker.parent=body;marker.data.materials.append(dot);markers.append(marker)
        data=bpy.data.curves.new(anchor['short'],'FONT');data.body=anchor['short'];data.size=.021
        text=bpy.data.objects.new(name,data);scene.collection.objects.link(text);text.parent=body;data.materials.append(ink);texts.append((text,p,anchor['placement_view']))
    groups.append((body,markers,texts))
camera=bpy.data.objects.new('Atlas orthographique',bpy.data.cameras.new('Atlas orthographique'));scene.collection.objects.link(camera);scene.camera=camera
camera.data.type='ORTHO';camera.data.ortho_scale=2.55
for name,yaw in (('face',0.),('dos',math.pi),('profil',math.pi/2),('trois-quarts',math.pi/4)):
    view=Vector((math.sin(yaw),-math.cos(yaw),0));horizontal=Vector((math.cos(yaw),math.sin(yaw),0))
    camera.location=view*8+Vector((0,0,.83));camera.rotation_euler=(Vector((0,0,.83))-camera.location).to_track_quat('-Z','Y').to_euler()
    for i,(body,markers,texts) in enumerate(groups):
        body.location=horizontal*((i-.5)*1.15)
        for text,p,placement in texts:
            text.location=Vector(p)+view*.07+horizontal*.008+Vector((0,0,.008));text.rotation_euler=(math.pi/2,0,yaw)
    bpy.context.view_layer.update();scene.render.filepath=str(out/('atlas-'+name+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'Atlas-reperes-01.blend'),compress=True)
print('SURFACE_ATLAS_REVIEW_READY',flush=True)
