"""Append global physique and separate anatomical cues; preserve 0.12 keys."""
import sys
from pathlib import Path
import bpy
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from global_physique_fields import envelope,surface_cues,soften_fat_surface
from experimental_growth_field import endpoint
from experimental_age_transfer import coordinates,write_key
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'extension'))
from proportions import CURRENT_SCHEMA


def bind(key,keys,expression):
    d=key.driver_add('value').driver;d.type='SCRIPTED'
    for v in tuple(d.variables):d.variables.remove(v)
    for name,path in (('amount','["hm_whole_body"]'),('muscle','["hm_muscles"]'),('fat','["hm_adiposity"]'),('stage','["human_modeling_age"]'),('morph','key_blocks["Morphologie"].value')):
        v=d.variables.new();v.name=name;v.type='SINGLE_PROP'
        v.targets[0].id_type='KEY';v.targets[0].id=keys;v.targets[0].data_path=path
    d.expression=expression


def main():
    asset,output=[Path(p).resolve() for p in sys.argv[sys.argv.index('--')+1:]]
    with bpy.data.libraries.load(str(asset),link=False) as (_,t):t.collections=['Realistic Human Base']
    col=t.collections[0];body=next(o for o in col.objects if o.get('human_modeling_body'))
    keys=body.data.shape_keys;basis=coordinates(keys.key_blocks[0])
    keys['hm_whole_body']=0.
    keys.id_properties_ui('hm_whole_body').update(min=-1.,max=1.,default=0.,description='Tissus corporels globaux : minceur et repères osseux vers adiposité répartie')
    endpoints=[endpoint(body,sex) for sex in (0,1)]
    fields=[]
    for rest in endpoints:
        mesh=bpy.data.meshes.new('Anatomical normals')
        mesh.from_pydata(rest.tolist(),[],[tuple(p.vertices) for p in body.data.polygons]);mesh.update()
        normals=np.array([v.normal[:] for v in mesh.vertices]);bpy.data.meshes.remove(mesh)
        bone,muscle=surface_cues(rest,normals)
        edges=np.array([e.vertices[:] for e in body.data.edges])
        gain=soften_fat_surface(rest,rest+envelope(rest,True),edges)
        fields.append({'gain':gain,'perte':envelope(rest,False),'bony_surface':bone,'muscle_surface':muscle})
    for identifier,expr in (('gain','max(amount,0)*(1-.25*abs(fat))'),('perte','max(-amount,0)*(1-.25*abs(fat))*(1-.3*max(-muscle,0))'),('bony_surface','max(-amount,0)*(1-.6*max(muscle,0))*(1-.6*max(fat,0))'),('muscle_surface','max(muscle,0)*(1-.8*max(amount,0))*(1-.5*max(fat,0))')):
        f,m=[p[identifier] for p in fields]
        label='whole_body · '+identifier if identifier in ('gain','perte') else 'anatomical_'+identifier
        for stage,index in (('Adulte',2),('Enfant',0),('Adolescent',1),('Senior',3)):
            transported=[]
            for sex,(rest,delta) in enumerate(zip(endpoints,(f,m))):
                if index==2:value=delta.copy()
                else:
                    change=coordinates(keys.key_blocks[stage])-basis
                    if sex:change+=coordinates(keys.key_blocks[stage+' · morphologie'])-basis
                    ratio=np.ptp((rest+change)[:,2])/np.ptp(rest[:,2])
                    value=delta*ratio**.8
                if index==0:value*=.35 if identifier in ('muscle_surface','bony_surface') else .65
                if index==1:value*=.65 if identifier=='muscle_surface' else .85
                transported.append(value)
            tf,tm=transported
            for corrective,delta in ((False,tf),(True,tm-tf)):
                name=('HM · ' if index==2 else 'Age · '+stage+' · HM · ')+label+(' · correction' if corrective else '')
                key=write_key(body,name,basis+delta)
                expression='('+expr+f')*max(0,1-abs(stage-{index}))'+('*morph' if corrective else '')
                bind(key,keys,expression)
    body.data['human_modeling_schema']=CURRENT_SCHEMA
    keys.key_blocks['Morphologie'].value=1.;keys['human_modeling_age']=2.
    bpy.data.libraries.write(str(output),{col,body.data,*(o.data for o in body.children)},fake_user=True,compress=True)
    print('GLOBAL_PHYSIQUE_READY',flush=True)


if __name__=='__main__':main()
