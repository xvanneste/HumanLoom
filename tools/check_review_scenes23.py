"""Reopen both standalone review scenes without touching their contents."""
from pathlib import Path
import sys,json
import bpy
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import extension as addon
addon.register()
out=ROOT/'validation/planches-modelisation-23'
results=[]
for index in (0,1):
    path=out/f'Revue-editable-{index}.blend'
    bpy.ops.wm.open_mainfile(filepath=str(path),load_ui=False)
    bodies=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.data.get('human_modeling_schema')==9]
    assert len(bodies)==1
    body=bodies[0];keys=body.data.shape_keys
    assert len([name for name in keys.keys() if name.startswith('hm_')])==48
    assert keys.key_blocks['Morphologie'].value==index
    assert keys['human_modeling_age']==2
    assert not any(o.type=='ARMATURE' for o in bpy.context.scene.objects)
    bpy.context.view_layer.update()
    deps=bpy.context.evaluated_depsgraph_get();mesh=body.evaluated_get(deps)
    assert len(mesh.data.vertices)>len(body.data.vertices)
    invalid=[d.data_path for d in keys.animation_data.drivers if not d.driver.is_valid]
    assert not invalid,invalid
    assert bpy.context.scene.camera is not None
    results.append({'file':path.name,'controls':48,'schema':9,'evaluated_vertices':len(mesh.data.vertices),'invalid_drivers':invalid})
(out/'verification-scenes.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
print('REVIEW_SCENES_VERIFIED',results)
