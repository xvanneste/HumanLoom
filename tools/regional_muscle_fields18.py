"""Original regional sculpt fields constrained by the native surface atlas.

Visual references guide volume distribution, not vertex correspondence. The
dimensionless amplitudes are artistic settings, not muscle mass measurements.
Neutral shape, pose, fingers, soles and face are not fitted to a supplied mesh.
"""
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree
from surface_frames15 import derive,region_labels
from build_surface_atlas15 import position
from reference_tissue_field14 import coordinates,regularize_ambient

REGIONS=('shoulders','chest','back','arms','abdomen','glutes','thighs','calves')

def smooth(t):
    t=np.clip(t,0,1);return t*t*(3-2*t)

def belly(t,start,peak,end):
    return smooth((t-start)/(peak-start))*(1-smooth((t-peak)/(end-peak)))

def dome(q,center,radius):
    d=np.sum(((q-np.asarray(center))/np.asarray(radius))**2,axis=1)
    return np.maximum(1-d,0)**2

def fields(points,faces,atlas):
    joints,report=derive(points,faces,atlas)
    anchors={k:position(points,v) for k,v in atlas['anchors'].items()}
    labels=region_labels(points,faces,anchors)
    counts=np.zeros((len(points),5))
    for label in range(5):np.add.at(counts[:,label],faces[labels==label].reshape(-1),1)
    counts/=np.maximum(counts.sum(1),1)[:,None]
    arm=counts[:,1]+counts[:,2];leg=counts[:,3]+counts[:,4];trunk=counts[:,0]
    h=np.ptp(points[:,2]);p=points.copy();sign=np.sign(p[:,0]);p[:,0]=abs(p[:,0])
    result={name:np.zeros_like(points) for name in REGIONS}
    for kind,(a,b) in (('upper_arm',(0,1)),('forearm',(1,2)),('thigh',(7,4)),('calf',(4,5))):
        _,radial,radius,_,t=coordinates(p,joints[a],joints[b])
        domain=arm if kind in ('upper_arm','forearm') else leg
        anterior=smooth((-radial[:,1]/radius+.2)/1.1)
        posterior=smooth((radial[:,1]/radius+.2)/1.1)
        lateral=smooth((radial[:,0]/radius+.2)/1.1)
        if kind=='upper_arm':
            shoulder=.75*belly(t,-.16,.11,.44)*(.50+.50*lateral)
            # Distinct anterior biceps and posterior triceps envelopes.
            upper=.52*belly(t,.12,.48,.94)*(.55+.25*anterior+.35*posterior)
            result['shoulders']+=radial*(shoulder*domain)[:,None]
            result['arms']+=radial*(upper*domain)[:,None]
        elif kind=='forearm':
            result['arms']+=radial*(.25*belly(t,.03,.30,.88)*domain)[:,None]
        elif kind=='thigh':
            quad=belly(t,.05,.43,.94)*(.75+.25*anterior+.10*lateral)
            hamstring=.30*belly(t,.12,.43,.86)*posterior
            result['thighs']+=radial*(.27*(quad+hamstring)*domain)[:,None]
        else:
            # Gastrocnemius above the thinner distal/Achilles transition.
            calf=belly(t,.06,.34,.83)*(.55+.65*posterior)
            result['calves']+=radial*(.30*calf*domain)[:,None]
    # Torso placement uses surface-anchor intervals, not universal height bands.
    x,y,z=p.T;front=smooth((-y/h-.002)/.04);back=smooth((y/h+.002)/.04)
    chest_z=(anchors['suprasternale'][2]*.45+anchors['chest_point_l'][2]*.55)
    iliac_z=anchors['iliocristale_l'][2];sternum_z=anchors['suprasternale'][2]
    chest=dome(p,(.050*h,-.055*h,chest_z),(.065*h,.085*h,.075*h))*front*trunk
    # Keep the added pectoral volume above the main breast surface.
    chest*=smooth((z-anchors['chest_point_l'][2])/(.035*h))
    result['chest'][:,1]=-.017*h*chest
    lats=dome(p,(.067*h,.035*h,(sternum_z+iliac_z)/2),(.065*h,.080*h,(sternum_z-iliac_z)*.75))*back*trunk
    traps=dome(p,(.036*h,.035*h,sternum_z-.015*h),(.065*h,.065*h,.080*h))*back*trunk
    result['back'][:,0]=h*(.012*lats+.003*traps)
    result['back'][:,1]=h*(.015*lats+.010*traps)
    abdomen=dome(p,(.022*h,-.05*h,(anchors['omphalion'][2]+chest_z)/2),(.07*h,.10*h,.09*h))*front*trunk
    result['abdomen'][:,1]=-.003*h*abdomen
    glute=dome(p,(anchors['buttock_point_l'][0],anchors['buttock_point_l'][1],anchors['buttock_point_l'][2]),(.065*h,.085*h,.075*h))*back
    # Torso/leg boundary is intentionally blended over the gluteal attachment.
    result['glutes'][:,0]=.003*h*glute
    result['glutes'][:,1]=.014*h*glute
    for delta in result.values():delta[:,0]*=sign
    regularize_ambient(points,result,iterations=4)
    # The arm/trunk seam identifies the folded axillary compartment. Muscle
    # bellies must not inflate the crease itself, especially under high bulk.
    boundary=(arm>0)&(trunk>0)&(points[:,2]<joints[0,2]-.025*h)&(points[:,2]>joints[1,2]+.04*h)
    seed=np.where(boundary)[0]
    if not len(seed):raise ValueError('No axillary seam support for clearance guard')
    tree=KDTree(len(seed))
    for i,index in enumerate(seed):tree.insert(Vector(points[index]),i)
    tree.balance()
    distance=np.array([tree.find(Vector(p))[2] for p in points])
    guard=smooth(distance/(.025*h))
    for name in ('shoulders','arms','chest','back'):result[name]*=guard[:,None]
    # Exact protected domains; no long smoothing tails into face or extremities.
    protect=(points[:,2]>sternum_z+.025*h)|(points[:,2]<points[:,2].min()+.045*h)
    _,_,_,_,wrist_t=coordinates(p,joints[1],joints[2])
    protect|=(arm>.5)&(wrist_t>.98)
    for delta in result.values():delta[protect]=0.
    report['amplitudes_scope']='Artist-authored regional proportions guided by supplied shapes, not biological mass calibration'
    report['axillary_guard']={'seam_vertices':len(seed),'method':'Compact C1 distance taper around the native arm/trunk seam below the shoulder cap'}
    report['regions']={name:{'maximum_displacement_mm':float(np.linalg.norm(delta,axis=1).max()*1000),
                             'affected_vertices':int((np.linalg.norm(delta,axis=1)>1e-5).sum())} for name,delta in result.items()}
    return result,report
