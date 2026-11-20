"""Inspect the review scene and measure guide motion under native gravity."""
from pathlib import Path
import sys,json
import bpy,numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import extension
from extension import groom
extension.register()
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'validation/groom-25/HumanLoom-groom-revue.blend'),load_ui=False)
body=next(o for o in bpy.context.scene.objects if o.get('human_modeling_body'))
hair=groom.find(body,'SCALP');scene=bpy.context.scene
out=ROOT/'validation/groom-28';out.mkdir(parents=True,exist_ok=True)
report={'original':groom.state(hair.hl_groom),'frame':scene.frame_current,'gravity':list(scene.gravity),'area_m2':hair.get('hl_mask_area_m2')}
report['profile_inputs']=[(s.name,s.socket_type,str(getattr(getattr(hair.modifiers['HumanLoom · profil'].properties.inputs,s.identifier),'value',None))) for s in hair.modifiers['HumanLoom · profil'].node_group.interface.items_tree if s.item_type=='SOCKET' and s.in_out=='INPUT']
print('ORIGINAL',json.dumps(report),flush=True)
for o in body.children:
 if o.get('hl_groom_region') and o!=hair:o.hide_set(True);o.hide_render=True
# Use representative guides rather than paying for full interpolation in a solver test.
cfg=groom.state(hair.hl_groom);cfg.update(guides=48,viewport=.1,physics='XPBD',substeps=4,iterations=4096,bendiness=.7,root_bendiness=.4,collisions=True)
hair=groom.build(body,'SCALP',cfg);hair.modifiers['HumanLoom · densité'].show_viewport=False
def coords():
 bpy.context.view_layer.update();data=hair.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
 return [np.array([p.position[:] for p in c.points]) for c in data.curves]
scene.frame_set(scene.frame_start);rest=coords();lens=np.array([np.linalg.norm(np.diff(p,axis=0),axis=1).sum() for p in rest]);roots=np.array([p[0] for p in rest]);tips=np.array([p[-1] for p in rest])
report['frames']=[]
for frame in range(scene.frame_start+1,scene.frame_start+25):
 scene.frame_set(frame);ps=coords();ls=np.array([np.linalg.norm(np.diff(p,axis=0),axis=1).sum() for p in ps]);dt=np.array([p[-1] for p in ps])-tips
 row={'frame':frame,'mean_tip_z_mm':float(dt[:,2].mean()*1000),'max_motion_mm':float(np.linalg.norm(dt,axis=1).max()*1000),'max_stretch':float(abs(ls/lens-1).max()),'max_root_mm':float(np.linalg.norm(np.array([p[0] for p in ps])-roots,axis=1).max()*1000)}
 report['frames'].append(row);print('PHYSICS28',row,flush=True)
(out/'diagnostic.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
