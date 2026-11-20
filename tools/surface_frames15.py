"""Geometry-derived modeling axes, not skeletal joint localization.

Surface anchor addresses select stations. Closed section area centroids select
the transverse centers, avoiding a vertex-density dependent average. Nothing
here infers hidden bone, biological age, or a population norm.
"""
import heapq
import numpy as np
from build_surface_atlas15 import position
from experimental_growth_field import anatomy
from semantic_torso14 import plane_points
from atlas_fit14 import hull


def region_labels(points,faces,p):
    """Partition by surface distance from separated arm/leg contour seeds."""
    centers=points[faces].mean(axis=1);adj=[set() for _ in faces];edges={}
    for i,tri in enumerate(faces):
        for a,b in ((tri[0],tri[1]),(tri[1],tri[2]),(tri[2],tri[0])):
            edge=tuple(sorted((int(a),int(b))))
            if edge in edges:
                j=edges[edge];adj[i].add(j);adj[j].add(i)
            else:edges[edge]=i
    seeds={}
    for part,level in (('arm',p['acromion_l'][2]*.3+p['radiale_l'][2]*.7),
                       ('leg',(p['trochanterion_l'][2]+p['midpatella_l'][2])/2)):
        loops,_=anatomy.section_loops(points,faces,level)
        classified=[]
        for loop in loops:
            label=0 if anatomy.encloses_axis(loop) else (1 if loop[:,0].mean()>0 else 2)+(2 if part=='leg' else 0)
            classified.append((loop,label))
        expected={0,1,2} if part=='arm' else {3,4}
        if not expected.issubset({label for _,label in classified}):raise ValueError(('Cannot seed separated regions',part))
        heights=points[faces,2]
        for i in np.where((heights.min(1)<level)&(heights.max(1)>level))[0]:
            hit=plane_points(points,faces[i:i+1],level)[0]
            seeds[i]=min(classified,key=lambda item:np.linalg.norm(item[0]-hit,axis=1).min())[1]
    distance=np.full(len(faces),np.inf);labels=np.full(len(faces),-1,dtype=int);queue=[]
    for i,label in seeds.items():distance[i]=0;labels[i]=label;heapq.heappush(queue,(0.,i))
    while queue:
        d,i=heapq.heappop(queue)
        if d!=distance[i]:continue
        for j in adj[i]:
            trial=d+np.linalg.norm(centers[i]-centers[j])
            if trial<distance[j]:distance[j]=trial;labels[j]=labels[i];heapq.heappush(queue,(trial,j))
    assert np.all(labels>=0)
    return labels


def polygon_centroid(loop):
    xy=loop[:,:2];nxt=np.roll(xy,-1,axis=0)
    cross=xy[:,0]*nxt[:,1]-nxt[:,0]*xy[:,1]
    area2=cross.sum()
    if abs(area2)<1e-10:raise ValueError('Degenerate section area')
    return np.r_[((xy+nxt)*cross[:,None]).sum(axis=0)/(3*area2),loop[:,2].mean()]


def station_center(points,faces,origin,direction):
    axis=direction/np.linalg.norm(direction)
    u=np.array((0.,1.,0.));u-=axis*np.dot(axis,u);u/=np.linalg.norm(u)
    frame=np.column_stack((u,np.cross(axis,u),axis))
    hits=plane_points((points-origin)@frame,faces,0.)
    if len(hits)<6:raise ValueError('Insufficient station contour support')
    polygon=hull(hits);center=polygon_centroid(np.column_stack((polygon,np.zeros(len(polygon)))))
    return origin+center@frame.T


