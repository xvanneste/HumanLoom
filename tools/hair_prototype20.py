"""Isolated Hair Curves prototype; does not register or install an extension."""
from pathlib import Path
import math
import bpy
import numpy as np
from mathutils import Vector, Matrix

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'validation/cheveux-20'


def load_body():
    assert bpy.app.version[:2] == (5, 2), 'This prototype requires Blender 5.2.'
    with bpy.data.libraries.load(str(ROOT / 'tools/data/realistic.blend'), link=False) as (src, dst):
        dst.collections = ['Realistic Human Base']
    collection = dst.collections[0]
    bpy.context.scene.collection.children.link(collection)
    body = next(obj for obj in collection.objects if obj.get('human_modeling_body'))
    body.name = 'Prototype · corps éditable'
    subdiv = body.modifiers.new('Prototype · surface', 'SUBSURF')
    subdiv.levels = 1
    subdiv.render_levels = 2
    subdiv.uv_smooth = 'NONE'
    body.modifiers.move(len(body.modifiers) - 1, 0)
    return body


def scalp_samples(body, count=850, seed=2026):
    """Sample an original provisional scalp mask, retaining face/barycentric IDs."""
    mesh = body.data
    mesh.calc_loop_triangles()
    points = np.array([v.co[:] for v in mesh.vertices])
    triangles = np.array([tri.vertices[:] for tri in mesh.loop_triangles], dtype=np.int32)
    corners = points[triangles]
    center = corners.mean(axis=1)
    top = points[:, 2].max()
    frontness = np.clip((-center[:, 1] - .015) / .13, 0, 1)
    threshold = top - .145 + .10 * frontness
    selected = (corners[:, :, 2].min(axis=1) > threshold)
    selected &= ~((abs(center[:, 0]) > .071) & (center[:, 2] < top - .095))
    indices = np.flatnonzero(selected)
    areas = np.linalg.norm(np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]), axis=1) / 2
    rng = np.random.default_rng(seed)
    sampled = rng.choice(indices, count, p=areas[indices] / areas[indices].sum())
    raw = rng.random((count, 2))
    raw[raw.sum(axis=1) > 1] = 1 - raw[raw.sum(axis=1) > 1]
    weights = np.column_stack((1 - raw.sum(axis=1), raw))
    roots = np.einsum('ni,nij->nj', weights, corners[sampled])
    normals = np.cross(corners[sampled, 1] - corners[sampled, 0], corners[sampled, 2] - corners[sampled, 0])
    normals /= np.linalg.norm(normals, axis=1)[:, None]
    uv_data = mesh.uv_layers.active.data
    uv_corners = np.array([[uv_data[loop].uv[:] for loop in mesh.loop_triangles[int(index)].loops] for index in sampled])
    uvs = np.einsum('ni,nij->nj', weights, uv_corners)
    mask = np.zeros(len(mesh.vertices), dtype=np.float32)
    mask[np.unique(triangles[indices])] = 1.
    return roots, normals, uvs, sampled, weights, mask


def write_attribute(data, name, kind, domain, values, field):
    attribute = data.attributes.get(name) or data.attributes.new(name, kind, domain)
    attribute.data.foreach_set(field, np.asarray(values).ravel())
    return attribute


