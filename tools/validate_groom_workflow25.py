"""Exercise public operators, editable sculpt preservation, JSON and native XPBD."""
from pathlib import Path
import sys,json
import bpy,numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import extension as addon
from extension import groom
OUT=ROOT/'validation/groom-25';OUT.mkdir(parents=True,exist_ok=True)
addon.register()
for o in tuple(bpy.context.scene.objects):bpy.data.objects.remove(o,do_unlink=True)
bpy.ops.human_modeling.create();body=bpy.context.object
cfg=groom.defaults('SCALP');cfg.update(guides=20,length=.06,nature=0.,style='UPRIGHT',viewport=.1,density=120000.)
hair=groom.build(body,'SCALP',cfg)
# Rebuilding while the guide object is active must keep the character UI usable.
assert bpy.ops.humanloom.groom_select()=={'FINISHED'}
assert bpy.context.object==hair
assert bpy.ops.humanloom.groom_build()=={'FINISHED'}
hair=groom.find(body,'SCALP');assert bpy.context.object==hair and groom.body_from(bpy.context)==body
hair.select_set(False);body.select_set(True);bpy.context.view_layer.objects.active=body
hair.data.points[3].position.x+=.0002
sculpt=np.array([p.position[:] for p in hair.data.points])
hair.hl_groom.color=(.1,.02,.01);hair.hl_groom.grey=.5;hair.hl_groom.radius=.00009
assert bpy.ops.humanloom.groom_apply()=={'FINISHED'}
assert np.array_equal(sculpt,np.array([p.position[:] for p in hair.data.points]))
assert groom.state(hair.hl_groom)['grey']==.5
path=OUT/'groom-workflow-preset.json'
assert bpy.ops.humanloom.groom_export(filepath=str(path))=={'FINISHED'}
payload=json.loads(path.read_text(encoding='utf-8'));assert payload['layers']['SCALP']['grey']==.5
bpy.ops.human_modeling.create();second=bpy.context.object;second.location.x=2.
assert bpy.ops.humanloom.groom_import(filepath=str(path))=={'FINISHED'}
copy=groom.find(second,'SCALP');assert copy and copy!=hair and copy.parent==second
# No shared material: changing the second character cannot recolor the first.
assert copy.data.materials[0]!=hair.data.materials[0]
assert groom.find(body,'SCALP')==hair
second.location=(1,.4,.2);second.rotation_euler=(.1,.2,.3);second.scale=(1.2,1.2,1.2)
bpy.context.view_layer.update();assert np.allclose(np.array(copy.matrix_world),np.array(second.matrix_world))
rootid=np.array([a.vector[:] for a in copy.data.attributes['surface_uv_coordinate'].data])
# Test actual native Physics, on guides before render interpolation.
config=groom.state(copy.hl_groom);config.update(physics='XPBD',substeps=4,iterations=4096,collisions=False)
groom.appearance(copy,config);copy.modifiers['HumanLoom · densité'].show_viewport=False
scene=bpy.context.scene;scene.frame_start=1;scene.frame_end=16
def coords():
    bpy.context.view_layer.update();data=copy.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
    return [np.array([p.position[:] for p in c.points]) for c in data.curves]
scene.frame_set(1);rest=coords();baseline=np.array([np.linalg.norm(np.diff(p,axis=0),axis=1).sum() for p in rest]);roots=np.array([p[0] for p in rest]);rows=[]
for frame in range(2,17):
    scene.frame_set(frame);curves=coords()
    assert len(curves)==len(rest)
    lengths=np.array([np.linalg.norm(np.diff(p,axis=0),axis=1).sum() for p in curves])
    assert all(np.isfinite(p).all() for p in curves)
    row={'frame':frame,'max_stretch_fraction':float(np.max(abs(lengths/baseline-1))),'max_root_m':float(np.linalg.norm(np.array([p[0] for p in curves])-roots,axis=1).max())}
    rows.append(row);print('GROOM25_XPBD',row,flush=True)
assert max(r['max_stretch_fraction'] for r in rows)<.05
assert max(r['max_root_m'] for r in rows)<.001
assert np.array_equal(rootid,np.array([a.vector[:] for a in copy.data.attributes['surface_uv_coordinate'].data]))
# Return to normal following, verifying the order is reversible.
config['physics']='ANIMATION';groom.appearance(copy,config);assert copy.modifiers[0].name=='HumanLoom · densité'
report={'appearance_preserves_sculpt':True,'json_roundtrip':True,'two_characters_independent':True,'parent_transform_preserved':True,'xpbd_guides_before_interpolation':True,'xpbd_scope':'20 straight 6 cm guides, 16 frames, gravity, no collisions; not a general material calibration','xpbd':rows}
(OUT/'validation-workflow.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('GROOM25_WORKFLOW_PASS',flush=True)
