"""Density correction and measured native gravity, in an isolated review copy."""
from pathlib import Path
import sys,json,math
import bpy,numpy as np
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import extension
from extension import groom
extension.register()
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'validation/groom-25/HumanLoom-groom-revue.blend'),load_ui=False)
body=next(o for o in bpy.context.scene.objects if o.get('human_modeling_body'))
hair=groom.find(body,'SCALP');scene=bpy.context.scene
OUT=ROOT/'validation/groom-28';OUT.mkdir(parents=True,exist_ok=True)
assert bpy.app.version[:2]==(5,2) and bpy.app.background
scene.render.resolution_x=720;scene.render.resolution_y=840;scene.render.resolution_percentage=100
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
report={'frames':[],'renders':[]}
def render(label):
 for view,yaw in [('face',0),('profil',90)]:
  if '--resume-physics' in sys.argv and label!='gravite-180' and (OUT/f'{label}-{view}.png').is_file():
   report['renders'].append({'stage':label,'view':view,'file':f'{label}-{view}.png'});continue
  target=Vector((0,-.025,1.55));direction=Vector((math.sin(math.radians(yaw)),-math.cos(math.radians(yaw)),.05))
  scene.camera.location=target+direction*3;scene.camera.rotation_euler=(target-scene.camera.location).to_track_quat('-Z','Y').to_euler();scene.camera.data.ortho_scale=.52
  scene.render.filepath=str(OUT/f'{label}-{view}.png');bpy.ops.render.render(write_still=True)
  report['renders'].append({'stage':label,'view':view,'file':f'{label}-{view}.png'})
  print('RENDER28',label,view,flush=True)
render('avant-70')
# Exercise the public correction on an existing sculpt; no reconstruction.
bpy.context.view_layer.objects.active=body;body.hl_groom_region='SCALP'
original=np.array([p.position[:] for p in hair.data.points]);old_view=hair.hl_groom.viewport
assert bpy.ops.humanloom.groom_density(preset='NORMAL')=={'FINISHED'}
assert np.array_equal(original,np.array([p.position[:] for p in hair.data.points]))
assert hair.hl_groom.viewport==old_view
assert groom.input_value(hair.modifiers['HumanLoom · densité'],'Density')==1800000.
report['density_preserves_guides_and_viewport']=True
render('densite-180')
# A bounded physical review on 128 guides, not a claim of universal calibration.
cfg=groom.state(hair.hl_groom);cfg.update(guides=128,physics='XPBD',substeps=8,iterations=4096,bendiness=.7,root_bendiness=.4,collisions=True)
report['physics_config']=cfg
hair=groom.build(body,'SCALP',cfg);hair.modifiers['HumanLoom · densité'].show_viewport=False
def coords():
 bpy.context.view_layer.update();data=hair.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
 return [np.array([p.position[:] for p in c.points]) for c in data.curves]
scene.frame_set(scene.frame_start);rest=coords();lens=np.array([np.linalg.norm(np.diff(p,axis=0),axis=1).sum() for p in rest]);roots=np.array([p[0] for p in rest]);tips=np.array([p[-1] for p in rest])
for frame in range(scene.frame_start+1,scene.frame_start+13):
 scene.frame_set(frame);ps=coords();ls=np.array([np.linalg.norm(np.diff(p,axis=0),axis=1).sum() for p in ps]);dt=np.array([p[-1] for p in ps])-tips
 row={'frame':frame,'mean_tip_z_mm':float(dt[:,2].mean()*1000),'max_motion_mm':float(np.linalg.norm(dt,axis=1).max()*1000),'max_stretch':float(abs(ls/lens-1).max()),'max_root_mm':float(np.linalg.norm(np.array([p[0] for p in ps])-roots,axis=1).max()*1000)}
 if row['max_stretch']>=.05:
  worst=int(np.argmax(abs(ls/lens-1)))
  (OUT/'failed-guide.json').write_text(json.dumps({'row':row,'settings':cfg,'index':worst,'rest':rest[worst].tolist(),'simulated':ps[worst].tolist()},indent=2),encoding='utf-8')
 assert all(np.isfinite(p).all() for p in ps) and row['max_stretch']<.05 and row['max_root_mm']<.1,row
 report['frames'].append(row);print('SIM28',row,flush=True)
 (OUT/'review.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
assert report['frames'][-1]['mean_tip_z_mm'] < -2.,'Gravity must visibly move tips down'
# Freeze the actual solver result to avoid a different render-graph simulation cache.
# No smoothing, rescaling, length repair or synthetic sag is applied after XPBD.
evaluated=hair.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.copy()
hair.data=evaluated;hair.modifiers['HumanLoom · densité'].show_viewport=True
cfg['physics']='ANIMATION';groom.configure(hair,cfg);hair.hl_groom.physics='ANIMATION'
# Evaluated guides already inhabit the current surface, not its rest space.
# Do not deform them a second time through the Animation following modifier.
follow=hair.modifiers['HumanLoom · suivi 5.2'];follow.show_viewport=False;follow.show_render=False
inter=next(n for n in hair.modifiers['HumanLoom · densité'].node_group.nodes if n.type=='GROUP')
inter.inputs['Resting Surface'].default_value=False
hair['hl_review_native_settled_frame']=scene.frame_current
report['physics_render']='Native XPBD guide result frozen after frame 13; interpolated at 180 hairs/cm². Static review, not a live simulation bake.'
render('gravite-180')
(OUT/'review.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'HumanLoom-densite-gravite-revue.blend'),compress=True)
print('REVIEW28_PASS',flush=True)
