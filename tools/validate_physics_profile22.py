"""Check profile validation and rejection without mutating the saved styles."""
from pathlib import Path
import sys,json
import bpy,numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
import hair_prototype20 as h20
from hair_physics22 import configure_benchmark

bpy.ops.wm.open_mainfile(filepath=str(h20.ROOT/'validation/nature-cheveux-21/Prototype-nature-cheveux-02.blend'))
rows=[]
for source in [o for o in bpy.context.scene.objects if 'hm_hair_nature' in o]:
    copy=source.copy();copy.data=source.data.copy()
    data=np.array([p.position[:] for p in copy.data.points])
    modifier=next(m for m in copy.modifiers if m.type=='NODES' and m.node_group and m.node_group.name.split('.')[0]=='Hair Dynamics')
    def snapshot():
        return [(item.identifier,getattr(modifier.properties.inputs,item.identifier).value) for item in modifier.node_group.interface.items_tree if item.item_type=='SOCKET' and item.in_out=='INPUT' and item.socket_type in ('NodeSocketMenu','NodeSocketBool','NodeSocketFloat','NodeSocketInt')]
    before=snapshot()
    try:
        profile=configure_benchmark(copy)
        assert source['hm_hair_nature']==0.
        rows.append({'nature':source['hm_hair_nature'],'accepted':True,'profile':profile})
    except ValueError as exc:
        assert source['hm_hair_nature']>0.
        assert snapshot()==before,'Rejected style changed modifier settings'
        rows.append({'nature':source['hm_hair_nature'],'accepted':False,'reason':str(exc),'modifier_settings_unchanged':True})
    assert np.array_equal(data,np.array([p.position[:] for p in copy.data.points]))
    original=next(m for m in source.modifiers if m.type=='NODES' and m.node_group and m.node_group.name.split('.')[0]=='Hair Dynamics')
    mode=next(i for i in original.node_group.interface.items_tree if i.item_type=='SOCKET' and i.in_out=='INPUT' and i.name=='Mode')
    assert getattr(original.properties.inputs,mode.identifier).value=='Animation'
assert sum(row['accepted'] for row in rows)==1
(h20.ROOT/'validation/physique-cheveux-22/validation-profil.json').write_text(json.dumps({'variants':rows,'source_styles_preserved':True,'pass':True},indent=2),encoding='utf-8')
print('PHYSICS22_PROFILE_GUARD_PASS',len(rows),flush=True)
