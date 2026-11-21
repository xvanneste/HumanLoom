"""Measure penetration against the evaluated body, including segment interiors.

Uses nearest oriented surface normals on this closed head/neck, not image pixels.
Roots and the first 2 mm are reported separately from the free strand.
"""
from pathlib import Path
import sys,json,time
import bpy,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import extension
from extension import groom
extension.register()
source=ROOT/('validation/groom-29/HumanLoom-contacts-revue.blend' if '--contacts' in sys.argv else 'validation/groom-28/HumanLoom-densite-gravite-revue.blend')
bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False)
body=next(o for o in bpy.context.scene.objects if o.get('human_modeling_body'));hair=groom.find(body,'SCALP')
OUT=ROOT/'validation/groom-29';OUT.mkdir(parents=True,exist_ok=True)
body.modifiers['Human Modeling · Surface'].levels=2
if '--no-follow-normal' in sys.argv:
 inter=next(n for n in hair.modifiers['HumanLoom · densité'].node_group.nodes if n.type=='GROUP')
 inter.inputs['Follow Surface Normal'].default_value=False
if '--follow-normal' in sys.argv:
 inter=next(n for n in hair.modifiers['HumanLoom · densité'].node_group.nodes if n.type=='GROUP')
 inter.inputs['Follow Surface Normal'].default_value=True
guard=None
if '--shrinkwrap' in sys.argv:
 guard=hair.modifiers.new('Test · protection de surface','NODES');guard.node_group=groom.native('Shrinkwrap Hair Curves')
 print('SHRINK29_INTERFACE',[(s.name,s.socket_type,str(getattr(getattr(guard.properties.inputs,s.identifier),'value',None))) for s in guard.node_group.interface.items_tree if s.item_type=='SOCKET' and s.in_out=='INPUT'],flush=True)
 for name,value,kind in [('Surface',body,'NodeSocketObject'),('Factor',1.,None),('Offset Distance',.0005,None),('Above Surface',0.,None),('Smoothing Steps',0,None),('Lock Roots',True,None)]:groom.set_input(guard,name,value,kind)
 guard.show_viewport=False
if '--adaptive' in sys.argv:
 from tools.groom_collision_guard29 import add_guard
 guard=add_guard(hair,body);guard.show_viewport=False
bpy.context.view_layer.update();graph=bpy.context.evaluated_depsgraph_get()
ev=body.evaluated_get(graph);mesh=ev.to_mesh()
bvh=BVHTree.FromPolygons([body.matrix_world@v.co for v in mesh.vertices],[p.vertices[:] for p in mesh.polygons]);ev.to_mesh_clear()
def measure(data,label):
 start=time.perf_counter();curves=list(data.curves);total=0;bad_curves=0;bad_points=0;root_depth=0.;max_depth=0.;worst=[]
 for index,c in enumerate(curves):
  ps=np.array([hair.matrix_world@p.position for p in c.points]);arc=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(ps,axis=0),axis=1))]
  samples=[(ps[0],0.)]
  for j in range(len(ps)-1):
   # Inspect the segment, not just vertices (maximum spacing 1 mm).
   count=max(1,int(np.ceil((arc[j+1]-arc[j])/.001)))
   for t in np.arange(1,count+1)/count:samples.append((ps[j]*(1-t)+ps[j+1]*t,arc[j]*(1-t)+arc[j+1]*t))
  curve_bad=False
  for p,s in samples:
   hit,n,_,dist=bvh.find_nearest(Vector(p));depth=max(0.,-(Vector(p)-hit).dot(n));total+=1
   if s<.002:root_depth=max(root_depth,depth);continue
   max_depth=max(max_depth,depth)
   if depth>.0005:
    bad_points+=1;curve_bad=True
    if len(worst)<20 or depth>worst[-1]['depth_m']:
     worst.append({'curve':index,'arc_m':float(s),'depth_m':depth,'position':p.tolist()});worst.sort(key=lambda r:-r['depth_m']);worst=worst[:20]
  bad_curves+=curve_bad
  if index and index%10000==0:print('COLLISION29_PROGRESS',label,index,flush=True)
 result={'label':label,'curves':len(curves),'samples':total,'root_zone_mm':2.,'tolerance_mm':.5,'penetrating_curves':bad_curves,'penetrating_samples':bad_points,'max_free_depth_mm':max_depth*1000,'max_root_zone_depth_mm':root_depth*1000,'worst':worst,'seconds':time.perf_counter()-start}
 print('COLLISION29',json.dumps({k:v for k,v in result.items() if k!='worst'}),flush=True);return result
report={'source':str(source.relative_to(ROOT)),'shrinkwrap':guard is not None,'method':'nearest oriented evaluated-body surface; points along segments at <=1 mm spacing','measurements':[]}
result_file=OUT/('penetration-follow-adaptive.json' if '--follow-normal' in sys.argv and '--adaptive' in sys.argv else 'penetration-follow.json' if '--follow-normal' in sys.argv else 'penetration-adaptive.json' if '--adaptive' in sys.argv else 'penetration-no-follow.json' if '--no-follow-normal' in sys.argv else 'penetration-protected.json' if guard else 'penetration-contacts.json' if '--contacts' in sys.argv else 'penetration.json')
hair.modifiers['HumanLoom · densité'].show_viewport=False;bpy.context.view_layer.update()
report['measurements'].append(measure(hair.evaluated_get(bpy.context.evaluated_depsgraph_get()).data,'simulated_guides'))
result_file.write_text(json.dumps(report,indent=2),encoding='utf-8')
if guard:guard.show_viewport=True
hair.modifiers['HumanLoom · densité'].show_viewport=True;groom.viewport_quality(hair,1.);bpy.context.view_layer.update()
report['measurements'].append(measure(hair.evaluated_get(bpy.context.evaluated_depsgraph_get()).data,'full_interpolation'))
result_file.write_text(json.dumps(report,indent=2),encoding='utf-8')
if guard:
 bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'HumanLoom-protection-revue.blend'),compress=True)
