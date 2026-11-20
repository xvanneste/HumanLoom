"""Replace adult global/regional muscle contributions coherently; keep neutral."""
from pathlib import Path
import sys,json
import bpy,numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from experimental_age_transfer import coordinates,write_key
from regional_muscle_fields18 import fields,REGIONS

ROOT=Path(__file__).resolve().parents[1]

def cage(body):
    body.data.shape_keys.update_tag();bpy.context.view_layer.update()
    obj=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=obj.to_mesh()
    try:return np.array([v.co[:] for v in mesh.vertices])
    finally:obj.to_mesh_clear()

def bind(key,keys,region,correction):
    driver=key.driver_add('value').driver;driver.type='SCRIPTED'
    for var in tuple(driver.variables):driver.variables.remove(var)
    for name,path in (('overall','["hm_muscles"]'),('local',f'["hm_muscles_{region}"]'),('age','["human_modeling_age"]'),('fat','["hm_adiposity"]'),('morph','key_blocks["Morphologie"].value')):
        var=driver.variables.new();var.name=name;var.type='SINGLE_PROP';var.targets[0].id_type='KEY';var.targets[0].id=keys;var.targets[0].data_path=path
    amount='min(max(overall+local,-1),1)'
    driver.expression=f'(max({amount},0)+.35*min({amount},0))*max(0,1-abs(age-2))*(1-.35*max(fat,0))'+('*morph' if correction else '')

def main():
    output=Path(sys.argv[sys.argv.index('--')+1]).resolve();output.parent.mkdir(parents=True,exist_ok=True)
    with bpy.data.libraries.load(str(ROOT/'validation/proportions-14/candidat-adulte-15.blend'),link=False) as (_,target):target.collections=['Realistic Human Base']
    col=target.collections[0];bpy.context.scene.collection.children.link(col)
    body=next(o for o in col.objects if o.get('human_modeling_body'));keys=body.data.shape_keys
    # The adult research candidate disabled legacy whole-body fields outright.
    # Restore them outside the adult anchor before any distributable merge, so
    # child, teen and senior controls keep their existing behavior.
    with bpy.data.libraries.load(str(ROOT/'validation/proportions-14/extension-13/data/realistic.blend'),link=False) as (_,legacy):legacy.collections=['Realistic Human Base']
    old_body=next(o for o in legacy.collections[0].objects if o.get('human_modeling_body'))
    old_expressions={d.data_path:d.driver.expression for d in old_body.data.shape_keys.animation_data.drivers}
    for curve in keys.animation_data.drivers:
        if curve.driver.expression=='0' and curve.data_path in old_expressions and any(term in curve.data_path for term in ('whole_body ·','anatomical_bony_surface','anatomical_muscle_surface')):
            var=curve.driver.variables.new();var.name='adult_stage';var.type='SINGLE_PROP';var.targets[0].id_type='KEY';var.targets[0].id=keys;var.targets[0].data_path='["human_modeling_age"]'
            curve.driver.expression='('+old_expressions[curve.data_path]+')*(1-max(0,1-abs(adult_stage-2)))'
    modifier_visibility=[(mod,mod.show_viewport) for mod in body.modifiers]
    for mod,_ in modifier_visibility:mod.show_viewport=False
    keys['human_modeling_age']=2.;keys['hm_muscles']=0.;keys['hm_whole_body']=0.
    for region in REGIONS:keys['hm_muscles_'+region]=0.
    body.data.calc_loop_triangles();faces=np.array([t.vertices[:] for t in body.data.loop_triangles])
    atlas=json.loads((ROOT/'validation/atlas-15/atlas-candidat-01.json').read_text(encoding='utf-8'))
    basis=coordinates(keys.key_blocks[0]);neutral=[];values=[];reports=[]
    for sex in (0,1):
        keys.key_blocks['Morphologie'].value=sex;p=cage(body);neutral.append(p)
        muscle,report=fields(p,faces,atlas);values.append(muscle);report['sex']=sex;reports.append(report)
    retired=[]
    for curve in tuple(keys.animation_data.drivers):
        path=curve.data_path
        if 'key_blocks["HM · muscles_' in path:
            var=curve.driver.variables.new();var.name='adult_stage';var.type='SINGLE_PROP';var.targets[0].id_type='KEY';var.targets[0].id=keys;var.targets[0].data_path='["human_modeling_age"]'
            curve.driver.expression='('+curve.driver.expression+')*(1-max(0,1-abs(adult_stage-2)))';retired.append(path)
        elif 'key_blocks["HM · Atlas14 · ' in path and any((' · '+name+'"' in path or ' · '+name+' · correction"' in path) for name in ('muscle_gain','muscle_perte','fat_muscle','thin_low')):
            curve.driver.expression='0';retired.append(path)
    for region in REGIONS:
        f,m=values[0][region],values[1][region]
        for correction,delta in ((False,f),(True,m-f)):
            key=write_key(body,'HM · Muscles18 · '+region+(' · correction' if correction else ''),basis+delta)
            key.slider_min=-1.;key.slider_max=1.;bind(key,keys,region,correction)
    errors=[]
    for sex in (0,1):
        keys.key_blocks['Morphologie'].value=sex;error=float(abs(cage(body)-neutral[sex]).max());errors.append(error);assert error<1e-7,error
    body['hm_regional_muscles_candidate']='Regional adult muscles 18: native neutral retained; artistic volume fields; all-age validation pending'
    for mod,visible in modifier_visibility:mod.show_viewport=visible
    bpy.data.libraries.write(str(output),{col,body.data,*(o.data for o in body.children)},fake_user=True,compress=True)
    output.with_suffix('.json').write_text(json.dumps({'neutral_maximum_error_m':errors,'regions':reports,'retired_adult_contributions':retired,'scope':'Adult regional muscle candidate; other age shapes preserved and not recalibrated'},indent=2),encoding='utf-8')
    print('REGIONAL_MUSCLES18_BUILT',errors,flush=True)

if __name__=='__main__':main()
