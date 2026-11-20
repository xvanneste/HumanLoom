"""Render actual VIEWPORT evaluated hair at 10/100%, beside native final Cycles.

Previews are frozen copies of the VIEWPORT dependency graph, lit in Cycles for
an equal-lighting density comparison. They are not screenshots of Blender UI.
The source guides, assets and user scene are never saved or modified.
"""
from pathlib import Path
import sys,json,math
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import extension
from extension import groom
OUT=ROOT/'validation/apercus-rendus-27';OUT.mkdir(parents=True,exist_ok=True)
assert bpy.app.background and bpy.app.version[:2]==(5,2)
extension.register()
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'validation/groom-25/HumanLoom-groom-revue.blend'),load_ui=False)
body=next(o for o in bpy.context.scene.objects if o.get('human_modeling_body'))
hairs=[o for o in body.children if o.get('hl_groom_region')]
scene=bpy.context.scene;scene.render.resolution_x=900;scene.render.resolution_y=1050;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.engine='CYCLES';scene.cycles.samples=20;scene.cycles.use_denoising=True
rows=[]
for name,yaw,scale,z in [('face',0,.52,1.55),('profil',90,.52,1.55),('dos',180,.52,1.55),('detail',20,.30,1.61)]:
    target=Vector((0,-.025,z));direction=Vector((math.sin(math.radians(yaw)),-math.cos(math.radians(yaw)),.05))
    camera=scene.camera;camera.location=target+direction*3;camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=scale
    for amount in (.1,1.):
        for hair in hairs:groom.viewport_quality(hair,amount)
        bpy.context.view_layer.update();graph=bpy.context.evaluated_depsgraph_get();assert graph.mode=='VIEWPORT'
        copies=[];counts={}
        for hair in hairs:
            evaluated=hair.evaluated_get(graph)
            data=evaluated.data.copy()
            frozen=bpy.data.objects.new('Copie évaluée pour comparaison',data);scene.collection.objects.link(frozen)
            frozen.matrix_world=hair.matrix_world.copy();copies.append(frozen)
            counts[hair['hl_groom_region']]=len(data.curves)
        for hair in hairs:hair.hide_render=True
        path=OUT/f'{name}-apercu-{int(amount*100):03d}.png';scene.render.filepath=str(path)
        bpy.ops.render.render(write_still=True)
        rows.append({'view':name,'kind':'viewport_geometry_cycles_lighting','fraction':amount,'curve_counts':counts,'file':path.name,'samples':20})
        for frozen in copies:
            data=frozen.data;bpy.data.objects.remove(frozen,do_unlink=True)
            if not data.users:bpy.data.hair_curves.remove(data)
        for hair in hairs:hair.hide_render=False
        (OUT/'captures.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
        print('QUALITY27_PREVIEW',name,amount,counts['SCALP'],flush=True)
    for hair in hairs:groom.viewport_quality(hair,.1)
    path=OUT/f'{name}-rendu-cycles.png';scene.render.filepath=str(path)
    bpy.ops.render.render(write_still=True)
    rows.append({'view':name,'kind':'native_cycles_final','file':path.name,'samples':20,'viewport_fraction_during_render':.1})
    (OUT/'captures.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    print('QUALITY27_FINAL',name,flush=True)
(OUT/'done.json').write_text(json.dumps({'status':'complete','images':len(rows)},indent=2),encoding='utf-8')
print('QUALITY27_DONE',len(rows),flush=True)
