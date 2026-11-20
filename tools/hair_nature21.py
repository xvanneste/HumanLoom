"""Intrinsic rod geometry for the isolated hair prototype, in SI units.

The continuum and example labels are design controls, not population norms.
Material twist is distinguished from torsion of an arbitrary groomed centerline.
"""
from dataclasses import dataclass
import math
import numpy as np


@dataclass(frozen=True)
class RestFiber:
    curvature_m_inv: float
    material_twist_m_inv: float
    length_m: float
    root_straight_m: float = .003

    def __post_init__(self):
        values = (self.curvature_m_inv, self.material_twist_m_inv, self.length_m, self.root_straight_m)
        if not all(math.isfinite(v) for v in values):
            raise ValueError('Fiber values must be finite.')
        if self.curvature_m_inv < 0 or not 0 <= self.root_straight_m < self.length_m <= 2:
            raise ValueError('Invalid curvature, root segment, or length.')
        if math.hypot(self.curvature_m_inv, self.material_twist_m_inv)*self.length_m > 1500:
            raise ValueError('Requested fiber exceeds the prototype sampling budget.')


def nature(amount, length_m=.06, handedness=1.):
    """Continuous demonstrator from straight to tightly coiled, not a fitted law."""
    if not math.isfinite(amount) or not 0 <= amount <= 1:
        raise ValueError('Nature must lie between 0 and 1.')
    if handedness not in (-1.,1.):
        raise ValueError('Handedness must be -1 or 1.')
    curvature = 900. * amount**2
    # Twist is independently overridable through RestFiber; this is only a preset path.
    twist = handedness * curvature * (2.25 - 2.*amount)
    return RestFiber(curvature,twist,length_m)


def rotation_integral(omega, ds):
    """Exact constant Darboux rotation and integrated tangent over one segment."""
    q = np.linalg.norm(omega)
    if q < 1e-12:
        return np.eye(3), np.eye(3)*ds
    x,y,z = omega
    w = np.array([[0.,-z,y],[z,0.,-x],[-y,x,0.]])
    angle = q*ds
    rotation = np.eye(3) + math.sin(angle)/q*w + (1-math.cos(angle))/q**2*(w@w)
    integral = np.eye(3)*ds + (1-math.cos(angle))/q**2*w + (angle-math.sin(angle))/q**3*(w@w)
    return rotation, integral


def sample_rest(fiber, samples=None):
    """Integrate an inextensible rest rod with curvature/twist in its material frame.

    A short root segment provides clearance. Sampling is by contour length, not
    root-to-tip distance; tightly coiled hair therefore retains the same length.
    """
    q = math.hypot(fiber.curvature_m_inv,fiber.material_twist_m_inv)
    required = max(24,int(math.ceil(q*fiber.length_m/.12))+2)
    count = required if samples is None else int(samples)
    if count < required or count > 13000:
        raise ValueError('Insufficient or excessive sampling for this curvature.')
    samples_s = np.linspace(0,fiber.length_m,count)
    frame = np.eye(3)
    position = np.zeros(3)
    points = [position.copy()]
    for s0,s1 in zip(samples_s[:-1],samples_s[1:]):
        if s0 < fiber.root_straight_m:
            split = min(s1,fiber.root_straight_m)
            position = position + frame[:,2]*(split-s0)
        else:
            split = s0
        if s1 > split:
            rotation, integral = rotation_integral(np.array([fiber.curvature_m_inv,0.,fiber.material_twist_m_inv]),s1-split)
            position = position + frame@integral[:,2]
            frame = frame@rotation
        points.append(position.copy())
    return np.asarray(points)


def section_properties(diameter_m, axis_ratio, young_pa, poisson, density_kg_m3):
    """Homogeneous isotropic elliptical rod approximation, not a keratin fit.

    diameter is the area-equivalent circular diameter; axis_ratio >= 1.
    Values are returned for calibration, never copied into native Bendiness.
    """
    values=(diameter_m,axis_ratio,young_pa,poisson,density_kg_m3)
    if not all(math.isfinite(v) for v in values) or not (diameter_m>0 and axis_ratio>=1 and young_pa>0 and -1<poisson<.5 and density_kg_m3>0):
        raise ValueError('Invalid material or cross-section parameters.')
    a=diameter_m/2*math.sqrt(axis_ratio)
    b=diameter_m/2/math.sqrt(axis_ratio)
    area=math.pi*a*b
    i1=math.pi*a*b**3/4
    i2=math.pi*a**3*b/4
    j=math.pi*a**3*b**3/(a*a+b*b)
    shear=young_pa/(2*(1+poisson))
    return {'area_m2':area,'semi_major_m':a,'semi_minor_m':b,'mass_per_length_kg_m':density_kg_m3*area,'axial_rigidity_n':young_pa*area,'bending_rigidity_1_nm2':young_pa*i1,'bending_rigidity_2_nm2':young_pa*i2,'torsional_rigidity_nm2':shear*j,'approximation':'homogeneous isotropic ellipse; no native solver calibration'}


def apply_to_hair(hair, amount, length_m=.06):
    """Change only a copied prototype groom; roots/UVs and surface stay intact."""
    from mathutils import Vector
    if hair.type!='CURVES' or not hair.get('hm_hair_prototype'):
        raise ValueError('Expected an isolated prototype groom.')
    # Validate and compute before resizing any datablock.
    fiber=nature(amount,length_m)
    local=sample_rest(fiber)
    data=hair.data
    roots=np.array([data.points[c.first_point_index].position[:] for c in data.curves])
    source=np.array([data.points[c.first_point_index+1].position[:] for c in data.curves])
    directions=source-roots
    directions/=np.maximum(np.linalg.norm(directions,axis=1)[:,None],1e-12)
    positions=[]
    for root,tangent in zip(roots,directions):
        t=Vector(tangent)
        reference=Vector((0,1,0))
        d1=reference-t*reference.dot(t)
        if d1.length<1e-6:d1=Vector((1,0,0))-t*t.x
        d1.normalize()
        q=math.hypot(fiber.curvature_m_inv,fiber.material_twist_m_inv)
        if q>1e-9:
            # Place the mean helix axis outwards. Aligning only the initial
            # tangent to the normal would aim tight coils into the scalp.
            sine=fiber.curvature_m_inv/q
            cosine=abs(fiber.material_twist_m_inv)/q
            sign=1. if fiber.material_twist_m_inv>=0 else -1.
            axis=t.copy();side=d1.copy()
            t=cosine*axis+sine*side
            d1=sign*(sine*axis-cosine*side)
        d2=t.cross(d1)
        frame=np.column_stack((d1[:],d2[:],t[:]))
        positions.append(root+local@frame.T)
    data.resize_curves([len(local)]*len(roots))
    data.attributes['position'].data.foreach_set('vector',np.asarray(positions,dtype=np.float32).ravel())
    data.attributes['radius'].data.foreach_set('value',np.tile(np.linspace(.000075,.000012,len(local)),len(roots)))
    for name,value in [('hm_rest_curvature_m_inv',fiber.curvature_m_inv),('hm_rest_material_twist_m_inv',fiber.material_twist_m_inv),('hm_rest_length_m',fiber.length_m)]:
        attr=data.attributes.get(name) or data.attributes.new(name,'FLOAT','CURVE')
        attr.data.foreach_set('value',np.full(len(roots),value))
    hair['hm_hair_nature']=amount
    hair['hm_hair_nature_schema']=1
    hair['hm_hair_nature_calibration']='Illustrative continuous preset; not fitted biological classes'
    data.update_tag()
    hair.update_tag()
    return fiber
