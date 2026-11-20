"""Render full-body views and report geometry checks on the age reference scene."""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


def inspect_mesh(obj):
    mesh = bmesh.new()
    mesh.from_mesh(obj.data)
    report = {
        "name": obj.name,
        "vertices": len(mesh.verts),
        "faces": len(mesh.faces),
        "boundary_edges": sum(edge.is_boundary for edge in mesh.edges),
        "nonmanifold_edges": sum(not edge.is_manifold for edge in mesh.edges),
        "zero_area_faces": sum(face.calc_area() < 1e-12 for face in mesh.faces),
        "nonfinite_vertices": sum(
            not all(math.isfinite(value) for value in vertex.co) for vertex in mesh.verts
        ),
    }
    remaining = set(mesh.verts)
    components = []
    while remaining:
        stack = [remaining.pop()]
        count = 0
        while stack:
            vertex = stack.pop()
            count += 1
            for edge in vertex.link_edges:
                other = edge.other_vert(vertex)
                if other in remaining:
                    remaining.remove(other)
                    stack.append(other)
        components.append(count)
    report["component_sizes"] = sorted(components, reverse=True)
    mesh.free()
    return report


def main():
    output = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    camera = scene.camera
    camera.location = (0, -10, .88)
    camera.rotation_euler = (Vector((0, 0, .88)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.ortho_scale = 5.2
    scene.render.resolution_x = 2400
    scene.render.resolution_y = 1100
    scene.render.resolution_percentage = 100
    scene.display.shading.show_cavity = False
    scene.display.shading.show_shadows = False
    families = [bpy.data.collections[name] for name in ("Féminine", "Masculine")]
    reports = []
    for family in families:
        family.hide_viewport = False
        objects = sorted(family.objects, key=lambda obj: obj["source_age_parameter"])
        for index, obj in enumerate(objects):
            obj.location = ((index - 1.5) * 1.25, 0, -min(vertex.co.z for vertex in obj.data.vertices))
            reports.append(inspect_mesh(obj))
    for current in families:
        for family in families:
            family.hide_render = family is not current
        for name, angle in (("face", 0), ("trois-quarts", math.pi / 4), ("profil", math.pi / 2)):
            for obj in current.objects:
                obj.rotation_euler.z = angle
            scene.render.filepath = str(output / f"{current.name}-corps-{name}.png")
            bpy.ops.render.render(write_still=True)
    (output / "controle-geometrie.json").write_text(
        json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(reports, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