def create_hair(body, count=850, seed=2026):
    """Use the native 5.2 operator for the surface/rest/dynamics setup."""
    if not body.data.uv_layers.active:
        raise ValueError('The body needs an attachment UV map.')
    roots, normals, uv, faces, weights, mask = scalp_samples(body, count, seed)
    write_attribute(body.data, 'hm_scalp_density', 'FLOAT', 'POINT', mask, 'value')
    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    assert bpy.ops.object.curves_empty_hair_add() == {'FINISHED'}
    hair = bpy.context.object
    hair.name = 'Prototype · cheveux courts · guides'
    hair.parent = body
    hair.matrix_parent_inverse = Matrix.Identity(4)
    hair.matrix_basis = Matrix.Identity(4)
    data = hair.data
    data.name = 'Guides éditables · Hair Curves 5.2'
    data.add_curves([8] * count)
    data.set_types(type='CATMULL_ROM')
    rng = np.random.default_rng(seed + 1)
    lengths = rng.uniform(.027, .048, count)
    positions = []
    for root, normal, length in zip(roots, normals, lengths):
        # Tangential sweep towards the back; a small lateral part remains provisional.
        flow = np.array([.32, 1., -.10])
        tangent = flow - normal * np.dot(flow, normal)
        tangent /= max(np.linalg.norm(tangent), 1e-8)
        for t in np.linspace(0, 1, 8):
            positions.append(root + normal * length * (.72*t - .24*t*t) + tangent * length * .78*t*t)
    write_attribute(data, 'position', 'FLOAT_VECTOR', 'POINT', positions, 'vector')
    write_attribute(data, 'surface_uv_coordinate', 'FLOAT2', 'CURVE', uv, 'vector')
    write_attribute(data, 'hm_root_triangle', 'INT', 'CURVE', faces, 'value')
    write_attribute(data, 'hm_root_barycentric', 'FLOAT_VECTOR', 'CURVE', weights, 'vector')
    write_attribute(data, 'hm_root_id', 'INT', 'CURVE', np.arange(count), 'value')
    radii = np.tile(np.linspace(.000075, .000012, 8), count)
    write_attribute(data, 'radius', 'FLOAT', 'POINT', radii, 'value')
    hair['hm_hair_prototype'] = 1
    hair['hm_hair_seed'] = seed
    hair['hm_hair_style'] = 'short_swept_experimental_01'
    hair['hm_hair_source'] = 'Original procedural guides; native Blender 5.2 node assets'
    hair['hm_hair_surface_vertices'] = len(body.data.vertices)
    data.surface = body
    data.surface_uv_map = body.data.uv_layers.active.name
    data.use_sculpt_collision = True
    data.surface_collision_distance = .001
    # Store the native mode explicitly; socket identifiers are obtained from its interface.
    modifier = hair.modifiers[0]
    mode = next(item for item in modifier.node_group.interface.items_tree if item.item_type == 'SOCKET' and item.in_out == 'INPUT' and item.name == 'Mode')
    mode_input = getattr(modifier.properties.inputs, mode.identifier)
    animation = next(item.identifier for item in mode_input.bl_rna.properties['value'].enum_items if item.name == 'Animation')
    mode_input.value = animation
    hair.update_tag()
    return hair


def native_group(name):
    existing = bpy.data.node_groups.get(name)
    if existing:
        return existing
    path = Path(bpy.utils.system_resource('DATAFILES'))/'assets/nodes/procedural_hair_node_assets.blend'
    with bpy.data.libraries.load(str(path), link=False) as (src, dst):
        if name not in src.node_groups:
            raise ValueError('Missing native Blender 5.2 group: ' + name)
        dst.node_groups = [name]
    return dst.node_groups[0]


def set_input(modifier, name, value):
    items = [item for item in modifier.node_group.interface.items_tree if item.item_type == 'SOCKET' and item.in_out == 'INPUT' and item.name == name]
    if len(items) != 1:
        raise ValueError('Ambiguous or missing modifier input: ' + name)
    socket = getattr(modifier.properties.inputs, items[0].identifier)
    socket.value = value


