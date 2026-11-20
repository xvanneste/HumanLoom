"""Render the unmodified 0.14 model from an extensive camera plan in Blender 5.2."""
from pathlib import Path
import sys,json,math,argparse,time
import bpy,numpy as np
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from validation_boards23 import ROOT,OUT
sys.path.insert(0,str(ROOT))
import extension as addon

parser=argparse.ArgumentParser();parser.add_argument('--shard',type=int,default=0);parser.add_argument('--limit',type=int,default=0);parser.add_argument('--force',action='store_true');parser.add_argument('--diagnostic-light',action='store_true')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
assert bpy.app.background and bpy.app.version[:2]==(5,2)
addon.register()
for obj in tuple(bpy.context.scene.objects):bpy.data.objects.remove(obj,do_unlink=True)
assert bpy.ops.human_modeling.create()=={'FINISHED'}
body=bpy.context.object
body.modifiers['Human Modeling · Surface'].levels=2
body.modifiers['Human Modeling · Surface'].render_levels=2
keys=body.data.shape_keys
base=np.array([v.co[:] for v in body.data.vertices]);top=base[:,2].max();height=np.ptp(base[:,2])
x,y,z=base.T
masks={
 'body':np.ones(len(base),dtype=bool),'head':z>top-.225,
 'torso':(z>.45*height)&(z<.88*height)&(abs(x)<.24),
 'hips':(z>.40*height)&(z<.60*height)&(abs(x)<.24),
 'axilla_pos':(x>.09)&(x<.255)&(z>.68*height)&(z<.88*height),
 'axilla_neg':(x<-.09)&(x>-.255)&(z>.68*height)&(z<.88*height),
 'knees':(z>.24*height)&(z<.38*height)&(abs(x)<.19),
 'hand_pos':x>.33,'hand_neg':x<-.33,
 'feet':z<.085*height,
 'eyes':(z>top-.14)&(z<top-.075)&(abs(x)<.058)&(y<-.07),
 'mouth':(z>top-.213)&(z<top-.14)&(abs(x)<.048)&(y<-.075),
 'ear_pos':(x>.061)&(z>top-.18)&(z<top-.065)&(y>-.09),
 'ear_neg':(x<-.061)&(z>top-.18)&(z<top-.065)&(y>-.09),
 'arms':(abs(x)>.19)&(z>.45*height)&(z<.85*height),
 'thighs':(z>.29*height)&(z<.55*height)&(abs(x)<.25),
 'calves':(z>.08*height)&(z<.32*height)&(abs(x)<.20),
}
assert all(mask.sum()>15 for mask in masks.values()),[(n,int(m.sum())) for n,m in masks.items()]
scene=bpy.context.scene
scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB';scene.render.image_settings.compression=25
shade=scene.display.shading;shade.light='STUDIO';shade.color_type='OBJECT';shade.show_cavity=True;shade.cavity_type='BOTH';shade.show_shadows=True
shade.background_type='WORLD'
if args.diagnostic_light:shade.show_shadows=False
scene.world.color=(.11,.125,.15)
for obj in (body,*body.children):obj.color=(.57,.59,.62,1)
camera=bpy.data.objects.new('Camera de validation',bpy.data.cameras.new('Orthographie de validation'));scene.collection.objects.link(camera);scene.camera=camera
camera.data.type='ORTHO';camera.data.clip_start=.001;camera.data.clip_end=100
plan=json.loads((OUT/'plan.json').read_text(encoding='utf-8'))
cases={case['id']:case for case in plan['cases']}
views=[v for v in plan['views'] if (0 if cases[v['case']]['morph']<=.5 else 1)==args.shard]
(OUT/'images').mkdir(exist_ok=True);(OUT/'presets').mkdir(exist_ok=True)
logpath=OUT/f'render-shard-{args.shard}{"-diagnostic-light" if args.diagnostic_light else ""}.json'
records={}
if logpath.exists():records=json.loads(logpath.read_text(encoding='utf-8'))
active_case=None;points=None;rendered=0;started=time.perf_counter()


