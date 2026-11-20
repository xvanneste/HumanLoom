"""Original artistic adipose and face fields; no inferred clinical composition."""
import numpy as np
from muscle_fields import ellipsoid
from body_mass_fields import fields as extended_body_field


def fields(points, height, eye_z):
    x,y,z = points.T
    side = np.sign(x)
    q = np.column_stack((np.abs(x)/height,y/height,z/height))
    result = {}
    def region(name, center, radius, direction, amplitude):
        w = ellipsoid(q,center,radius)
        delta = np.broadcast_to(np.array(direction,dtype=float),points.shape).copy()
        delta[:,0] *= side
        result[name] = delta*(w*amplitude)[:,None]
    region("fat_abdomen",(.025,-.035,.605),(.070,.065,.087),(.35,-1,0),.055)
    region("fat_flanks",(.075,.005,.590),(.042,.075,.075),(1,.15,0),.026)
    region("fat_hips",(.073,.015,.465),(.050,.070,.060),(.65,.7,0),.032)
    region("fat_thighs",(.073,.005,.365),(.045,.060,.085),(.65,.6,0),.022)
    region("fat_arms",(.172,.010,.665),(.038,.045,.070),(.55,.7,0),.018)
    # Cheek and submental volumes, with a compact head mask.
    face = np.exp(-((np.abs(x)-.045)/.032)**2-((z-(eye_z-.045))/.045)**2)
    face *= np.clip((-y-.045)/.04,0,1)
    t=np.clip((z-(eye_z-.028))/.016,0,1)
    face *= 1-t*t*(3-2*t)
    t=np.clip((np.abs(x)-.026)/.016,0,1)
    face *= t*t*(3-2*t)
    result["fat_face"] = np.column_stack((side*.006*face,-.006*face,np.zeros(len(x))))
    result["adiposity"] = sum(result.values())
    result["body_mass"] = extended_body_field(points,height)
    front = np.clip((-y-.06)/.04,0,1)
    def g(cx,cz,rx,rz):
        return np.exp(-((np.abs(x)-cx)/rx)**2-((z-cz)/rz)**2)*front
    ear = np.exp(-((np.abs(x)-.077)/.016)**2-((z-(eye_z-.008))/.048)**2-((y+.015)/.045)**2)
    result["ears_size"] = np.column_stack((side*.005*ear,np.zeros(len(x)),(z-(eye_z-.008))*.12*ear))
    result["ears_angle"] = np.column_stack((side*.003*ear,-.004*ear,np.zeros(len(x))))
    aperture = g(.033,eye_z,.019,.014)
    t=np.clip((-y-.124)/.010,0,1)
    aperture *= t*t*(3-2*t)
    result["eyelid_aperture"] = np.column_stack((np.zeros(len(x)),np.zeros(len(x)),(z-eye_z)*.11*aperture))
    bridge = g(0,eye_z-.010,.015,.031)
    result["nose_bridge"] = np.column_stack((np.zeros(len(x)),-.003*bridge,np.zeros(len(x))))
    lip = g(0,eye_z-.067,.031,.012)
    result["lip_thickness"] = np.column_stack((np.zeros(len(x)),-.0008*lip,(z-(eye_z-.067))*.18*lip))
    corner = g(.025,eye_z-.069,.009,.013)
    result["mouth_corner"] = np.column_stack((np.zeros(len(x)),np.zeros(len(x)),.002*corner))
    angle = g(.047,eye_z-.096,.025,.025)
    result["jaw_angle"] = np.column_stack((side*.003*angle,np.zeros(len(x)),-.0015*angle))
    asym = g(0,eye_z-.040,.075,.065)
    result["facial_asymmetry"] = np.column_stack((.0015*asym,.0006*side*asym,.0007*side*asym))
    # Broad muscle relief. Fat coverage attenuates it in the runtime driver.
    abdominal = ellipsoid(q,(.018,-.043,.650),(.035,.035,.066))
    bands = .5+.5*np.cos((q[:,2]-.65)*height*125)
    result["muscle_definition"] = np.column_stack((np.zeros(len(x)),-.0018*abdominal*bands,np.zeros(len(x))))
    result["skin_relief"] = np.zeros_like(points)
    return result