def segment_axis(points,faces,a,b,semantic=False):
    axis=b-a;length=np.linalg.norm(axis);axis/=length
    u=np.array((0.,1.,0.));u-=axis*np.dot(axis,u);u/=np.linalg.norm(u)
    v=np.cross(axis,u);frame=np.column_stack((u,v,axis))
    local=(points-a)@frame;centers=[];sections=[]
    # Stay in the free middle shaft. Near shoulder/hip, the closed contour
    # joins the trunk and no longer describes an isolated limb section.
    for t in (.35,.5,.65):
        if semantic:
            hits=plane_points(local,faces,t*length)
            if len(hits)<6:raise ValueError('Insufficient regional section support')
            polygon=hull(hits);loops=[np.column_stack((polygon,np.full(len(polygon),t*length)))];level=t*length
        else:loops,level=anatomy.section_loops(local,faces,t*length)
        candidates=[(np.linalg.norm(polygon_centroid(loop)[:2]),loop) for loop in loops]
        distance,loop=min(candidates,key=lambda pair:pair[0])
        # Reject an unrelated limb or torso component rather than guessing.
        if distance>length*.45:raise ValueError(('Section too far from anchor segment',distance,length))
        center=polygon_centroid(loop);centers.append(center)
        sections.append({'station':t,'centroid_m':(a+center@frame.T).tolist(),
                         'perimeter_m':float(np.linalg.norm(loop-np.roll(loop,1,axis=0),axis=1).sum())})
    centers=np.array(centers)
    fit=np.linalg.lstsq(np.column_stack((centers[:,2],np.ones(3))),centers[:,:2],rcond=None)[0]
    ends=np.array([np.r_[np.array((z,1.))@fit,z] for z in (0.,length)])
    return a+ends@frame.T,sections


def derive(points,faces,atlas):
    p={k:position(points,a) for k,a in atlas['anchors'].items()}
    wrist=(p['stylion_l']+p['ulnar_wrist_l'])/2
    neck_seed=(p['suprasternale']+p['cervicale'])/2
    # The chin is an anterior surface point, not the upper neck center.
    # Use only its height for the upper station; horizontal sections find XY.
    upper_neck=neck_seed.copy();upper_neck[2]=p['menton'][2]
    labels=region_labels(points,faces,p)
    pairs=(('upper_arm',p['acromion_l'],p['radiale_l']),
           ('forearm',p['radiale_l'],wrist),
           ('thigh',p['trochanterion_l'],p['midpatella_l']),
           ('calf',p['midpatella_l'],p['lateral_malleolus_l']),
           ('neck',neck_seed,upper_neck))
    fitted={};report={}
    for name,a,b in pairs:
        region=1 if name in ('upper_arm','forearm') else 3 if name in ('thigh','calf') else None
        fitted[name],sections=segment_axis(points,faces if region is None else faces[labels==region],a,b,region is not None)
        report[name]={'axis_endpoints_m':fitted[name].tolist(),'sections':sections,
                      'method':'Least-squares line through three area centroids; geodesic region partition and convex section envelope for limbs'}
    shoulder,elbow_upper=fitted['upper_arm'];elbow_lower,hand=fitted['forearm']
    hip,knee_upper=fitted['thigh'];knee_lower,ankle=fitted['calf']
    # Muscle bellies need not extrapolate to a common center (the calf line
    # can miss the knee by centimetres). Use the local surface section at the
    # joint station rather than averaging those extrapolated muscle axes.
    arm_direction=(elbow_upper-shoulder)+(hand-elbow_lower)
    leg_direction=(knee_upper-hip)+(ankle-knee_lower)
    elbow=station_center(points,faces[labels==1],p['radiale_l'],arm_direction)
    knee=station_center(points,faces[labels==3],p['midpatella_l'],leg_direction)
    neck,jaw=fitted['neck'];neck[0]=jaw[0]=0
    pelvis=np.array((0.,hip[1],hip[2]))
    joints=np.array((shoulder,elbow,hand,pelvis,knee,ankle,neck,hip,jaw))
    if not np.isfinite(joints).all():raise ValueError('Nonfinite frame')
    report['scope']='Modeling axes from native surface; not anatomical joints or a rig'
    report['joints_m']=joints.tolist()
    report['junction_mismatch_m']={'elbow':float(np.linalg.norm(elbow_upper-elbow_lower)),
                                  'knee':float(np.linalg.norm(knee_upper-knee_lower))}
    report['junction_method']='Area centroid of the local section at the surface-anchor station; not the average of extrapolated muscle-belly axes, and not a skeletal joint'
    return joints,report
