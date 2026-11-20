"""Original extended body envelopes, radial around trunk and limb axes.

No weight, BMI or tissue-composition inference is attached to these fields.
"""
import numpy as np


def smooth(x):
    x=np.clip(x,0,1)
    return x*x*(3-2*x)


def fields(points,height=None):
    height=np.ptp(points[:,2]) if height is None else height
    floor=points[:,2].min()
    x,y,z=points.T;side=np.sign(x);u=(z-floor)/height
    delta=np.zeros_like(points)
    central=1-smooth((np.abs(x)/height-.10)/.035)
    support=smooth((u-.43)/.075)*(1-smooth((u-.71)/.09))*central
    abdomen=np.exp(-((u-.595)/.115)**2)*support
    dy=y+.005*height
    radius=np.maximum(np.hypot(x,dy),.025)
    delta[:,0]+=.067*(x/radius)*abdomen
    front=smooth((-y+.005)/.045)
    delta[:,1]+=(.038+.055*front)*(dy/radius)*abdomen
    chest=np.exp(-((u-.745)/.066)**2)*central
    delta[:,0]+=.027*(x/radius)*chest
    delta[:,1]+=.020*(dy/radius)*chest
    # Broader pelvis and posterior seat, without displacing the limb axes.
    pelvis=np.exp(-((u-.47)/.054)**2)*central
    delta[:,0]+=.025*(x/radius)*pelvis
    delta[:,1]+=.033*(dy/radius)*pelvis
    delta[:,2]-=.012*np.exp(-((u-.535)/.055)**2)*front*support
    for name,center_z,width_z,center_x,center_y,width_xy,amount in (
        ('thigh',.345,.105,.061,-.004,.053,.036),
        ('calf',.185,.060,.057,.012,.036,.015),
        ('arm',.705,.060,0.,.003,.032,.018),
        ('forearm',.590,.046,0.,-.010,.024,.009),
    ):
        axis_x=np.full(len(points),center_x*height)
        if name in ('arm','forearm'):
            axis_x=(.097+(.81-u)*.38)*height
        rx=np.abs(x)-axis_x;ry=y-center_y*height
        length=np.maximum(np.hypot(rx,ry),.008)
        weight=np.exp(-(rx/(width_xy*height))**2-(ry/(width_xy*height))**2-((u-center_z)/width_z)**2)
        weight*=smooth((np.abs(x)/height-.012)/.018)
        growth=amount*weight
        dx=rx/length*growth
        if name in ('thigh','calf'):
            # Smooth asymptotic midline clearance avoids clipping inner thighs
            # onto a flat plane or translating the entire limb sideways.
            room=np.maximum(np.abs(x)-.004,.0001)
            dx=np.where(dx<0,-room*(1-np.exp(np.minimum(dx,0)/room)),dx)
        delta[:,0]+=side*dx
        delta[:,1]+=ry/length*growth
    support=smooth((u-.065)/.035)*(1-smooth((u-.83)/.035))
    # The indexed base has tightly folded axillary surfaces. Leave this band
    # to the existing regional controls rather than inflate it radially.
    support*=1-smooth((u-.64)/.035)*(1-smooth((u-.79)/.035))
    return delta*support[:,None]
