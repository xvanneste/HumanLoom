"""Bounded native-physics benchmark profiles, not a general material calibration."""
import math
import bpy
import numpy as np
import hair_prototype20 as h20


def configure_benchmark(hair):
    """Prepare native Physics only inside the tested geometric domain.

    Reject unsupported high-resolution/curl shapes before changing any setting.
    No positions or lengths are corrected after the solver.
    """
    if bpy.app.version[:2]!=(5,2) or hair.type!='CURVES' or not hair.data.surface:
        raise ValueError('Expected attached Hair Curves in Blender 5.2.')
    counts=[len(curve.points) for curve in hair.data.curves]
    if not counts or len(set(counts))!=1 or counts[0] not in (8,24):
        raise ValueError('Benchmark validated only for 8 or 24 points per guide; dense coils require separate convergence tests.')
    n=counts[0]
    positions=np.array([p.position[:] for p in hair.data.points]).reshape((-1,n,3))
    edges=np.diff(positions,axis=1)
    lengths=np.linalg.norm(edges,axis=2)
    if not np.isfinite(positions).all() or lengths.min()<1e-7:
        raise ValueError('Invalid or degenerate guide geometry.')
    if np.max(abs(lengths.sum(axis=1)/.06-1))>.001:
        raise ValueError('This benchmark profile is verified for 6 cm fibers only.')
    directions=edges/lengths[:,:,None]
    angle=np.arccos(np.clip(np.sum(directions[:,1:]*directions[:,:-1],axis=2),-1,1))
    if angle.max()>.15:
        raise ValueError('Guide turns exceed this benchmark domain; do not erase curl detail to bypass the check.')
    mods=[m for m in hair.modifiers if m.type=='NODES' and m.node_group and m.node_group.name.split('.')[0]=='Hair Dynamics']
    if len(mods)!=1:
        raise ValueError('Expected exactly one native Hair Dynamics modifier.')
    modifier=mods[0]
    values={('Mode','NodeSocketMenu'):'Physics (Experimental)',('Substeps','NodeSocketInt'):4,('Constraint Steps','NodeSocketInt'):1024 if n==8 else 16384,('Stretchiness','NodeSocketFloat'):0.,('Bendiness','NodeSocketFloat'):.2,('Root Bendiness','NodeSocketFloat'):.1,('Randomness','NodeSocketBool'):False,('Gravity','NodeSocketBool'):True,('Surface Collision','NodeSocketBool'):False}
    plan=[]
    for (name,kind),value in values.items():
        items=[item for item in modifier.node_group.interface.items_tree if item.item_type=='SOCKET' and item.in_out=='INPUT' and item.name==name and item.socket_type==kind]
        if len(items)!=1:raise ValueError('Missing or ambiguous native input: '+name)
        socket=getattr(modifier.properties.inputs,items[0].identifier)
        plan.append((socket,socket.value,value))
    try:
        for socket,old,value in plan:socket.value=value
        hair.update_tag()
    except Exception:
        for socket,old,value in plan:socket.value=old
        hair.update_tag()
        raise
    hair['hm_physics_benchmark_schema']=1
    hair['hm_physics_benchmark_domain']='6cm, 8/24 points, segment turn <=0.15 rad, no collisions; native controls not biological constants'
    return {'points_per_guide':n,'substeps':4,'iterations':1024 if n==8 else 16384,'material_calibrated':False}


def build_guides(body, points=8, count=12, curvature=0., twist=0.):
    hair=h20.create_hair(body,count=count)
    roots=np.array([hair.data.points[c.first_point_index].position[:] for c in hair.data.curves])
    tangents=np.array([hair.data.points[c.first_point_index+1].position[:] for c in hair.data.curves])-roots
    tangents/=np.linalg.norm(tangents,axis=1)[:,None]
    local=np.column_stack((np.zeros(points),np.zeros(points),np.linspace(0,.06,points)))
    if curvature or twist:
        from hair_nature21 import RestFiber,sample_rest
        local=sample_rest(RestFiber(curvature,twist,.06),samples=points)
    positions=[]
    for root,tangent in zip(roots,tangents):
        side=np.array([0.,1.,0.]);side-=tangent*np.dot(side,tangent);side/=np.linalg.norm(side)
        frame=np.column_stack((side,np.cross(tangent,side),tangent))
        positions.append(root+local@frame.T)
    hair.data.resize_curves([points]*count)
    hair.data.set_types(type='POLY')
    hair.data.attributes['position'].data.foreach_set('vector',np.asarray(positions).ravel())
    hair.data.attributes['radius'].data.foreach_set('value',np.tile(np.linspace(.000075,.000012,points),count))
    hair.data.update_tag();hair.update_tag()
    return hair
