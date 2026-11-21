"""Native XPBD contact test; no post-solver projection or length repairs."""
from pathlib import Path
import sys,json,math
import bpy,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import extension
from extension import groom
extension.register()
OUT=ROOT/'validation/groom-29';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'validation/groom-25/HumanLoom-groom-revue.blend'),load_ui=False)
body=next(o for o in bpy.context.scene.objects if o.get('human_modeling_body'));scene=bpy.context.scene
cfg=groom.defaults('SCALP');cfg.update(guides=128,physics='XPBD',substeps=8,iterations=4096,bendiness=.7,root_bendiness=.4,collisions=True)
hair=groom.build(body,'SCALP',cfg)
groom.set_input(hair.modifiers['HumanLoom · suivi 5.2'],'Edge Contacts',True)
hair.modifiers['HumanLoom · densité'].show_viewport=False
def coords():
 bpy.context.view_layer.update();data=hair.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
 return [np.array([p.position[:] for p in c.points]) for c in data.curves]
scene.frame_set(1);rest=coords();lens=np.array([np.linalg.norm(np.diff(p,axis=0),axis=1).sum() for p in rest]);roots=np.array([p[0] for p in rest]);tips=np.array([p[-1] for p in rest])
graph=bpy.context.evaluated_depsgraph_get();ev=body.evaluated_get(graph);mesh=ev.to_mesh()
bvh=BVHTree.FromPolygons([v.co[:] for v in mesh.vertices],[p.vertices[:] for p in mesh.polygons]);ev.to_mesh_clear()
report={'edge_contacts':True,'frames':[],'settings':cfg}
def penetration(curves):
 maximum=0.;bad=0
 for p in curves:
  arc=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))];depth=0.
  for j in range(len(p)-1):
   n=max(1,math.ceil((arc[j+1]-arc[j])/.001))
   for t in np.arange(n+1)/n:
    if arc[j]*(1-t)+arc[j+1]*t<.002:continue
    v=Vector(p[j]*(1-t)+p[j+1]*t);hit,normal,_,_=bvh.find_nearest(v)
    depth=max(depth,-(v-hit).dot(normal))
  maximum=max(maximum,depth);bad+=depth>.0005
 return maximum*1000,bad
for frame in range(2,14):
 scene.frame_set(frame);ps=coords();ls=np.array([np.linalg.norm(np.diff(p,axis=0),axis=1).sum() for p in ps]);depth,bad=penetration(ps)
 row={'frame':frame,'max_stretch':float(abs(ls/lens-1).max()),'root_motion_mm':float(np.linalg.norm(np.array([p[0] for p in ps])-roots,axis=1).max()*1000),'mean_tip_z_mm':float((np.array([p[-1] for p in ps])-tips)[:,2].mean()*1000),'max_depth_mm':depth,'penetrating_guides':bad}
 assert all(np.isfinite(p).all() for p in ps) and row['max_stretch']<.05,row
 report['frames'].append(row);print('CONTACT29',row,flush=True)
 (OUT/'native-contacts.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
# Freeze native coordinates, keeping current-surface interpolation and no second follow.
data=hair.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.copy();hair.data=data
follow=hair.modifiers['HumanLoom · suivi 5.2'];follow.show_viewport=False;follow.show_render=False
hair.modifiers['HumanLoom · densité'].show_viewport=True;groom.viewport_quality(hair,1.)
hair['hl_review_native_settled_frame']=13
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'HumanLoom-contacts-revue.blend'),compress=True)
print('CONTACT29_DONE',flush=True)
