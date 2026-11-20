"""Transport diagnostics on existing artistic ages, without adult norm transfer."""
from pathlib import Path
import sys,json,importlib
import bpy,numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from build_surface_atlas15 import position
from surface_frames15 import derive

root=Path(__file__).resolve().parents[1];folder=root/'validation/atlas-15'
atlas=json.loads((folder/'atlas-candidat-01.json').read_text(encoding='utf-8'))
addon=importlib.import_module('bl_ext.user_default.human_modeling')
addon.ASSET_PATH=root/'validation/proportions-14/extension-13/data/realistic.blend'
bpy.ops.human_modeling.create();body=bpy.context.object;keys=body.data.shape_keys
for mod in body.modifiers:mod.show_viewport=False
body.data.calc_loop_triangles();faces=np.array([t.vertices[:] for t in body.data.loop_triangles]);rows=[]
for sex in (0,1):
    keys.key_blocks['Morphologie'].value=sex
    for stage,age in enumerate((5,15,30,75)):
        keys['human_modeling_age']=float(stage);keys.update_tag();bpy.context.view_layer.update()
        obj=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=obj.to_mesh()
        try:points=np.array([v.co[:] for v in mesh.vertices])
        finally:obj.to_mesh_clear()
        assert len(points)==len(body.data.vertices) and np.isfinite(points).all()
        anchors={k:position(points,v) for k,v in atlas['anchors'].items()}
        row={'sex':sex,'age_preset':age,'attachment':'pass','landmark_positions_m':{k:p.tolist() for k,p in anchors.items()}}
        try:
            joints,report=derive(points,faces,atlas);row['frame_diagnostic']=report;row['frames']='computed'
        except (ValueError,AssertionError) as error:row['frames']='needs_review';row['reason']=str(error)
        rows.append(row);print('ATLAS_AGE_TRANSPORT',sex,age,row['frames'],flush=True)
(folder/'controle-transport-ages-01.json').write_text(json.dumps({'cases':rows,'scope':'Topology attachment and geometric diagnostics only. Existing age shapes remain artistic; adult ANSUR norms are not transferred to children, adolescents or seniors.'},indent=2),encoding='utf-8')
