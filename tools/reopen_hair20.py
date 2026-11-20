from pathlib import Path
import bpy,numpy as np,json,hashlib
root=Path('C:/Users/xvann/OneDrive/Documents/ChatGPT/BlenderDev');p=root/'validation/cheveux-20/Prototype-cheveux-01.blend';rows=[]
for i in range(2):
 bpy.ops.wm.open_mainfile(filepath=str(p));h=next(o for o in bpy.context.scene.objects if o.get('hm_hair_prototype'));bpy.context.view_layer.update();d=h.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
 a=np.array([v.vector[:] for v in d.attributes['surface_uv_coordinate'].data]);pos=np.array([v.position[:] for v in d.points]);print('REOPEN',i,len(d.curves),flush=True)
 rows.append({'strands':len(d.curves),'uv_sha256':hashlib.sha256(a.tobytes()).hexdigest(),'guides':len(h.data.curves)})
assert rows[0]==rows[1],rows
(root/'validation/cheveux-20/reouverture-01.json').write_text(json.dumps({'pass':True,'runs':rows},indent=2),encoding='utf-8');print('REOPEN_HAIR20_PASS',flush=True)
