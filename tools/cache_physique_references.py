"""Study licensed reference shapes independently of our procedural fields.

MPFB is a build-time tool only. Exported reference geometry is CC0, not a
measured biological dataset; it must not be confused with ANSUR observations.
"""
from pathlib import Path
import sys,json
import bpy,addon_utils
import numpy as np

NAMES=('joint-l-shoulder','joint-l-elbow','joint-l-hand','joint-pelvis','joint-l-knee','joint-l-ankle','joint-neck','joint-l-upper-leg','joint-jaw')
PROFILES={'reference':(.5,.5),'thin':(.10,.50),'fat':(.90,.50),'muscle':(.50,.90),'muscle_low':(.50,.10),'fat_muscle':(.90,.90),'thin_low':(.10,.10)}

output=Path(sys.argv[sys.argv.index('--')+1]).resolve();output.parent.mkdir(parents=True,exist_ok=True)
addon_utils.enable('bl_ext.user_default.mpfb',default_set=True)
from bl_ext.user_default.mpfb.services import HumanService,TargetService
values={'joint_names':np.array(NAMES)};meta=[]
for sex in (0,1):
    for profile,(weight,muscle) in PROFILES.items():
        settings=TargetService.get_default_macro_info_dict()
        settings.update(age=.5+5/130,gender=sex,weight=weight,muscle=muscle)
        obj=HumanService.create_human(macro_detail_dict=settings)
        graph=bpy.context.evaluated_depsgraph_get();bpy.context.view_layer.update()
        evaluated=obj.evaluated_get(graph);mesh=evaluated.to_mesh();mesh.calc_loop_triangles()
        points=np.array([v.co[:] for v in mesh.vertices]);faces=np.array([t.vertices[:] for t in mesh.loop_triangles])
        evaluated.to_mesh_clear()
        for modifier in obj.modifiers:modifier.show_viewport=False
        bpy.context.view_layer.update();evaluated=obj.evaluated_get(graph);mesh=evaluated.to_mesh()
        joints=[]
        for name in NAMES:
            group=obj.vertex_groups[name]
            indices=[v.index for v in obj.data.vertices if any(g.group==group.index for g in v.groups)]
            joints.append(np.array([mesh.vertices[i].co[:] for i in indices]).mean(0))
        evaluated.to_mesh_clear()
        key=f'{sex}_{profile}'
        values['points_'+key]=points;values['triangles_'+key]=faces;values['joints_'+key]=np.array(joints)
        meta.append({'sex':sex,'profile':profile,'source_macro_weight':weight,'source_macro_muscle':muscle,'height_m':float(np.ptp(points[:,2]))})
        bpy.data.objects.remove(obj,do_unlink=True)
        print('PHYSIQUE_REFERENCE',key,len(points),flush=True)
np.savez_compressed(output,**values)
output.with_suffix('.json').write_text(json.dumps({'source':'MPFB 2.0.18 / MakeHuman CC0 artist-authored shapes; not clinical observations','joint_names':NAMES,'profiles':meta},indent=2),encoding='utf-8')
