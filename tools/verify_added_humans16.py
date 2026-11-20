"""Reopen the audit deliverables; verify displayed comparison dimensions."""
from pathlib import Path
import json,bpy,numpy as np
root=Path(__file__).resolve().parents[1]/'validation/references-humaines-16';rows=[]
for label in ('homme-stylise','femme-yoga','comparaison-masculine-normalisee'):
    path=root/f'{label}-inspection.blend';bpy.ops.wm.open_mainfile(filepath=str(path))
    scene=bpy.context.scene;assert scene.camera and scene.camera.data.type=='ORTHO'
    meshes=[o for o in scene.objects if o.type=='MESH'];assert meshes
    row={'scene':path.name,'mesh_objects':len(meshes),'orthographic_camera':True,'reopen':'pass'}
    if label.startswith('comparaison'):
        bodies=[o for o in meshes if o.name.startswith(('Notre candidat','Référence ajoutée'))];assert len(bodies)==2
        heights={}
        for body in bodies:
            obj=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=obj.to_mesh()
            try:height=float(np.ptp([float((body.matrix_world@v.co).z) for v in mesh.vertices]))
            finally:obj.to_mesh_clear()
            assert abs(height-1.8)<1e-4,(body.name,height);heights[body.name]=height
        row['normalized_heights']=heights
    rows.append(row)
(root/'controle-reouverture.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print('ADDED_REFERENCE_SCENES_REOPEN_PASS',flush=True)
