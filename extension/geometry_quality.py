"""Geometry diagnostics with explicit limits on surface-intersection detection."""

import hashlib

import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def segment_hits(starts, ends, triangles):
    """Strict, transverse segment/triangle crossings (no coplanar contacts)."""
    edge1, edge2 = triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]
    direction = ends - starts
    p = np.cross(direction, edge2)
    determinant = np.einsum("ij,ij->i", edge1, p)
    threshold = np.linalg.norm(edge1, axis=1) * np.linalg.norm(edge2, axis=1) * np.linalg.norm(direction, axis=1) * 1e-10
    usable = np.abs(determinant) > np.maximum(threshold, 1e-24)
    inverse = np.zeros_like(determinant)
    inverse[usable] = 1 / determinant[usable]
    offset = starts - triangles[:, 0]
    u = np.einsum("ij,ij->i", offset, p) * inverse
    q = np.cross(offset, edge1)
    v = np.einsum("ij,ij->i", direction, q) * inverse
    along = np.einsum("ij,ij->i", edge2, q) * inverse
    tolerance = 1e-7
    return usable & (u > tolerance) & (v > tolerance) & (u + v < 1 - tolerance) & (along > tolerance) & (along < 1 - tolerance)


def intersections(coords, triangles, triangle_budget=250_000):
    if len(triangles) > triangle_budget:
        return {"status": "not_computed", "reason": "Triangle budget exceeded", "triangle_budget": triangle_budget}
    tree = BVHTree.FromPolygons([Vector(point) for point in coords], triangles.tolist(), all_triangles=True)
    vertex_sets = [set(face) for face in triangles]
    candidates = sorted({(a, b) for a, b in tree.overlap(tree) if a < b and not vertex_sets[a].intersection(vertex_sets[b])})
    pairs = np.array(candidates, dtype=np.int32).reshape((-1, 2))
    hit = np.zeros(len(pairs), dtype=bool)
    if len(pairs):
        a, b = coords[triangles[pairs[:, 0]]], coords[triangles[pairs[:, 1]]]
        for first, second in ((a, b), (b, a)):
            for edge in range(3):
                hit |= segment_hits(first[:, edge], first[:, (edge + 1) % 3], second)
    crossing = pairs[hit]
    extent = max(float(np.ptp(coords[:, 2])), 1e-9)
    floor = float(coords[:, 2].min())
    regions = {}
    for a, b in crossing:
        center = coords[triangles[[a, b]].reshape(-1)].mean(axis=0)
        z = (center[2] - floor) / extent
        region = "head" if z > .85 else "feet" if z < .1 else "hands_arms" if abs(center[0]) > extent * .12 else "legs_pelvis" if z < .55 else "torso"
        regions[region] = regions.get(region, 0) + 1
    return {"status": "computed", "crossing_triangle_pairs": len(crossing),
            "approximate_regions": regions,
            "bvh_candidates": len(candidates), "sample_triangle_pairs": crossing[:200].tolist(),
            "limitations": "Strict transverse crossings of triangles without shared vertices. Coplanar contact, nested closed shells and adjacent-face foldovers are not detected."}


