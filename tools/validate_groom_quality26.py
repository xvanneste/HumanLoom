"""Measure real VIEWPORT and RENDER dependency graphs, not UI labels."""
from pathlib import Path
import sys,json,hashlib
import bpy,numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import extension
from extension import groom
OUT=ROOT/'validation/groom-quality-26';OUT.mkdir(parents=True,exist_ok=True)
extension.register()
for obj in tuple(bpy.context.scene.objects):bpy.data.objects.remove(obj,do_unlink=True)
bpy.ops.human_modeling.create();body=bpy.context.object
# Compare at identical surface resolution; subdivision also changes sampling area.
body.modifiers['Human Modeling · Surface'].levels=2
body.modifiers['Human Modeling · Surface'].render_levels=2
cfg=groom.defaults('SCALP');cfg.update(guides=30,density=120000.,viewport=.1)
hair=groom.build(body,'SCALP',cfg)
beard=groom.build(body,'BEARD',{**groom.defaults('BEARD'),'guides':30,'density':90000.,'viewport':.3})
def signature(obj):return hashlib.sha256(np.array([p.position[:] for p in obj.data.points]).tobytes()).hexdigest()
source=signature(hair);rows=[];render_counts=[]

class HL_QualityProbe(bpy.types.RenderEngine):
    bl_idname='HL_QUALITY_PROBE';bl_label='HumanLoom test render graph';bl_use_preview=False
    def render(self,depsgraph):
        assert depsgraph.mode=='RENDER'
        data=hair.evaluated_get(depsgraph).data
        render_counts.append(len(data.curves))
        result=self.begin_result(0,0,4,4);self.end_result(result)

bpy.utils.register_class(HL_QualityProbe)
scene=bpy.context.scene;scene.render.engine='HL_QUALITY_PROBE';scene.render.resolution_x=4;scene.render.resolution_y=4;scene.render.resolution_percentage=100
camera=bpy.data.objects.new('Quality probe',bpy.data.cameras.new('Quality probe'));scene.collection.objects.link(camera);scene.camera=camera
for amount in (0.,.1,.5,1.):
    groom.viewport_quality(hair,amount);bpy.context.view_layer.update()
    graph=bpy.context.evaluated_depsgraph_get();assert graph.mode=='VIEWPORT'
    viewport=len(hair.evaluated_get(graph).data.curves)
    bpy.ops.render.render()
    row={'viewport_fraction':amount,'viewport_curves':viewport,'render_curves':render_counts[-1]};rows.append(row)
    assert signature(hair)==source
    print('QUALITY26_CASE',row,flush=True)
assert len(set(r['render_curves'] for r in rows))==1
assert rows[0]['viewport_curves']<rows[1]['viewport_curves']<rows[2]['viewport_curves']<=rows[3]['viewport_curves']
assert rows[3]['viewport_curves']==rows[3]['render_curves']
# The real render-density control changes the final graph independently.
cfg=groom.state(hair.hl_groom);cfg['density']=240000.;cfg['viewport']=.1
for key,value in cfg.items():setattr(hair.hl_groom,key,value)
groom.appearance(hair,cfg);bpy.context.view_layer.update();bpy.ops.render.render()
assert render_counts[-1]>rows[0]['render_curves']*1.7
# Per-zone and character-wide quick presets, including physics settings untouched.
body.hl_groom_region='SCALP';bpy.context.view_layer.objects.active=body;body.select_set(True)
dynamics=hair.modifiers['HumanLoom · suivi 5.2'];mode=groom.input_value(dynamics,'Mode');order=[m.name for m in hair.modifiers]
beard_before=groom.input_value(beard.modifiers['HumanLoom · densité'],'Viewport Amount')
assert bpy.ops.humanloom.groom_quality(preset='LIGHT')=={'FINISHED'}
assert groom.input_value(beard.modifiers['HumanLoom · densité'],'Viewport Amount')==beard_before
assert bpy.ops.humanloom.groom_quality(preset='BALANCED',all_layers=True)=={'FINISHED'}
assert abs(hair.hl_groom.viewport-.3)<1e-6 and abs(beard.hl_groom.viewport-.3)<1e-6
assert groom.input_value(dynamics,'Mode')==mode and [m.name for m in hair.modifiers]==order
assert signature(hair)==source
# Existing v1 groom presets continue to round-trip without a schema change.
assert set(groom.state(hair.hl_groom))==set(cfg)
scene.render.engine='CYCLES';bpy.utils.unregister_class(HL_QualityProbe)
report={'version':'0.15.1','cases':rows,'doubled_density_render_curves':render_counts[-1],'render_independent_from_viewport':True,'guides_unchanged':True,'per_zone_and_all_zone_presets':True,'dynamics_and_stack_unchanged':True}
(OUT/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Qualite-viewport-rendu.blend'),compress=True)
print('QUALITY26_PASS',report,flush=True)
