from pathlib import Path
import json,bpy,numpy as np
root=Path(__file__).resolve().parents[1]/'validation/unreal-17';rows=[]
exports=json.loads((root/'metahuman-cpu-export-report.json').read_text(encoding='utf-8'))['characters']
for name,label in (('MHC_Base_Female','MetaHuman-feminin'),('MHC_Base_Male','MetaHuman-masculin')):
    source=next(row for row in exports if row['character']==name);assert source['status']=='exported'
    path=root/'blender'/f'{label}-inspection.blend';bpy.ops.wm.open_mainfile(filepath=str(path))
    bodies=[o for o in bpy.context.scene.objects if o.type=='MESH'];assert len(bodies)==1
    body=bodies[0];assert len(body.data.vertices)==source['vertices'] and len(body.data.polygons)==source['triangles']
    p=np.array([body.matrix_world@v.co for v in body.data.vertices]);assert np.isfinite(p).all()
    extent=np.ptp(p,axis=0);assert extent[0]>extent[1] and extent[2]>.5
    assert bpy.context.scene.camera.data.type=='ORTHO'
    for view in ('face','profil','dos','trois-quarts'):assert (root/'blender'/f'{label}-{view}.png').stat().st_size>1000
    rows.append({'character':name,'reopen':'pass','vertices':len(body.data.vertices),'triangles':len(body.data.polygons),'world_extents_m':extent.tolist(),'four_orthographic_images':True})
(root/'controle-blender-reouverture.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print('METAHUMAN_EXPORTS_REOPEN_PASS',flush=True)