def inspect_mesh(mesh, check_intersections=True):
    coords = np.empty(len(mesh.vertices) * 3)
    mesh.vertices.foreach_get("co", coords)
    coords = coords.reshape((-1, 3))
    finite = bool(np.isfinite(coords).all())
    report = {"vertices": len(mesh.vertices), "edges": len(mesh.edges), "faces": len(mesh.polygons), "finite_coordinates": finite,
              "geometry_sha256": hashlib.sha256(coords.astype("<f8").tobytes()).hexdigest()}
    if not finite or not len(coords):
        report["status"] = "invalid_coordinates_or_empty"
        return report
    # Read indexed evaluated topology directly. BMesh.from_mesh can traverse
    # inherited shape-key layers whose cage size differs after subdivision.
    edges = np.empty(len(mesh.edges)*2,dtype=np.int32)
    mesh.edges.foreach_get("vertices",edges)
    edges = edges.reshape((-1,2))
    edge_indices = np.empty(len(mesh.loops),dtype=np.int32)
    mesh.loops.foreach_get("edge_index",edge_indices)
    uses = np.bincount(edge_indices,minlength=len(mesh.edges))
    parents = list(range(len(coords)))
    def root(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i
    components = len(coords)
    for a,b in edges:
        ra,rb = root(int(a)),root(int(b))
        if ra != rb:
            parents[rb] = ra
            components -= 1
    areas = np.empty(len(mesh.polygons))
    mesh.polygons.foreach_get("area",areas)
    report.update(components=components,boundary_edges=int((uses==1).sum()),
                  non_manifold_edges=int((uses!=2).sum()),zero_area_faces=int((areas<=1e-12).sum()))
    mesh.calc_loop_triangles()
    triangles = np.empty(len(mesh.loop_triangles) * 3, dtype=np.int32)
    mesh.loop_triangles.foreach_get("vertices", triangles)
    triangles = triangles.reshape((-1, 3))
    report["triangles"] = len(triangles)
    report["intersections"] = intersections(coords, triangles) if check_intersections else {"status": "not_requested"}
    report["status"] = "diagnostic_only"
    return report


def eye_fit(body, context):
    def data(obj):
        evaluated=obj.evaluated_get(context.evaluated_depsgraph_get())
        mesh=evaluated.to_mesh()
        try:
            mesh.calc_loop_triangles()
            points=np.array([v.co[:] for v in mesh.vertices])
            matrix=np.array(obj.matrix_world)
            points=(matrix[:3,:3]@points.T).T+matrix[:3,3]
            faces=np.array([t.vertices[:] for t in mesh.loop_triangles],dtype=np.int32)
            return points,faces
        finally:evaluated.to_mesh_clear()
    eyes=[o for o in body.children if o.type=='MESH' and o.data.shape_keys and 'Morphologie' in o.data.shape_keys.key_blocks]
    if not eyes:return {'status':'no_separate_eyes','eyes':[]}
    bp,bf=data(body)
    if len(bf)>250000:return {'status':'not_computed','reason':'Triangle budget exceeded'}
    tree=BVHTree.FromPolygons([Vector(p) for p in bp],bf.tolist(),all_triangles=True)
    results=[]
    for eye in eyes:
        ep,ef=data(eye)
        other=BVHTree.FromPolygons([Vector(p) for p in ep],ef.tolist(),all_triangles=True)
        pairs=np.array(sorted(set(tree.overlap(other))),dtype=np.int32).reshape((-1,2))
        hits=np.zeros(len(pairs),dtype=bool)
        if len(pairs):
            a,b=bp[bf[pairs[:,0]]],ep[ef[pairs[:,1]]]
            for first,second in ((a,b),(b,a)):
                for edge in range(3):hits|=segment_hits(first[:,edge],first[:,(edge+1)%3],second)
        results.append({'name':eye.name,'crossing_triangle_pairs':int(hits.sum())})
    return {'status':'computed','eyes':results,'limitations':'Strict transverse crossings including internal orbital geometry. Coplanar tangency and nested surfaces are excluded.'}


def report(body, context, check_intersections=True, include_eyes=False):
    evaluated = body.evaluated_get(context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try:
        result = inspect_mesh(mesh, check_intersections)
        result_report = {"format": "human_modeling.geometry_report", "version": 1, "character": body.name,
                "matrix_world": [list(row) for row in body.matrix_world],
                "method": "Evaluated body mesh in local coordinates; separate eyes and other objects excluded",
                "geometry": result, "scope": "Geometric diagnostic; does not certify anatomical correctness."}
    finally:
        evaluated.to_mesh_clear()
    if include_eyes:
        result_report["eye_fit"] = eye_fit(body, context)
    return result_report
