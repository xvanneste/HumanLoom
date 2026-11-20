"""Render an unchanged generator with locked cameras for a body-volume diagnosis."""
from pathlib import Path
import sys,json,math
import bpy,numpy as np
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import extension as addon
OUT=ROOT/'validation/comparaison-corpulence-24'
(OUT/'images').mkdir(parents=True,exist_ok=True)
(OUT/'presets').mkdir(exist_ok=True)
assert bpy.app.version[:2]==(5,2) and bpy.app.background
addon.register()
for o in tuple(bpy.context.scene.objects):bpy.data.objects.remove(o,do_unlink=True)
bpy.ops.human_modeling.create();body=bpy.context.object;keys=body.data.shape_keys
mod=body.modifiers['Human Modeling · Surface'];mod.levels=2;mod.render_levels=2
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH'
scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
shade=scene.display.shading;shade.light='STUDIO';shade.color_type='OBJECT';shade.show_shadows=False
shade.show_cavity=True;shade.cavity_type='BOTH';shade.background_type='WORLD'
scene.world.color=(.11,.125,.15)
for o in (body,*body.children):o.color=(.57,.59,.62,1)
camera=bpy.data.objects.new('Camera comparaison verrouillee',bpy.data.cameras.new('Orthographique'))
scene.collection.objects.link(camera);scene.camera=camera;camera.data.type='ORTHO'
camera.data.clip_start=.001;camera.data.clip_end=100

def reset(morph):
    for name,_ in addon.proportions.CONTROLS:keys['hm_'+name]=0.
    keys.key_blocks['Morphologie'].value=morph;keys['human_modeling_age']=2.

def points():
    keys.update_tag();body.update_tag();bpy.context.view_layer.update()
    mod.show_viewport=False;bpy.context.view_layer.update()
    evaluated=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
    arr=np.array([v.co[:] for v in mesh.vertices]);evaluated.to_mesh_clear()
    mod.show_viewport=True;bpy.context.view_layer.update();return arr

levels=[('maigre',-1.,'VERY_LEAN'),('mince',-.65,'MINCE'),('normal',0.,'REFERENCE'),('gros',1.,'LARGE')]
angles=[('face',0,'body'),('profil',90,'body'),('trois-quarts',45,'body'),('dos',180,'body'),('ventre-face',0,'abdomen'),('ventre-profil',90,'abdomen')]
results=[];diagnostics=[]
for morph,sex in ((0.,'F'),(1.,'M')):
    reset(morph);neutral=points();floor=neutral[:,2].min();height=np.ptp(neutral[:,2])
    zn=(neutral[:,2]-floor)/height
    # Fixed neutral vertex sets: omit hanging arms from the trunk sections.
    masks={name:(abs(zn-ratio)<.015)&(abs(neutral[:,0])<limit) for name,ratio,limit in [('abdomen',.60,.18),('bassin',.50,.23),('thorax',.74,.19)]}
    def measures(arr):
        return {name:{'largeur_cm':float(np.ptp(arr[mask,0])*100),'profondeur_cm':float(np.ptp(arr[mask,1])*100),'avant_cm':float(-np.quantile(arr[mask,1],.1)*100),'vertices':int(mask.sum())} for name,mask in masks.items()}
    baseline=measures(neutral)
    for control in ('whole_body','corpulence','body_mass','adiposity'):
        reset(morph);keys['hm_'+control]=1.;arr=points()
        diagnostics.append({'sex':sex,'control':control,'value':1.,'neutral':baseline,'measures':measures(arr),'active_shapes':{k.name:float(k.value) for k in keys.key_blocks if abs(k.value)>1e-5}})
    for mode in ('curseur','prereglage'):
        for label,value,profile in levels:
            reset(morph)
            if mode=='prereglage':
                bpy.context.view_layer.objects.active=body;body.select_set(True)
                assert bpy.ops.human_modeling.body_profile(profile=profile)=={'FINISHED'}
            else:keys['hm_whole_body']=value
            arr=points();identifier=f'{sex}-{mode}-{label}'
            addon.character_presets.write(str(OUT/'presets'/(identifier+'.json')),addon.character_presets.capture(body))
            entry={'id':identifier,'sex':sex,'mode':mode,'label':label,'value':value,'profile':profile,'neutral':baseline,'measures':measures(arr),'images':{}}
            for angle,yaw,region in angles:
                # Identical target, scale and resolution across all compared configurations.
                target=Vector((0,0,.84 if region=='body' else 1.00))
                direction=Vector((math.sin(math.radians(yaw)),-math.cos(math.radians(yaw)),0))
                camera.location=target+direction*5;camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
                camera.data.ortho_scale=2.05 if region=='body' else .78
                scene.render.resolution_x=900;scene.render.resolution_y=1500 if region=='body' else 1000
                path=OUT/'images'/f'{identifier}-{angle}.png';scene.render.filepath=str(path)
                if not path.exists():bpy.ops.render.render(write_still=True)
                entry['images'][angle]=path.relative_to(OUT).as_posix()
            results.append(entry)
            (OUT/'comparaisons.json').write_text(json.dumps(results,indent=2,ensure_ascii=False),encoding='utf-8')
            print('CORPULENCE24',identifier,len(results),'/16',flush=True)
(OUT/'diagnostic-controles.json').write_text(json.dumps(diagnostics,indent=2,ensure_ascii=False),encoding='utf-8')
print('CORPULENCE24_DONE',len(results),flush=True)
