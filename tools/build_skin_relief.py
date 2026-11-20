"""Bake original UV wrinkle fields and add an editable age-driven Displace.

This is geometric surface detail, not a fitted skin-aging model. No external
images or scans are used. The original cage, UVs, and age shapes are preserved.
"""

from pathlib import Path
import sys

import bpy
import numpy as np


def signal(points, eye_z):
    x,y,z=points.T
    value=np.zeros(len(points))
    # Three broad forehead creases with a slight arc and unequal lengths.
    for offset,width,amplitude in ((.025,.050,.32),(.043,.060,.38),(.061,.049,.25)):
        line=eye_z+offset+.003*(x/.06)**2+.0008*np.sin(x*105)
        value-=amplitude*np.exp(-((z-line)/.0018)**2-(x/width)**6)
    # Vertical glabellar folds, away from the eyeballs.
    value-=.22*np.exp(-((np.abs(x)-.007)/.0018)**2-((z-(eye_z+.012))/.016)**4)
    # Lateral eye folds remain outside the ocular clearance zone.
    for slope in (-.35,0.,.35):
        line=eye_z+slope*(np.abs(x)-.057)
        value-=.2*np.exp(-((z-line)/.0016)**2-((np.abs(x)-.062)/.012)**4)
    return np.clip(.5+value,.05,.5)


def main():
    asset,output=[Path(p).resolve() for p in sys.argv[sys.argv.index('--')+1:]]
    with bpy.data.libraries.load(str(asset),link=False) as (_,target):
        target.collections=['Realistic Human Base']
    collection=target.collections[0]
    bpy.context.scene.collection.children.link(collection)
    body=next(o for o in collection.objects if o.get('human_modeling_body'))
    keys=body.data.shape_keys
    base=np.array([v.co[:] for v in keys.key_blocks['Basis'].data])
    eyes=[o for o in body.children if o.type=='MESH']
    eye_z=float(np.concatenate([np.array([v.co[:] for v in o.data.shape_keys.key_blocks['Basis'].data]) for o in eyes])[:,2].mean())
    size=2048
    pixels=np.full((size,size,4),.5,dtype=np.float32)
    pixels[:,:,3]=1.
    mesh=body.data
    mesh.calc_loop_triangles()
    uv=mesh.uv_layers.active
    for tri in mesh.loop_triangles:
        points=base[list(tri.vertices)]
        if points[:,2].max()<eye_z-.04 or points[:,1].min()>-.025:
            continue
        st=np.array([uv.data[i].uv[:] for i in tri.loops])* (size-1)
        lo=np.maximum(np.floor(st.min(axis=0)).astype(int),0)
        hi=np.minimum(np.ceil(st.max(axis=0)).astype(int),size-1)
        if np.any(hi<lo):continue
        matrix=np.column_stack((st[1]-st[0],st[2]-st[0]))
        if abs(np.linalg.det(matrix))<1e-8:continue
        yy,xx=np.mgrid[lo[1]:hi[1]+1,lo[0]:hi[0]+1]
        xy=np.column_stack((xx.ravel(),yy.ravel()))
        bc=(np.linalg.inv(matrix)@(xy-st[0]).T).T
        inside=(bc[:,0]>=0)&(bc[:,1]>=0)&(bc.sum(axis=1)<=1)
        if not inside.any():continue
        values=points[0]+bc[inside,0,None]*(points[1]-points[0])+bc[inside,1,None]*(points[2]-points[0])
        field=signal(values,eye_z)
        loc=xy[inside]
        pixels[loc[:,1],loc[:,0],:3]=field[:,None]
    image=bpy.data.images.new('HM · Relief peau original',width=size,height=size,alpha=True,float_buffer=False)
    image.colorspace_settings.name='Non-Color'
    image.pixels.foreach_set(pixels.reshape(-1));image.update();image.pack()
    texture=bpy.data.textures.new('HM · Relief peau original',type='IMAGE')
    texture.image=image
    group=body.vertex_groups.new(name='HM · Relief visage')
    for i,(x,y,z) in enumerate(base):
        frontal=np.clip((-y-.02)/.035,0,1)
        head=np.clip((z-(eye_z-.012))/.020,0,1)
        # Zero influence on the globe-sized neighborhood and internal eyelids.
        distance=min(np.hypot(x-sign*.033,z-eye_z) for sign in (-1,1))
        clear=np.clip((distance-.022)/.008,0,1)
        weight=float(frontal*head*clear)
        if weight>0:group.add([i],weight,'REPLACE')
    keys['hm_skin_relief']=0.
    keys.id_properties_ui('hm_skin_relief').update(min=-1.,max=1.,default=0.,description='Relief de peau âgée : -1 désactive, 0 référence, +1 accentue')
    placeholder=body.shape_key_add(name='HM · skin_relief')
    placeholder.data.foreach_set('co',base.reshape(-1))
    modifier=body.modifiers.new('Human Modeling · Relief de peau','DISPLACE')
    modifier.texture=texture;modifier.texture_coords='UV';modifier.uv_layer=uv.name
    modifier.vertex_group=group.name;modifier.mid_level=.5
    driver=modifier.driver_add('strength').driver
    driver.type='SCRIPTED'
    for name,path in (('stage','["human_modeling_age"]'),('amount','["hm_skin_relief"]')):
        variable=driver.variables.new();variable.name=name;variable.type='SINGLE_PROP'
        variable.targets[0].id_type='KEY';variable.targets[0].id=keys;variable.targets[0].data_path=path
    driver.expression='max(0,stage-2)*.002*(1+amount)'
    body.data['human_modeling_schema']=6
    bpy.data.libraries.write(str(output),{collection,*(o.data for o in (body,*eyes))},fake_user=True,compress=True)
    print('SKIN_RELIEF_READY',flush=True)


if __name__=='__main__':main()