def add_density(hair):
    """Native interpolation on the masked rest surface, before native following."""
    group = bpy.data.node_groups.new('Prototype · densité sur cuir chevelu', 'GeometryNodeTree')
    group.interface.new_socket(name='Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    group.interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    density = group.interface.new_socket(name='Density', in_out='INPUT', socket_type='NodeSocketFloat')
    density.default_value = 600000.
    density.min_value = 0.
    density.max_value = 2000000.
    viewport = group.interface.new_socket(name='Viewport Amount', in_out='INPUT', socket_type='NodeSocketFloat')
    viewport.default_value = .35
    viewport.min_value = 0.
    viewport.max_value = 1.
    seed = group.interface.new_socket(name='Seed', in_out='INPUT', socket_type='NodeSocketInt')
    seed.default_value = hair['hm_hair_seed']
    source = group.nodes.new('NodeGroupInput')
    output = group.nodes.new('NodeGroupOutput')
    interpolate = group.nodes.new('GeometryNodeGroup')
    interpolate.node_tree = native_group('Interpolate Hair Curves')
    interpolate.inputs['Resting Surface'].default_value = True
    interpolate.inputs['Distance to Guides'].default_value = .045
    attribute = group.nodes.new('GeometryNodeInputNamedAttribute')
    attribute.data_type = 'FLOAT'
    attribute.inputs['Name'].default_value = 'hm_scalp_density'
    group.links.new(source.outputs['Geometry'], interpolate.inputs['Geometry'])
    for name in ('Density','Viewport Amount','Seed'):
        group.links.new(source.outputs[name], interpolate.inputs[name])
    group.links.new(attribute.outputs['Attribute'], interpolate.inputs['Density Mask'])
    group.links.new(interpolate.outputs['Geometry'], output.inputs['Geometry'])
    source.location = (-520,120)
    attribute.location = (-520,-140)
    interpolate.location = (-180,100)
    output.location = (220,120)
    modifier = hair.modifiers.new('Prototype · densité', 'NODES')
    modifier.node_group = group
    hair.modifiers.move(len(hair.modifiers)-1,0)
    length = hair.modifiers.new('Prototype · longueur', 'NODES')
    length.node_group = native_group('Trim Hair Curves')
    set_input(length,'Replace Length',False)
    set_input(length,'Length Factor',1.)
    hair.modifiers.move(len(hair.modifiers)-1,0)
    profile = hair.modifiers.new('Prototype · épaisseur', 'NODES')
    profile.node_group = native_group('Set Hair Curve Profile')
    set_input(profile,'Replace Radius',True)
    set_input(profile,'Radius',.000075)


def assign_hair_material(hair, material):
    """Assign explicitly in the evaluated graph, including interpolated strands."""
    group = bpy.data.node_groups.new('Prototype · matière des mèches', 'GeometryNodeTree')
    group.interface.new_socket(name='Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    group.interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    source = group.nodes.new('NodeGroupInput')
    output = group.nodes.new('NodeGroupOutput')
    assign = group.nodes.new('GeometryNodeSetMaterial')
    assign.inputs['Material'].default_value = material
    group.links.new(source.outputs['Geometry'],assign.inputs['Geometry'])
    group.links.new(assign.outputs['Geometry'],output.inputs['Geometry'])
    source.location = (-300,0)
    assign.location = (0,0)
    output.location = (250,0)
    mod = hair.modifiers.new('Prototype · matière', 'NODES')
    mod.node_group = group


def material(name, color, hair=False):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    if hair:
        nodes.clear()
        shader = nodes.new('ShaderNodeBsdfHairPrincipled')
        shader.parametrization = 'COLOR'
        shader.inputs['Color'].default_value = (*color, 1)
        shader.inputs['Roughness'].default_value = .4
        output = nodes.new('ShaderNodeOutputMaterial')
        mat.node_tree.links.new(shader.outputs[0], output.inputs['Surface'])
    else:
        shader = nodes.get('Principled BSDF')
        shader.inputs['Base Color'].default_value = (*color, 1)
        shader.inputs['Roughness'].default_value = .65
    return mat


def evaluated_points(hair):
    bpy.context.view_layer.update()
    evaluated = hair.evaluated_get(bpy.context.evaluated_depsgraph_get())
    positions = np.empty((len(evaluated.data.points), 3), dtype=np.float32)
    evaluated.data.attributes['position'].data.foreach_get('vector', positions.ravel())
    return positions


def frame_camera(scene, target, distance, view):
    camera = scene.camera
    if camera is None:
        data = bpy.data.cameras.new('Camera inspection')
        camera = bpy.data.objects.new('Camera inspection', data)
        scene.collection.objects.link(camera)
        scene.camera = camera
    camera.location = Vector(target) + Vector(view).normalized() * distance
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = distance


def setup_render(body, hair):
    scene = bpy.context.scene
    clay = material('Peau · argile neutre', (.39, .43, .48))
    for obj in (body, *body.children):
        if obj.type == 'MESH':
            obj.data.materials.clear()
            obj.data.materials.append(clay)
            for polygon in obj.data.polygons:
                polygon.use_smooth = True
    hair_material = material('Cheveux · brun · Cycles', (.045, .016, .008), hair=True)
    hair.data.materials.append(hair_material)
    assign_hair_material(hair, hair_material)
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1100
    scene.render.resolution_y = 1100
    scene.render.resolution_percentage = 100
    scene.world.color = (.25, .25, .25)
    for location, power, size in [((2,-3,4),110,3),((-2,-1,2.5),65,2),((0,2,3),120,2)]:
        data = bpy.data.lights.new('Lumière inspection', 'AREA')
        data.energy = power
        data.shape = 'DISK'
        data.size = size
        light = bpy.data.objects.new(data.name, data)
        scene.collection.objects.link(light)
        light.location = location
        light.rotation_euler = (Vector((0,-.05,1.5))-light.location).to_track_quat('-Z','Y').to_euler()
    frame_camera(scene, (0,-.045,1.49), .52, (0,-1,.12))


def make_scene():
    if not bpy.app.background:
        raise RuntimeError('Build this isolated prototype with --background --factory-startup, not inside a working scene.')
    OUT.mkdir(exist_ok=True)
    for obj in tuple(bpy.context.scene.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    body = load_body()
    hair = create_hair(body)
    add_density(hair)
    setup_render(body, hair)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                area.spaces.active.region_3d.view_perspective = 'CAMERA'
    return body, hair
