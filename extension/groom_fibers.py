"""Original rest-fiber geometry, in metres; no biological category inference."""
import math
import numpy as np


def fiber(length, nature, phase=0.):
    """Analytic inextensible helix, with its mean axis along +Z.

    Nature is an artistic path through curvature/twist, independent of diameter
    and color. Length is contour length, not the root-to-tip distance.
    """
    k=900.*nature**2
    tau=k*(2.25-2.*nature)
    q=math.hypot(k,tau)
    count=max(12,min(1536,int(math.ceil(q*length/.20))+2))
    s=np.linspace(0.,length,count)
    if q<1e-9:return np.column_stack((s*0,s*0,s))
    axis=np.array([k,0,tau])/q;z=np.array([0.,0.,1.])
    p=s[:,None]*z+(1-np.cos(q*s))[:,None]/q*np.cross(axis,z)+(q*s-np.sin(q*s))[:,None]/q*np.cross(axis,np.cross(axis,z))
    side=np.array([tau,0,-k])/q
    p=np.column_stack((p@side,p[:,1],p@axis))
    c,ss=math.cos(phase),math.sin(phase)
    p[:,:2]=p[:,:2]@np.array([[c,ss],[-ss,c]])
    return p
