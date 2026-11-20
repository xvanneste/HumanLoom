"""Transfer regional tissue-radius changes in local anatomical frames.

Artist-authored CC0 reference geometry supplies shape changes. It supplies no
clinical body-fat or muscle-mass calibration. Target limb frames remain fixed;
source and target poses can differ. No reference program code is copied.
"""
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree


def native_joints(rest,sex):
    h=np.ptp(rest[:,2]);floor=rest[:,2].min()
    arms=np.array((((.16,0,1.32),(.246,.024,1.05),(.348,-.036,.85)),
                   ((.18,0,1.37),(.287,-.003,1.10),(.373,-.06,.89)))[sex])
    # Native A-pose engineering centers. These must be reviewed independently
    # of surface girths; they are not inferred clinical joint centers.
    hip=np.array((.055*h,0,floor+.515*h));knee=np.array((.057*h,-.015*h,floor+.280*h));ankle=np.array((.058*h,0,floor+.055*h))
    neck=np.array((0,0,floor+.845*h));jaw=np.array((0,-.025*h,floor+.9*h))
    pelvis=np.array((0,0,floor+.515*h))
    return np.array((*arms,pelvis,knee,ankle,neck,hip,jaw))


PAIRS=((3,6),(0,1),(1,2),(7,4),(4,5),(6,8))
RADII=(.105,.033,.025,.047,.031,.027)


def regularize_ambient(rest,fields,iterations=4):
    """Regularize transport across nearby folded surfaces, not only mesh edges.

    Axillary surfaces can be close in space and distant in topology. Giving
    them a common smooth ambient deformation avoids opposing tissue fields.
    This is a geometric transport constraint, not a biological coefficient.
    """
    tree=KDTree(len(rest))
    for i,p in enumerate(rest):tree.insert(Vector(p),i)
    tree.balance();indices=[];weights=[]
    for p in rest:
        neighbors=tree.find_n(Vector(p),64)
        indices.append([v[1] for v in neighbors])
        d=np.array([v[2] for v in neighbors]);w=np.exp(-.5*(d/.025)**2);weights.append(w/w.sum())
    indices=np.array(indices);weights=np.array(weights)
    support=np.max(np.array([np.linalg.norm(v,axis=1) for v in fields.values()]),axis=0)>1e-7
    for delta in fields.values():
        for _ in range(iterations):
            averaged=np.sum(delta[indices]*weights[:,:,None],axis=1)
            delta[:]=.5*delta+.5*averaged;delta[~support]=0.


def coordinates(points,a,b):
    direction=b-a;length=np.linalg.norm(direction);axis=direction/length
    e1=np.array((0.,1.,0.));e1-=axis*np.dot(axis,e1);e1/=np.linalg.norm(e1)
    e2=np.cross(axis,e1)
    offset=points-a;t=offset@axis/length
    radial=offset-(offset@axis)[:,None]*axis
    radius=np.maximum(np.linalg.norm(radial,axis=1),.001)
    c=radial@e1/radius;s=radial@e2/radius
    feature=np.column_stack((t*2,c*.5,s*.5))
    closest=a+np.clip(t,0,1)[:,None]*direction
    distance=np.linalg.norm(points-closest,axis=1)
    return feature,radial,radius,distance,t


def transfer(rest,sex,cache,profile,joints=None,reference_envelope=False):
    source=cache[f'points_{sex}_reference'].copy();changed=cache[f'points_{sex}_{profile}'].copy()
    source[:,0]=abs(source[:,0]);changed[:,0]=abs(changed[:,0])
    sj=cache[f'joints_{sex}_reference'];cj=cache[f'joints_{sex}_{profile}'];nj=native_joints(rest,sex) if joints is None else joints
    target=rest.copy();sign=np.sign(target[:,0]);target[:,0]=abs(target[:,0])
    sh=np.ptp(source[:,2]);th=np.ptp(rest[:,2]);sdata=[];tdata=[];sw=[];tw=[];tapers=[]
    for index,((a,b),radius) in enumerate(zip(PAIRS,RADII)):
        sd=coordinates(source,sj[a],sj[b]);td=coordinates(target,nj[a],nj[b])
        sdata.append(sd);tdata.append(td)
        sw.append(np.exp(-2*np.minimum(sd[3]/(sh*radius),8)**4))
        weight=np.exp(-2*np.minimum(td[3]/(th*radius),8)**4)
        # Preserve fingers and soles rather than stretching them with tissue.
        taper=np.clip((td[4]+.08)/.16,0,1)*np.clip((1.08-td[4])/.16,0,1)
        if index in (2,4):taper*=np.clip((1-td[4])/.18,0,1)
        if index==5:taper*=np.clip((1-td[4])/.22,0,1)
        tapers.append(taper)
        tw.append(weight)
    groups=np.argmax(np.array(sw),axis=0);weights=np.array(tw).T
    total=weights.sum(axis=1);weights/=np.maximum(total,1e-12)[:,None]
    result=np.zeros_like(rest)
    for index,(a,b) in enumerate(PAIRS):
        if reference_envelope and index!=0:continue
        selected=np.where((groups==index)&(sdata[index][4]>-.05)&(sdata[index][4]<1.05))[0]
        if len(selected)<20:continue
        original_radius=sdata[index][2]
        changed_radius=coordinates(changed,cj[a],cj[b])[2]
        ratio=np.clip(changed_radius/original_radius,.55,1.65)
        tree=KDTree(len(selected))
        for i,vertex in enumerate(selected):tree.insert(Vector(sdata[index][0][vertex]),i)
        tree.balance()
        for vertex in np.where((weights[:,index]>.002)&(total>1e-5))[0]:
            nearest=tree.find_n(Vector(tdata[index][0][vertex]),24)
            ids=np.array([selected[v[1]] for v in nearest]);d=np.array([v[2] for v in nearest])
            influence=1/np.maximum(d,.018)**2;influence/=influence.sum()
            if reference_envelope:
                # Match the artist-authored neutral torso envelope in local
                # coordinates. This is a shape reference, not observed anatomy.
                desired=float(np.sum(original_radius[ids]*influence))*th/sh
                factor=float(np.clip(desired/tdata[index][2][vertex],.55,1.65))-1
            else:factor=float(np.sum(ratio[ids]*influence))-1
            result[vertex]+=tdata[index][1][vertex]*factor*weights[vertex,index]*tapers[index][vertex]
    result[:,0]*=sign
    # Maintain a smooth positive medial clearance in the native closer-leg pose.
    medial=(rest[:,2]<nj[7,2])&(abs(rest[:,0])<.1*th)
    inward=sign*result[:,0];room=np.maximum(abs(rest[:,0])-.003,.0001)
    inward=np.where(medial&(inward<0),-room*(1-np.exp(np.minimum(inward,0)/room)),inward)
    result[:,0]=sign*inward
    result[total<1e-5]=0.
    return result
