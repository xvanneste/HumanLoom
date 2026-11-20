"""Temporary, topology-bound torso/arm segmentation for contour diagnostics.

The survey tape surrounds the torso, not the arms. Material IDs are used only
as temporary discrete face labels inherited by Subdivision; original materials
are restored. The anatomical region boundary remains subject to visual review.
"""
import heapq
from contextlib import contextmanager
import bpy,numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree
from atlas_fit14 import perimeter


def plane_points(points,faces,level):
    triangles=points[faces];out=[]
    for i,j in ((0,1),(1,2),(2,0)):
        a=triangles[:,i];b=triangles[:,j];dz=b[:,2]-a[:,2]
        selected=((a[:,2]<=level)&(b[:,2]>level))|((b[:,2]<=level)&(a[:,2]>level))
        t=(level-a[selected,2])/dz[selected]
        out.append(a[selected]+t[:,None]*(b[selected]-a[selected]))
    return np.concatenate(out)


def classify(mesh,rest,level,anatomy):
    loops,_=anatomy.section_loops(rest,np.array([t.vertices[:] for t in mesh.loop_triangles]),level)
    assert len(loops)>=3,'A separated neutral torso/arm section is required for region seeding'
    tree=KDTree(sum(map(len,loops)));counter=0
    for loop in loops:
        label=0 if anatomy.encloses_axis(loop) else 1
        for point in loop:tree.insert(Vector(point),counter*2+label);counter+=1
    tree.balance();seeds={};adjacency=[set() for _ in mesh.polygons];edges={}
    for polygon in mesh.polygons:
        for edge in polygon.edge_keys:
            if edge in edges:
                other=edges[edge];adjacency[polygon.index].add(other);adjacency[other].add(polygon.index)
            else:edges[edge]=polygon.index
    for triangle in mesh.loop_triangles:
        vertices=rest[list(triangle.vertices)]
        if vertices[:,2].min()<=level<vertices[:,2].max():
            hits=plane_points(rest,np.array([triangle.vertices[:]]),level)
            if len(hits):seeds[triangle.polygon_index]=tree.find(Vector(hits[0]))[1]%2
    centers=np.array([rest[list(p.vertices)].mean(0) for p in mesh.polygons])
    distance=np.full(len(centers),np.inf);labels=np.full(len(centers),-1,dtype=int);queue=[]
    for index,label in seeds.items():distance[index]=0.;labels[index]=label;heapq.heappush(queue,(0.,index))
    while queue:
        gap,index=heapq.heappop(queue)
        if gap!=distance[index]:continue
        for neighbor in adjacency[index]:
            trial=gap+np.linalg.norm(centers[index]-centers[neighbor])
            if trial<distance[neighbor]:
                distance[neighbor]=trial;labels[neighbor]=labels[index];heapq.heappush(queue,(trial,neighbor))
    assert np.all(labels>=0)
    return labels


@contextmanager
def tagged(body,rest,level,anatomy):
    mesh=body.data;mesh.calc_loop_triangles();labels=classify(mesh,rest,level,anatomy)
    original=np.array([p.material_index for p in mesh.polygons]);start=len(mesh.materials)
    materials=[bpy.data.materials.new('Temporary torso contour tag'),bpy.data.materials.new('Temporary arm contour tag')]
    for mat in materials:mesh.materials.append(mat)
    for polygon,label in zip(mesh.polygons,labels):polygon.material_index=start+int(label)
    mesh.update();bpy.context.view_layer.update()
    try:yield start
    finally:
        for polygon,index in zip(mesh.polygons,original):polygon.material_index=int(index)
        mesh.materials.pop(index=start+1);mesh.materials.pop(index=start)
        for mat in materials:bpy.data.materials.remove(mat)
        mesh.update();bpy.context.view_layer.update()


def measure(body,level,tag):
    evaluated=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
    try:
        mesh.calc_loop_triangles();points=np.array([v.co[:] for v in mesh.vertices])
        faces=np.array([t.vertices[:] for t in mesh.loop_triangles if t.material_index==tag])
        return perimeter(plane_points(points,faces,level))
    finally:evaluated.to_mesh_clear()
