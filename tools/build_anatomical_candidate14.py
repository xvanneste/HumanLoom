"""Adult-only research candidate: real girth targets and corrected landmarks.

This does not claim pediatric/senior anthropometric validation and is not an
automatic replacement for the installed extension. Retain 0.13 unchanged.
"""
from pathlib import Path
import sys,json
import bpy,numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from experimental_growth_field import endpoint
from experimental_age_transfer import coordinates,write_key
from atlas_fit14 import fit,locate
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'extension'))
import anatomy
from build_global_physique import bind
from reference_tissue_field14 import transfer,regularize_ambient


def main():
    args=sys.argv[sys.argv.index('--')+1:]
    asset,output=[Path(p).resolve() for p in args[:2]]
    atlas=json.loads(Path(args[args.index('--surface-atlas')+1]).read_text(encoding='utf-8')) if '--surface-atlas' in args else None
    source=json.loads((output.parent/'anthropometric-profiles.json').read_text(encoding='utf-8'))
    with bpy.data.libraries.load(str(asset),link=False) as (_,t):t.collections=['Realistic Human Base']
    col=t.collections[0];body=next(o for o in col.objects if o.get('human_modeling_body'))
    keys=body.data.shape_keys;basis=coordinates(keys.key_blocks[0]);body.data.calc_loop_triangles()
    faces=np.array([t.vertices[:] for t in body.data.loop_triangles]);reports=[];targets=[]
    cache=np.load(output.parent/'source/reference-physiques.npz')
    for sex in (0,1):
        rest=endpoint(body,sex);profiles=source['sexes'][str(sex)]['profiles']
        levels=locate(rest,profiles['reference'])
        values={}
        joints=None
        if atlas:
            from surface_frames15 import derive
            joints,frame_report=derive(rest,faces,atlas)
            reports.append({'sex':sex,'surface_frames':frame_report})
        working=rest.copy()
        if '--reference-envelope' in args:
            envelope={'neutral':transfer(rest,sex,cache,'reference',joints,reference_envelope=True)}
            regularize_ambient(rest,envelope,iterations=6)
            working+=envelope['neutral']
            if atlas:joints,_=derive(working,faces,atlas)
        learned={name:transfer(working,sex,cache,name,joints) for name in ('thin','fat','muscle','muscle_low','fat_muscle','thin_low')}
        regularize_ambient(working,learned,iterations=6 if atlas else 4)
        meter=None
        if '--evaluated-fit' in args:
            from evaluated_fit15 import SurfaceMeter
            meter=SurfaceMeter(body,rest,levels,anatomy)
        for name in ('reference','thin','fat'):
            initial=working if name=='reference' else working+learned[name]
            result,report=fit(rest,initial,faces,profiles[name],levels,sex,anatomy,joints,meter)
            values[name]=result-rest
            report.update(sex=sex,profile=name,source_subject_id=profiles[name]['subject_id'])
            reports.append(report)
            print('ATLAS_FIT',sex,name,report['maximum_relative_residual'],flush=True)
        if meter:meter.close()
        original_muscle=coordinates(keys.key_blocks['HM · muscles'])-basis
        if sex:original_muscle+=coordinates(keys.key_blocks['HM · muscles · correction'])-basis
        values['muscle_cancel']=-original_muscle
        values['muscle_gain']=learned['muscle']
        values['muscle_perte']=learned['muscle_low']
        values['fat_muscle']=learned['fat_muscle']-learned['fat']-learned['muscle']
        values['thin_low']=learned['thin_low']-learned['thin']-learned['muscle_low']
        targets.append(values)
    # Preserve the old arrays for diagnosis, but disable their adult influence in
    # this candidate. Age variants remain available and are explicitly unvalidated.
    retired=[]
    for curve in keys.animation_data.drivers:
        if curve.data_path.startswith('key_blocks["HM · ') and any(s in curve.data_path for s in ('whole_body ·','anatomical_bony_surface','anatomical_muscle_surface')):
            curve.driver.expression='0';retired.append(curve.data_path)
    expressions=(('reference','1'),('gain','max(amount,0)'),('perte','max(-amount,0)'),
                 ('muscle_cancel','muscle'),('muscle_gain','max(muscle,0)'),('muscle_perte','max(-muscle,0)'),
                 ('fat_muscle','max(amount,0)*max(muscle,0)'),('thin_low','max(-amount,0)*max(-muscle,0)'))
    for label,expr in expressions:
        displacements=[]
        for values in targets:
            d=values['fat' if label=='gain' else 'thin']-values['reference'] if label in ('gain','perte') else values[label]
            displacements.append(d)
        f,m=displacements
        for correction,delta in ((False,f),(True,m-f)):
            key=write_key(body,'HM · Atlas14 · '+label+(' · correction' if correction else ''),basis+delta)
            bind(key,keys,'('+expr+')*max(0,1-abs(stage-2))'+('*morph' if correction else ''))
    keys['hm_whole_body']=0.;keys['human_modeling_age']=2.;keys.key_blocks['Morphologie'].value=1.
    body['hm_anatomy_candidate']='Adult reference research candidate 14; not clinical validation; source proportions review required'
    if atlas:body['hm_surface_frames']='Surface atlas 15: geodesic limb partition and section centroids; modeling axes, not skeletal joints'
    bpy.data.libraries.write(str(output),{col,body.data,*(o.data for o in body.children)},fake_user=True,compress=True)
    output.with_suffix('.fit.json').write_text(json.dumps({'fits':reports,'retired_adult_fields':retired,'scope':'Adult candidate only; recorded source rows are modeling references, not clinical twins'},indent=2),encoding='utf-8')


if __name__=='__main__':main()