def apply_case(case):
    for identifier,label in addon.proportions.CONTROLS:keys['hm_'+identifier]=0.
    keys.key_blocks['Morphologie'].value=case['morph'];keys['human_modeling_age']=case['age']
    for obj in tuple(bpy.context.selected_objects):obj.select_set(False)
    body.select_set(True);bpy.context.view_layer.objects.active=body
    assert bpy.ops.human_modeling.body_profile(profile=case['profile'])=={'FINISHED'}
    for identifier,value in case['controls'].items():keys['hm_'+identifier]=value
    keys.update_tag();body.update_tag();bpy.context.view_layer.update()
    addon.character_presets.write(str(OUT/'presets'/(case['id']+'.json')),addon.character_presets.capture(body))
    mod=body.modifiers['Human Modeling · Surface'];visible=mod.show_viewport;mod.show_viewport=False
    bpy.context.view_layer.update();evaluated=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
    try:
        coords=np.array([v.co[:] for v in mesh.vertices])
        assert len(coords)==len(base) and np.isfinite(coords).all()
    finally:evaluated.to_mesh_clear();mod.show_viewport=visible;bpy.context.view_layer.update()
    return coords


def aim(view,coords):
    region=view['region'];selected=coords[masks[region]]
    yaw=math.radians(view['yaw']);elevation=math.radians(view['elevation'])
    direction=Vector((math.sin(yaw)*math.cos(elevation),-math.cos(yaw)*math.cos(elevation),math.sin(elevation)))
    target=Vector((selected.min(0)+selected.max(0))/2)
    camera.location=target+direction*5
    camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
    right=np.array(camera.rotation_euler.to_quaternion()@Vector((1,0,0)));up=np.array(camera.rotation_euler.to_quaternion()@Vector((0,1,0)))
    r=selected@right;u=selected@up
    center=right*((r.min()+r.max())/2)+up*((u.min()+u.max())/2)
    target_array=np.array(target);target_array+=center-right*np.dot(target_array,right)-up*np.dot(target_array,up)
    target=Vector(target_array)
    camera.location=target+direction*5
    if region=='body':scene.render.resolution_x=1100;scene.render.resolution_y=1600
    else:scene.render.resolution_x=1400;scene.render.resolution_y=1400
    aspect=scene.render.resolution_x/scene.render.resolution_y
    width=float(np.ptp(r));h=float(np.ptp(u));margin=1.15 if region=='body' else 1.25
    camera.data.ortho_scale=(max(width,h*aspect) if aspect>=1 else max(h,width/aspect))*margin
    return {'camera_position':list(camera.location),'camera_euler':list(camera.rotation_euler),'ortho_scale':camera.data.ortho_scale,'model_height_m':float(np.ptp(coords[:,2])),'selected_vertices':int(masks[region].sum()),'resolution':[scene.render.resolution_x,scene.render.resolution_y]}


def make_wire(region):
    mod=body.modifiers['Human Modeling · Surface'];visible=mod.show_viewport;mod.show_viewport=False;bpy.context.view_layer.update()
    graph=bpy.context.evaluated_depsgraph_get();evaluated=body.evaluated_get(graph)
    mesh=bpy.data.meshes.new_from_object(evaluated,depsgraph=graph)
    mod.show_viewport=visible;bpy.context.view_layer.update()
    for v in mesh.vertices:v.co+=v.normal*.0006
    obj=bpy.data.objects.new('Cage technique temporaire',mesh);scene.collection.objects.link(obj);obj.color=(.06,.55,.75,1)
    wire=obj.modifiers.new('Aretes de la cage','WIREFRAME');wire.thickness=.0007 if region=='body' else .00025;wire.use_replace=True
    return obj


for view in views:
    path=OUT/'images'/(view['id']+('-sans-ombres' if args.diagnostic_light else '')+'.png')
    if path.exists() and view['id'] in records and not args.force:continue
    case=cases[view['case']]
    if active_case!=case['id']:points=apply_case(case);active_case=case['id']
    entry=aim(view,points)
    wire=make_wire(view['region']) if view['wire'] else None
    scene.render.filepath=str(path)
    bpy.ops.render.render(write_still=True)
    if wire:
        mesh=wire.data;bpy.data.objects.remove(wire,do_unlink=True);bpy.data.meshes.remove(mesh)
    entry.update(view=view['id'],case=case['id'],render_subdivision=2,shape_schema=body.data.get('human_modeling_schema'))
    records[view['id']]=entry
    logpath.write_text(json.dumps(records,indent=2),encoding='utf-8')
    rendered+=1
    print('VALIDATION23_RENDERED',args.shard,view['id'],len(records),'/',len(views),flush=True)
    if args.limit and rendered>=args.limit:break

if not args.limit:
    case=next(c for c in plan['cases'] if c['morph']==float(args.shard) and c['age']==2 and c['profile']=='REFERENCE' and not c['controls'])
    points=apply_case(case);aim({'region':'body','yaw':0,'elevation':0},points)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA'
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/f'Revue-editable-{args.shard}.blend'),compress=True)
print('VALIDATION23_SHARD_DONE',args.shard,rendered,round(time.perf_counter()-started,1),flush=True)
