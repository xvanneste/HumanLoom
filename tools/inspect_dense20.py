from pathlib import Path
import bpy,numpy as np
p=Path('C:/Users/xvann/OneDrive/Documents/ChatGPT/BlenderDev/validation/cheveux-20/Prototype-cheveux-01.blend');bpy.ops.wm.open_mainfile(filepath=str(p));h=next(o for o in bpy.context.scene.objects if o.get('hm_hair_prototype'))
for i in range(len(h.modifiers)+1):
 for j,m in enumerate(h.modifiers):m.show_viewport=j<i
 h.update_tag();bpy.context.view_layer.update();d=h.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
 pts=np.array([v.position[:] for v in d.points]);roots=np.array([pts[c.first_point_index] for c in d.curves])
 print('STAGE',i,[m.name for m in h.modifiers if m.show_viewport],len(d.curves),'PTS',pts.min(0),pts.max(0),'ROOTS',roots.min(0),roots.max(0),'ATTRS',[(a.name,a.data_type) for a in d.attributes],flush=True)
 print('MAT',[m.name for m in d.materials],flush=True)
