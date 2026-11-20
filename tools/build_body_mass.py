"""Append extended body-volume controls without rewriting existing shapes."""
from pathlib import Path
import sys
import bpy
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from body_mass_fields import fields
from experimental_growth_field import endpoint
from experimental_age_transfer import coordinates,write_key
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'extension'))
from proportions import bind_control,CURRENT_SCHEMA


def main():
    asset,output=[Path(p).resolve() for p in sys.argv[sys.argv.index('--')+1:]]
    with bpy.data.libraries.load(str(asset),link=False) as (_,target):target.collections=['Realistic Human Base']
    collection=target.collections[0];body=next(o for o in collection.objects if o.get('human_modeling_body'))
    keys=body.data.shape_keys;basis=coordinates(keys.key_blocks[0])
    keys['hm_body_mass']=0.
    keys.id_properties_ui('hm_body_mass').update(min=-1.,max=1.,default=0.,description='Plage étendue de volumes : minceur vers forte corpulence, sans poids clinique associé')
    endpoints=[endpoint(body,sex) for sex in (0,1)]
    f,m=[fields(points) for points in endpoints]
    for corrective,delta in ((False,f),(True,m-f)):
        key=write_key(body,'HM · body_mass'+(' · correction' if corrective else ''),basis+delta)
        key.slider_min=-1.;bind_control(key,keys,'body_mass',corrective)
    for stage,index in (('Enfant',0),('Adolescent',1),('Senior',3)):
        transported=[]
        for sex,(rest,delta) in enumerate(zip(endpoints,(f,m))):
            change=coordinates(keys.key_blocks[stage])-basis
            if sex:change+=coordinates(keys.key_blocks[stage+' · morphologie'])-basis
            ratio=np.ptp((rest+change)[:,2])/np.ptp(rest[:,2])
            head=smooth_head(rest)
            transverse=ratio**.8*(1-head)+ratio**.28*head
            vertical=ratio*(1-head)+ratio**.28*head
            value=delta*np.column_stack((transverse,transverse,vertical))
            if stage=='Enfant':
                value*=.8
                value[:,2]=0.
            elif stage=='Adolescent':
                value*=.7
            transported.append(value)
        tf,tm=transported
        for corrective,delta in ((False,tf-f),(True,(tm-tf)-(m-f))):
            key=write_key(body,'Age · '+stage+' · HM · body_mass'+(' · correction' if corrective else ''),basis+delta)
            key.slider_min=-1.;bind_control(key,keys,'body_mass',corrective)
            driver=keys.animation_data.drivers.find(key.path_from_id('value')).driver
            age=driver.variables.new();age.name='stage';age.type='SINGLE_PROP'
            age.targets[0].id_type='KEY';age.targets[0].id=keys;age.targets[0].data_path='["human_modeling_age"]'
            driver.expression='('+driver.expression+f')*max(0,1-abs(stage-{index}))'
    body.data['human_modeling_schema']=CURRENT_SCHEMA
    bpy.data.libraries.write(str(output),{collection,body.data,*(o.data for o in body.children)},fake_user=True,compress=True)
    print('EXTENDED_BODY_VOLUMES_READY',flush=True)


def smooth_head(points):
    z=(points[:,2]-points[:,2].min())/np.ptp(points[:,2])
    t=np.clip((z-.83)/.10,0,1)
    return t*t*(3-2*t)


if __name__=='__main__':main()
