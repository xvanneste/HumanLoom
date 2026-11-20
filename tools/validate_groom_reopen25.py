"""Reopen a delivered scene, check native dependencies and painted-mask failure."""
from pathlib import Path
import sys,json,hashlib
import bpy,numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import extension as addon
from extension import groom
OUT=ROOT/'validation/groom-25'
addon.register();bpy.ops.wm.open_mainfile(filepath=str(OUT/'HumanLoom-groom-revue.blend'),load_ui=False)
body=next(o for o in bpy.context.scene.objects if o.get('human_modeling_body'))
hairs=[o for o in body.children if o.get('hl_groom_region')]
assert len(hairs)==9
seen=set()
def local(tree):
    if tree.as_pointer() in seen:return
    seen.add(tree.as_pointer());assert tree.library is None,tree.name
    for node in tree.nodes:
        if node.type=='GROUP' and node.node_tree:local(node.node_tree)
rows=[]
for h in hairs:
    assert len(h.data.curves)>0 and h.data.surface==body
    assert len(h.data.attributes['surface_uv_coordinate'].data)==len(h.data.curves)
    groom.validate(groom.state(h.hl_groom))
    for m in h.modifiers:
        if m.type=='NODES':local(m.node_group)
    bpy.context.view_layer.update();data=h.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
    assert len(data.curves)>0 and np.isfinite(np.array([p.position[:] for p in data.points])).all()
    rows.append({'region':h['hl_groom_region'],'guides':len(h.data.curves),'evaluated_curves':len(data.curves)})
for m in body.modifiers:
    if m.type=='NODES':local(m.node_group)
assert len({h.data.materials[0].as_pointer() for h in hairs})==len(hairs)
assert all(body.vertex_groups.get('hl_density_'+h['hl_groom_region'].lower()) for h in hairs)
hair=groom.find(body,'SCALP');cfg=groom.state(hair.hl_groom)
# Refuse an empty painted mask without removing the existing layer.
painted=body.vertex_groups['hl_density_scalp'];painted.remove(list(range(len(body.data.vertices))))
try:groom.build(body,'SCALP',cfg)
except ValueError:pass
else:raise AssertionError('Empty painted mask accepted')
assert groom.find(body,'SCALP')==hair
# Registration lifecycle used by installing and reloading an extension.
addon.unregister();addon.register()
assert hasattr(bpy.types.Object,'hl_groom') and hasattr(bpy.types.Object,'hl_groom_region')
report={'reopened':True,'native_dependencies_local':True,'settings_restored':True,'independent_materials':True,'empty_mask_preserves_existing':True,'registration_roundtrip':True,'node_groups_checked':len(seen),'layers':rows,'asset_sha256':hashlib.sha256((ROOT/'extension/data/realistic.blend').read_bytes()).hexdigest()}
assert report['asset_sha256']=='0eb9600a06f46d43f17ba5579afdc6614dbe82c450e069bff0f4fe87d33e3413'
(OUT/'validation-reopen.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('GROOM25_REOPEN_PASS',report,flush=True)
