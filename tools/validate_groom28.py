"""Check density corrections on an existing sculpt without altering other settings."""
from pathlib import Path
import sys,json
import bpy,numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import extension
from extension import groom
extension.register()
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'validation/groom-25/HumanLoom-groom-revue.blend'),load_ui=False)
body=next(o for o in bpy.context.scene.objects if o.get('human_modeling_body'))
hair=groom.find(body,'SCALP');bpy.context.view_layer.objects.active=body
body.hl_groom_region='SCALP'
hair.data.points[3].position.x+=.0002
source=np.array([p.position[:] for p in hair.data.points]);before=groom.state(hair.hl_groom)
stack=[m.name for m in hair.modifiers];mode=groom.input_value(hair.modifiers['HumanLoom · suivi 5.2'],'Mode')
level=groom.input_value(hair.modifiers['HumanLoom · densité'],'Viewport Amount')
# Unapplied settings must not accidentally be committed by a density button.
hair.hl_groom.physics='XPBD';hair.hl_groom.viewport=.87
rows=[]
for preset,value in [('SPARSE',700000.),('NORMAL',1800000.),('DENSE',2500000.)]:
 assert bpy.ops.humanloom.groom_density(preset=preset)=={'FINISHED'}
 assert groom.input_value(hair.modifiers['HumanLoom · densité'],'Density')==value
 assert hair.hl_groom.density==value
 assert groom.input_value(hair.modifiers['HumanLoom · densité'],'Viewport Amount')==level
 assert groom.input_value(hair.modifiers['HumanLoom · suivi 5.2'],'Mode')==mode
 assert np.array_equal(source,np.array([p.position[:] for p in hair.data.points]))
 assert stack==[m.name for m in hair.modifiers]
 bpy.context.view_layer.update();ev=hair.evaluated_get(bpy.context.evaluated_depsgraph_get())
 rows.append({'preset':preset,'density_per_cm2':value/10000,'viewport_curves':len(ev.data.curves)})
 assert hair.hl_groom.physics=='XPBD' and abs(hair.hl_groom.viewport-.87)<1e-6
assert rows[0]['viewport_curves']<rows[1]['viewport_curves']<rows[2]['viewport_curves']
after=groom.state(hair.hl_groom)
for key in before:
 if key not in ('density','physics','viewport'):assert after[key]==before[key],key
# A rejected expensive request must preserve the active density.
# The budget now follows the mask as painted (I-35): simulate an expensive mask by painting it to 1.0, then restore it.
body=hair.parent;group=body.vertex_groups['hl_density_scalp']
saved=[next((g.weight for g in v.groups if g.group==group.index),0.) for v in body.data.vertices]
group.add(list(range(len(saved))),1.,'REPLACE')
try:
 try:bpy.ops.humanloom.groom_density(preset='NORMAL')
 except RuntimeError:pass  # Blender exposes an operator ERROR report this way.
 assert groom.input_value(hair.modifiers['HumanLoom · densité'],'Density')==2500000.
 assert hair.hl_groom.density==2500000.
finally:
 for index,weight in enumerate(saved):group.add([index],weight,'REPLACE')
assert groom.defaults('SCALP')['density']==1800000.
assert mode=='Animation',repr(mode)
cfg=groom.state(hair.hl_groom);cfg.update(physics='XPBD')
groom.configure(hair,cfg)
assert groom.input_value(hair.modifiers['HumanLoom · suivi 5.2'],'Mode')=='Physics (Experimental)'
cfg['physics']='ANIMATION';groom.configure(hair,cfg)
assert groom.input_value(hair.modifiers['HumanLoom · suivi 5.2'],'Mode')=='Animation'
report={'cases':rows,'sculpt_preserved':True,'material_and_physics_preserved':True,'pending_settings_not_applied':True,'budget_rejection_preserves_density':True,'native_mode_status_verified':True}
out=ROOT/'validation/groom-28';out.mkdir(exist_ok=True)
(out/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('VALIDATE28_PASS',report,flush=True)
