"""Bake and reopen a native physics bench; original character files stay intact."""
from pathlib import Path
import sys,math,json,time
import bpy,numpy as np
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import hair_prototype20 as h20
from hair_physics22 import build_guides,configure_benchmark

assert bpy.app.background and bpy.app.version[:2]==(5,2)
out=h20.ROOT/'validation/physique-cheveux-22';out.mkdir(exist_ok=True)
for obj in tuple(bpy.context.scene.objects):bpy.data.objects.remove(obj,do_unlink=True)
body=h20.load_body()
hair=build_guides(body,points=8,count=12)
hair.name='XPBD · 12 guides · 6 cm'
profile=configure_benchmark(hair)
scene=bpy.context.scene
scene.render.fps=24;scene.frame_start=1;scene.frame_end=48
scene.frame_set(1)
bpy.ops.object.make_local(type='ALL')
modifier=hair.modifiers[0]
modifier.bake_target='PACKED'
bpy.context.view_layer.update()
print('NATIVE_BAKES',len(modifier.bakes),flush=True)
for bake in modifier.bakes:
    bake.use_custom_simulation_frame_range=True
    bake.frame_start=1;bake.frame_end=48
    bake.bake_target='PACKED'
for obj in bpy.context.selected_objects:obj.select_set(False)
hair.select_set(True);bpy.context.view_layer.objects.active=hair
path=out/'Banc-physique-cheveu-03.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(path),compress=True)
started=time.perf_counter()
result=bpy.ops.object.simulation_nodes_cache_bake(selected=True)
assert result=={'FINISHED'},result
elapsed=time.perf_counter()-started
rows=[];first=None;last=None
for frame in range(1,49):
    scene.frame_set(frame)
    p=h20.evaluated_points(hair).reshape((12,8,3))
    if first is None:first=p.copy()
    last=p.copy()
    lengths=np.linalg.norm(np.diff(p,axis=1),axis=2).sum(axis=1)
    rows.append({'frame':frame,'maximum_extension_fraction':float(np.max(lengths/.06-1)),'root_motion_m':float(np.linalg.norm(p[:,0]-first[:,0],axis=1).max())})
assert max(r['maximum_extension_fraction'] for r in rows)<.01
assert max(r['root_motion_m'] for r in rows)<1e-6
assert np.linalg.norm(last-first,axis=2).max()>.001

# Presentation copies are measured solver output, enlarged only in thickness.
for obj in tuple(scene.objects):obj.hide_render=True
mat1=h20.material('Repos initial',(.12,.30,.55))
mat2=h20.material('Sous gravité',(.18,.50,.22))
textmat=h20.material('Texte',(.8,.8,.8))
anchor=first[0,0]
for points,offset,label,material in [(first[0],-.045,'Image 1',mat1),(last[0],.045,'Image 48',mat2)]:
    data=bpy.data.curves.new('Mesure · '+label,'CURVE');data.dimensions='3D';data.bevel_depth=.00045;data.bevel_resolution=3
    spline=data.splines.new('POLY');spline.points.add(len(points)-1)
    for item,position in zip(spline.points,points-anchor+np.array([offset,0.,0.])):item.co=(*position,1)
    obj=bpy.data.objects.new(data.name,data);scene.collection.objects.link(obj);data.materials.append(material)
    font=bpy.data.curves.new(label,'FONT');font.body=label;font.size=.004;font.align_x='CENTER'
    obj=bpy.data.objects.new(label,font);scene.collection.objects.link(obj);obj.location=(offset,-.012,-.025);obj.rotation_euler=(math.pi/2,0,0);font.materials.append(textmat)
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.render.resolution_x=1200;scene.render.resolution_y=850;scene.render.resolution_percentage=100
scene.world.color=(.4,.4,.4)
h20.frame_camera(scene,(0,0,.005),.18,(.2,-1,.15))
for location,power in [((0,-.4,.4),8),((-.3,-.2,.25),4)]:
    data=bpy.data.lights.new('Eclairage du banc','AREA');data.energy=power;data.size=.35
    obj=bpy.data.objects.new(data.name,data);scene.collection.objects.link(obj);obj.location=location
    obj.rotation_euler=(Vector((0,0,.02))-obj.location).to_track_quat('-Z','Y').to_euler()
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA'
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(path),compress=True)
scene.render.filepath=str(out/'Gravite-fibre-droite-48-images.png')
bpy.ops.render.render(write_still=True)
name=hair.name
bpy.ops.wm.open_mainfile(filepath=str(path))
bpy.context.scene.frame_set(48)
reopened=h20.evaluated_points(bpy.data.objects[name]).reshape((12,8,3))
error=float(np.linalg.norm(reopened-last,axis=2).max())
assert error<2e-6,('Packed bake mismatch',error)
report={'profile':profile,'blender':bpy.app.version_string,'guides':12,'frames':rows,'packed_cache_reopened':True,'cache_reopen_error_m':error,'bake_seconds':elapsed,'material_calibrated':False,'collisions_tested':False,'presentation':'Two snapshots of first guide; thickness exaggerated; source Hair Curves remain separate and baked'}
(out/'banc-valide-03.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('NATIVE_PHYSICS22_BENCH_PASS',elapsed,error,flush=True)
