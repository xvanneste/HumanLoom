from pathlib import Path
import sys,json
import bpy,numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
import audit_added_humans16 as audit
root=Path(__file__).resolve().parents[1];audit.OUT=root/'validation/muscles-regionaux-18/apercus';audit.OUT.mkdir(parents=True,exist_ok=True)
for sex,label in ((0,'Feminin'),(1,'Masculin')):
    for obj in tuple(bpy.context.scene.objects):bpy.data.objects.remove(obj,do_unlink=True)
    bodies=[];chunks=[]
    for i,amount in enumerate((0.,1.)):
        bpy.ops.human_modeling.create();body=bpy.context.object;body.name=label+(' · Neutre' if i==0 else ' · Muscles')
        keys=body.data.shape_keys;keys.key_blocks['Morphologie'].value=sex;keys['human_modeling_age']=2.;keys['hm_muscles']=amount
        body.modifiers['Human Modeling · Surface'].levels=2;body.location.x=(i-.5)*1.1
        keys.update_tag();bpy.context.view_layer.update();obj=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=obj.to_mesh()
        try:chunks.append(np.array([body.matrix_world@v.co for v in mesh.vertices]))
        finally:obj.to_mesh_clear()
        bodies.append(body)
    audit.render(label+'-neutre-muscles',bodies,np.concatenate(chunks),paired=True)
print('MUSCLE_PAIRS18_RENDERED',flush=True)
