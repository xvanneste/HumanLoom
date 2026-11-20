"""Original surface models informed by the regional anatomy in the research note.

Amplitudes are artistic, not a fitted biological dataset. The continuous flow
changes tissue envelopes; bones and muscles have separate surface cues.
"""
import numpy as np


def smooth(t):
    t=np.clip(t,0.,1.)
    return t*t*(3.-2.*t)


def bell(t,center,width):
    return np.exp(-((t-center)/width)**2)


def envelope(points,gain=True):
    height=np.ptp(points[:,2]); floor=points[:,2].min()
    value=points.copy()
    for _ in range(32):
        x,y,z=value.T; ax=np.abs(x); side=np.sign(x); u=(z-floor)/height
        arm=smooth((ax/height-.077)/.052)*smooth((u-.42)/.045)*(1-smooth((u-.83)/.035))
        leg=1-smooth((u-.445)/.065)
        # Smooth blending of axes keeps the shoulder and hip junctions attached.
        arm_axis=(.097+(.81-u)*.38)*height
        leg_axis=(.057+.004*bell(u,.36,.12))*height
        torso_x=x*(.32 if gain else -.115)
        torso_y=(y+.007*height)*(.44 if gain else -.15)
        waist=bell(u,.60,.095)
        torso_y-=height*(.008 if gain else -.003)*waist*smooth((-y/height)/.025)
        limb_gain=(.40 if gain else -.30)*(.40+.60*bell(u,.36,.12))
        local=(ax-leg_axis)*limb_gain
        room=np.maximum(ax,.0001)
        local=np.where(local<0,-.55*room*np.tanh(-local/(.55*room)),local)
        leg_x=side*local
        leg_y=(y-.006*height)*limb_gain
        arm_gain=(.38 if gain else -.32)*(.35+.65*smooth((u-.55)/.16))
        arm_x=side*(ax-arm_axis)*arm_gain
        arm_y=(y+.002*height)*arm_gain
        # The neutral A pose gains modest clearance at the arms; joint lengths
        # are not interpreted as an increase of adipose tissue.
        if gain:arm_x+=side*height*.010*(1-smooth((u-.78)/.06))
        dx=(1-arm)*((1-leg)*torso_x+leg*leg_x)+arm*arm_x
        dy=(1-arm)*((1-leg)*torso_y+leg*leg_y)+arm*arm_y
        body_support=smooth((u-.055)/.045)*(1-smooth((u-.825)/.035))
        # Preserve narrow ankles, wrists and hands while retaining forearm bulk.
        wrist=1-smooth((ax/height-.105)/.035)*(1-smooth((u-.54)/.065))
        dx*=body_support*wrist;dy*=body_support*wrist
        neck=bell(u,.862,.019)*(1-smooth((ax/height-.025)/.025))
        dx+=x*neck*(.16 if gain else -.07)
        dy+=(y+.006*height)*neck*(.16 if gain else -.07)
        # Compact cheek/submental support, below the orbital rim and outside lips.
        face=bell(u,.903,.017)*bell(ax/height,.027,.016)
        face*=smooth((-y/height-.025)/.025)
        dx+=x*face*(.09 if gain else -.045)
        dy-=height*face*(.0024 if gain else -.0018)
        value[:,0]+=dx/32.;value[:,1]+=dy/32.
    return value-points


def surface_cues(points,normals):
    height=np.ptp(points[:,2]); q=points/height
    x,y,z=q.T;ax=np.abs(x)
    front=smooth((-y-.005)/.025);back=smooth((y-.002)/.025)
    central=1-smooth((ax-.085)/.025)
    # Broad ridges and neighboring shallow hollows, not exposed bone meshes.
    clavicle_z=.811-.085*ax+.004*np.sin(ax*45.)
    clavicle=bell(z-clavicle_z,0,.0055)*smooth((ax-.008)/.014)*(1-smooth((ax-.102)/.014))*front
    supraclavicular=bell(z-clavicle_z,.008,.007)*bell(ax,.05,.045)*front
    sternum=bell(ax,0,.008)*bell(z,.753,.040)*front
    rib_region=bell(ax,.061,.027)*front*central
    ribs=np.zeros(len(points))
    for level in (.663,.685,.707):
        arch=level+.17*ax
        ribs+=bell(z-arch,0,.0055)-.65*bell(z-arch,-.010,.006)
    ribs*=rib_region
    iliac_z=.529+.10*(ax-.06)
    iliac=bell(z-iliac_z,0,.0055)*bell(ax,.077,.021)
    iliac*=np.maximum(front,back)*central
    scapula=bell(ax-(.040+.18*(z-.745)),0,.004)*bell(z,.750,.039)*back
    scapula+=.7*bell(z-(.790-.12*ax),0,.004)*bell(ax,.052,.035)*back
    knee=bell(z,.275,.013)*bell(ax,.058,.019)*front
    bone_scalar=(.0050*clavicle-.0040*supraclavicular+.0018*sternum+
                 .0050*ribs+.0037*iliac+.0040*scapula+.0018*knee)
    bone=normals*bone_scalar[:,None]
    # A separate muscular surface layer; the existing keys supply broad volume.
    def g(cx,cy,cz,rx,ry,rz):
        return np.exp(-((ax-cx)/rx)**2-((y-cy)/ry)**2-((z-cz)/rz)**2)
    shoulder=g(.108,0,.805,.027,.05,.033)
    pec=g(.045,-.040,.776,.035,.04,.024)*front
    back_m=g(.066,.033,.733,.045,.04,.060)*back
    arm=g(.151,0,.718,.033,.045,.047)
    thigh=g(.064,-.002,.365,.043,.05,.074)
    calf=g(.057,.015,.175,.030,.045,.044)
    glute=g(.059,.038,.471,.043,.05,.045)*back
    ab=g(.023,-.045,.646,.030,.04,.061)*front
    abdomen_bands=.45+.55*np.maximum(0,np.cos((z-.64)*height*118))
    muscle_scalar=(.0035*shoulder+.003*pec+.003*back_m+.0035*arm+
                   .004*thigh+.003*calf+.0035*glute+.0018*ab*abdomen_bands)
    muscle=normals*muscle_scalar[:,None]
    # Hard compact supports protect eyes, mouth and the original finger details.
    support=smooth((z-.075)/.035)*(1-smooth((z-.835)/.025))
    return bone*support[:,None],muscle*support[:,None]


def soften_fat_surface(rest,changed,edges):
    """Attenuate superficial muscular furrows under an increased tissue layer.

    Symmetric Taubin steps retain broad volume better than repeated shrinking
    Laplacian steps. Keep fingers, feet, face and the narrow wrist untouched.
    """
    height=np.ptp(rest[:,2]);q=rest/height;ax=np.abs(q[:,0]);z=q[:,2]
    mask=smooth((z-.11)/.07)*(1-smooth((z-.82)/.025))
    mask*=1-smooth((ax-.19)/.035)*(1-smooth((z-.59)/.05))
    degree=np.bincount(edges.reshape(-1),minlength=len(rest)).clip(min=1)
    result=changed.copy()
    for _ in range(12):
        for step in (.45,-.47):
            neighbors=np.zeros_like(result)
            np.add.at(neighbors,edges[:,0],result[edges[:,1]])
            np.add.at(neighbors,edges[:,1],result[edges[:,0]])
            result+=(neighbors/degree[:,None]-result)*(mask*step)[:,None]
    return result-rest
