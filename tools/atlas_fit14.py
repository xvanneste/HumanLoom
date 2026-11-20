"""Fit measured adult girth relations while preserving longitudinal coordinates.

ANSUR targets do not make the posed mesh a clinical digital twin. Chest and
buttock levels are identified on the native surface near anatomical reference
heights; waist level remains an explicitly provisional umbilical plane.
"""
import numpy as np
from global_physique_fields import smooth


def hull(points):
    p=sorted(set(map(tuple,points[:,:2])))
    def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    low=[];high=[]
    for v in p:
        while len(low)>1 and cross(low[-2],low[-1],v)<=0:low.pop()
        low.append(v)
    for v in reversed(p):
        while len(high)>1 and cross(high[-2],high[-1],v)<=0:high.pop()
        high.append(v)
    return np.array(low[:-1]+high[:-1])


def perimeter(loop):
    h=hull(loop)
    return float(np.linalg.norm(h-np.roll(h,1,axis=0),axis=1).sum())


def monotone_curve(x,y,query):
    """Shape-preserving cubic Hermite interpolation, without Gaussian bands."""
    spacing=np.diff(x);slope=np.diff(y)/spacing;tangent=np.zeros(len(x))
    for j in range(1,len(x)-1):
        if slope[j-1]*slope[j]>0:
            a=2*spacing[j]+spacing[j-1];b=spacing[j]+2*spacing[j-1]
            tangent[j]=(a+b)/(a/slope[j-1]+b/slope[j])
    index=np.clip(np.searchsorted(x,query)-1,0,len(x)-2)
    length=x[index+1]-x[index];t=np.clip((query-x[index])/length,0,1)
    value=(2*t**3-3*t**2+1)*y[index]+(t**3-2*t**2+t)*length*tangent[index]
    value+=(-2*t**3+3*t**2)*y[index+1]+(t**3-t**2)*length*tangent[index+1]
    return value


def section(points,faces,level,anatomy,part='trunk'):
    loops,_=anatomy.section_loops(points,faces,float(level))
    if part=='trunk':loops=[l for l in loops if anatomy.encloses_axis(l)]
    else:loops=[l for l in loops if l[:,0].mean()>.025]
    if not loops:raise ValueError(('No closed anatomical section',part,level))
    return max(loops,key=lambda l:perimeter(l))


def locate(rest,reference):
    h=np.ptp(rest[:,2]);floor=rest[:,2].min();r=reference['normalized_by_stature']
    ax=np.abs(rest[:,0]);z=(rest[:,2]-floor)/h
    # Surface extrema are searched only near the corresponding anatomical height.
    # These are engineering placements for review, not validated palpated points.
    chest=(ax<h*.10)&(abs(z-r['chestheight'])<.035)
    hip=(ax<h*.13)&(abs(z-r['buttockheight'])<.045)
    ci=np.where(chest)[0][np.argmin(rest[chest,1])]
    hi=np.where(hip)[0][np.argmax(rest[hip,1])]
    return {'chest':float(rest[ci,2]),'waist':float(floor+h*r['waistheightomphalion']),
            'hips':float(rest[hi,2]),'neck':float(floor+h*(r['suprasternaleheight']+.026)),
            'chest_vertex':int(ci),'hips_vertex':int(hi),'height':float(h),'floor':float(floor),
            'status':'Surface extrema near documented adult heights; umbilical and neck planes provisional; A-pose differs from survey pose'}


def arm_mask(rest,sex,joints=None):
    # Locally reviewed native A-pose centers, in metres. This is an engineering
    # skeleton for tissue masks, not a rig or a validated anatomical joint atlas.
    joints=np.array((((.16,0,1.32),(.246,.024,1.05),(.348,-.036,.85)),
                     ((.18,0,1.37),(.287,-.003,1.10),(.373,-.06,.89)))[sex]) if joints is None else joints[:3]
    p=rest.copy();p[:,0]=abs(p[:,0]);dist=[]
    for a,b in zip(joints[:-1],joints[1:]):
        v=b-a;t=np.clip((p-a)@v/(v@v),0,1)
        dist.append(np.linalg.norm(p-(a+t[:,None]*v),axis=1))
    d=np.minimum(*dist)
    gate=smooth((p[:,0]-(joints[0,0]-.055))/.05)
    return (1-smooth((d-.060)/.045))*gate


def fit(rest,initial,faces,record,levels,sex,anatomy,joints=None,measure_surface=None):
    height=levels['height'];floor=levels['floor'];z=rest[:,2];q=(z-floor)/height
    targets={name:record['normalized_by_stature'][column]*height for name,column in
             (('chest','chestcircumference'),('waist','waistcircumference'),('hips','buttockcircumference'))}
    protected=arm_mask(rest,sex,joints)
    torso=(1-protected)*smooth((q-.43)/.06)*(1-smooth((q-.815)/.035))
    # The torso band must not reach hands at the same height as the pelvis.
    torso*=1-smooth((abs(rest[:,0])/height-.12)/.025)
    knots=np.array((floor+.405*height,levels['hips'],levels['waist'],levels['chest'],floor+.845*height))
    assert np.all(np.diff(knots)>0),knots
    center_y=-.005*height
    def apply(coefficients):
        logs=np.array((0.,coefficients[2],coefficients[1],coefficients[0],0.))
        s=np.exp(monotone_curve(knots,logs,z)*torso)
        p=initial.copy();p[:,0]*=s;p[:,1]=center_y+(p[:,1]-center_y)*s
        return p
    def measure(p):return measure_surface(p) if measure_surface else np.array([perimeter(section(p,faces,levels[n],anatomy)) for n in targets])
    target=np.array(list(targets.values()));coeff=np.zeros(len(targets));history=[]
    for _ in range(12):
        current=measure(apply(coeff));err=np.log(target/current)
        history.append(float(abs(err).max()))
        if abs(err).max()<.002:break
        jac=[]
        for j in range(len(targets)):
            trial=coeff.copy();trial[j]+=.004
            jac.append((np.log(measure(apply(trial)))-np.log(current))/.004)
        step=np.linalg.lstsq(np.array(jac).T,err,rcond=None)[0]
        coeff+=np.clip(step,-.10,.10);coeff=np.clip(coeff,-.4,.4)
    final=apply(coeff);measured=measure(final)
    # Longitudinal coordinates, hands and protected arm axes are retained.
    assert np.array_equal(final[:,2],initial[:,2])
    return final,{'targets_m':targets,'actual_m':dict(zip(targets,map(float,measured))),
                  'maximum_relative_residual':float(np.max(abs(measured/target-1))),
                  'iterations':len(history),'log_coefficients':coeff.tolist(),'levels':levels,
                  'fitting_surface':'Evaluated Catmull-Clark level 2 with torso face segmentation' if measure_surface else 'Native cage',
                  'limitations':'Convex mesh sections span hollows. Bra, respiration, soft-tissue compression and exact survey posture are not reproduced. These are provisional modeling fits.'}
