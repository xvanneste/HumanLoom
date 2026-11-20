"""Show the misplaced field center on the unchanged 0.13 reference bodies."""
import sys,json,math,importlib
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from render_anatomy_review import path_object,material
root=Path(__file__).resolve().parents[1];out=root/'validation/proportions-14'
addon=importlib.import_module('bl_ext.user_default.human_modeling')
addon.ASSET_PATH=out/'extension-13/data/realistic.blend'
scene=bpy.context.scene
for obj in tuple(scene.objects):bpy.data.objects.remove(obj,do_unlink=True)
scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO'
scene.display.shading.color_type='MATERIAL';scene.render.resolution_x=2000;scene.render.resolution_y=1600;scene.render.resolution_percentage=100
clay=material('Argile',(.48,.50,.53));old=material('Ancien calcul',(.95,.18,.12));reference=material('Repère documentaire',(.1,.75,.95));white=material('Texte',(.9,.9,.9))
def text(name,label,position,size=.026,mat=white):
    data=bpy.data.curves.new(name,'FONT');data.body=label;data.size=size
    obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.location=position;obj.rotation_euler.x=math.pi/2;data.materials.append(mat)
profiles=json.loads((out/'anthropometric-profiles.json').read_text(encoding='utf-8'))
records=[]
for sex,label,x in ((0,'Féminin',-.66),(1,'Masculin',.66)):
    scene.cursor.location=(x,0,0);bpy.ops.human_modeling.create();body=bpy.context.object
    body.data.shape_keys.key_blocks['Morphologie'].value=sex;body.data.shape_keys.update_tag()
    for obj in (body,*body.children):
        if obj.type=='MESH':obj.data.materials.clear();obj.data.materials.append(clay)
    p=np.array([v.co[:] for v in body.data.shape_keys.key_blocks['Morphologie' if sex else 'Basis'].data]);h=np.ptp(p[:,2]);floor=p[:,2].min()
    ratio=profiles['sexes'][str(sex)]['profiles']['reference']['normalized_by_stature']['iliocristaleheight']
    for level,name,mat in ((.5307*h,'Ancien centre de calcul · ~0,53 H',old),(floor+ratio*h,f'Repère choisi · {ratio:.2f} H',reference)):
        path_object(body,[(-.22,-.23,level),(.22,-.23,level)],name,mat,.0012)
        text(name,name,(x-.23,-.24,level+.012),.023,mat)
    text(label,label,(x-.11,-.2,-.09),.036)
    records.append({'sex':sex,'old_calculated_field_center_m':float(.5307*h),'selected_reference_height_m':float(floor+ratio*h),'scope':'Comparison of calculation locations, not a palpated native landmark or a universal norm'})
text('Titre','Diagnostic du relief iliaque',(-1.12,-.3,1.88),.060)
text('Légende','Position de calcul 0.13 / repère adulte documentaire à vérifier',(-1.12,-.3,1.80),.033)
camera=bpy.data.objects.new('Diagnostic',bpy.data.cameras.new('Diagnostic'));scene.collection.objects.link(camera);scene.camera=camera
camera.location=(0,-6,.85);camera.rotation_euler=(Vector((0,0,.85))-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=2.8
scene.render.filepath=str(out/'diagnostic-repere-iliaque.png');bpy.ops.render.render(write_still=True)
(out/'diagnostic-repere-iliaque.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
