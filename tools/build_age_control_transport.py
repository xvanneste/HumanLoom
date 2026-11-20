"""Transport controls by smooth positive regional scales, not clinical growth.

Shape topology and UV loops are unchanged. All original keys remain.
"""
import json
from pathlib import Path
import sys
import bpy
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from experimental_growth_field import endpoint
from experimental_age_transfer import coordinates, write_key


def main():
    asset,output=[Path(p).resolve() for p in sys.argv[sys.argv.index('--')+1:]]
    with bpy.data.libraries.load(str(asset),link=False) as (_,t): t.collections=['Realistic Human Base']
    col=t.collections[0]
    bpy.context.scene.collection.children.link(col)
    body=next(o for o in col.objects if o.get('human_modeling_body'))
    owner=body.data.shape_keys
    owner['human_modeling_age']=2.
    owner.id_properties_ui('human_modeling_age').update(min=0.,max=3.,default=2.,description='Interpolation entre références 5, 15, 30 et 75 ans')
    count=0
    for obj in (body,*body.children):
        keys=obj.data.shape_keys
        basis=coordinates(keys.key_blocks['Basis'])
        original=[k for k in keys.key_blocks if k.name.startswith('HM · ') and ' · correction' not in k.name]
        for stage,index in (('Enfant',0),('Adolescent',1),('Senior',3)):
            matrices=[]
            for sex in (0,1):
                rest=endpoint(obj,sex)
                change=coordinates(keys.key_blocks[stage])-basis
                if sex: change+=coordinates(keys.key_blocks[stage+' · morphologie'])-basis
                target=rest+change
                if obj is body:
                    height=np.ptp(rest[:,2]); ratio=np.ptp(target[:,2])/height
                    relative=(rest[:,2]-rest[:,2].min())/height
                    t=np.clip((relative-.83)/.10,0,1); head=t*t*(3-2*t)
                    transverse=ratio**.8*(1-head)+ratio**.28*head
                    vertical=ratio*(1-head)+ratio**.28*head
                    matrix=np.zeros((len(rest),3,3))
                    matrix[:,0,0]=matrix[:,1,1]=transverse;matrix[:,2,2]=vertical
                    matrices.append(matrix)
                else:
                    # Preserve a rigid eye displacement under each transported control.
                    original_body=endpoint(body,sex)
                    change_body=coordinates(owner.key_blocks[stage])-coordinates(owner.key_blocks['Basis'])
                    if sex:change_body+=coordinates(owner.key_blocks[stage+' · morphologie'])-coordinates(owner.key_blocks['Basis'])
                    factor=(np.ptp((original_body+change_body)[:,2])/np.ptp(original_body[:,2]))**.28
                    matrices.append(np.broadcast_to(np.eye(3)*factor,(len(rest),3,3)).copy())
            for original_key in original:
                correction=keys.key_blocks.get(original_key.name.replace('HM · '+original_key.name.split(' · ')[1], 'HM · '+original_key.name.split(' · ')[1]+' · correction',1))
                f=coordinates(original_key)-basis
                m=f+(coordinates(correction)-basis if correction else 0)
                tf=np.einsum('ni,nij->nj',f,matrices[0])
                tm=np.einsum('ni,nij->nj',m,matrices[1])
                if stage=='Enfant' and ('muscles' in original_key.name or 'muscle_definition' in original_key.name):
                    tf*=.4; tm*=.4
                for source,delta in ((original_key,tf-f),(correction,(tm-tf)-(m-f))):
                    if source is None: continue
                    key=write_key(obj,'Age · '+stage+' · '+source.name,basis+delta)
                    key.slider_min=-1
                    driver=key.driver_add('value').driver
                    driver.type='SCRIPTED'
                    source_driver=next(c.driver for c in keys.animation_data.drivers if c.data_path==source.path_from_id('value'))
                    for var in source_driver.variables:
                        new=driver.variables.new();new.name=var.name;new.type='SINGLE_PROP'
                        new.targets[0].id_type='KEY';new.targets[0].id=owner;new.targets[0].data_path=var.targets[0].data_path
                    age=driver.variables.new();age.name='stage';age.type='SINGLE_PROP'
                    age.targets[0].id_type='KEY';age.targets[0].id=owner;age.targets[0].data_path='["human_modeling_age"]'
                    driver.expression='('+source_driver.expression+f')*max(0,1-abs(stage-{index}))'
                    count+=1
        if obj is not body:
            center=(basis.max(axis=0)+basis.min(axis=0))/2
            key=write_key(obj,'Surface · Ajustement orbital',basis-.08*(basis-center)+np.array((0,.002,0)))
            key.value=1.
    body.data['human_modeling_schema']=5
    bpy.context.view_layer.update()
    assert all(c.is_valid for o in (body,*body.children) for c in o.data.shape_keys.animation_data.drivers)
    bpy.data.libraries.write(str(output),{col,*(o.data for o in (body,*body.children))},fake_user=True,compress=True)
    output.with_suffix('.transport.json').write_text(json.dumps({'transport_keys':count,'eye_retraction_m':.002,'eye_radius_scale':.92,'method':'Smooth positive regional scale transport; child muscle amplitude factor .4 is artistic'},indent=2),encoding='utf-8')
    print('AGE_CONTROLS_READY',count,flush=True)


if __name__=='__main__': main()
