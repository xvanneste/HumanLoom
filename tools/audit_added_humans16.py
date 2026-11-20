"""Read-only source audit; import copies into an isolated Blender 5.2 scene.

Bounds and mesh sections are geometric descriptors, never biological norms.
No source vertices are transferred to the extension by this script.
"""
from pathlib import Path
import sys,json,hashlib,zipfile,math
from collections import Counter
import bpy,bmesh,numpy as np
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
SOURCE=Path('G:/_dev/BlenderDev')
OUT=ROOT/'validation/references-humaines-16'


def fingerprint(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        while block:=f.read(8*1024*1024):h.update(block)
    return {'path':str(path),'bytes':path.stat().st_size,'sha256':h.hexdigest()}


def describe(obj):
    mesh=obj.data;points=np.array([obj.matrix_world@v.co for v in mesh.vertices])
    bm=bmesh.new();bm.from_mesh(mesh)
    degree=Counter(len(p.vertices) for p in mesh.polygons)
    todo=set(bm.verts);sizes=[]
    while todo:
        first=todo.pop();queue=[first];size=0
        while queue:
            v=queue.pop();size+=1
            for edge in v.link_edges:
                other=edge.other_vert(v)
                if other in todo:todo.remove(other);queue.append(other)
        sizes.append(size)
    report={'name':obj.name,'vertices':len(mesh.vertices),'faces':len(mesh.polygons),
            'polygon_sizes':dict(degree),'uv_layers':len(mesh.uv_layers),'shape_keys':len(mesh.shape_keys.key_blocks) if mesh.shape_keys else 0,
            'vertex_groups':len(obj.vertex_groups),'modifiers':[{'name':m.name,'type':m.type} for m in obj.modifiers],
            'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),
            'connected_components':len(sizes),'largest_components_vertices':sorted(sizes,reverse=True)[:12],
            'world_bounds_min':points.min(0).tolist(),'world_bounds_max':points.max(0).tolist(),
            'world_extents':np.ptp(points,axis=0).tolist(),'object_scale':list(obj.scale)}
    bm.free();return report,points


def render(label,objects,points,paired=False):
    scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH'
    scene.display.shading.light='STUDIO';scene.display.shading.color_type='SINGLE';scene.display.shading.single_color=(.55,.57,.60)
    scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH'
    scene.render.resolution_x=1600;scene.render.resolution_y=1400;scene.render.resolution_percentage=100
    if scene.world is None:scene.world=bpy.data.worlds.new('Fond neutre audit')
    scene.world.color=(.12,.12,.12)
    camera=bpy.data.objects.new('Audit orthographique',bpy.data.cameras.new('Audit orthographique'));scene.collection.objects.link(camera);scene.camera=camera;camera.data.type='ORTHO'
    low=points.min(0);high=points.max(0);target=Vector((low+high)/2);extent=float(np.ptp(points,axis=0).max());distance=max(extent*4,10.)
    locations=[o.location.copy() for o in objects]
    for name,yaw in (('face',0.),('profil',math.pi/2),('dos',math.pi),('trois-quarts',math.pi/4)):
        view=Vector((math.sin(yaw),-math.cos(yaw),0));horizontal=np.array((math.cos(yaw),math.sin(yaw),0))
        if paired:
            chunks=[]
            for i,(obj,original) in enumerate(zip(objects,locations)):
                offset=(i-.5)*1.1
                obj.location=original+Vector(horizontal*offset)-Vector((offset,0,0))
            bpy.context.view_layer.update()
            graph=bpy.context.evaluated_depsgraph_get()
            for obj in objects:
                evaluated=obj.evaluated_get(graph);mesh=evaluated.to_mesh()
                try:chunks.append(np.array([obj.matrix_world@v.co for v in mesh.vertices]))
                finally:evaluated.to_mesh_clear()
            points=np.concatenate(chunks);target=Vector((points.min(0)+points.max(0))/2)
        width=float(np.ptp(points@horizontal));height=float(np.ptp(points[:,2]))
        # Blender ortho_scale is the larger sensor dimension for landscape.
        camera.data.ortho_scale=max(width,height*1600/1400)*1.15
        camera.data.clip_end=distance*10;camera.data.clip_start=max(extent*1e-5,.001)
        camera.location=target+view*distance;camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
        scene.render.filepath=str(OUT/f'{label}-{name}.png');bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/f'{label}-inspection.blend'),compress=True)


def main():
    OUT.mkdir(parents=True,exist_ok=True);rows=[]
    tasks=[('homme-stylise',next(SOURCE.glob('FREE_Stylized*/maya/*extracted/Cena_FBX.fbx')),True),
           ('homme-stylise-obj',next(SOURCE.glob('FREE_Stylized*/maya/*extracted/Cena_OBJ.obj')),False),
           ('femme-yoga',next(SOURCE.glob('Beautiful*/fbx/*.fbx')),True)]
    for label,path,images in tasks:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        if path.suffix.lower()=='.fbx':bpy.ops.import_scene.fbx(filepath=str(path),use_anim=False)
        else:bpy.ops.wm.obj_import(filepath=str(path),forward_axis='NEGATIVE_Z',up_axis='Y')
        meshes=[o for o in bpy.context.scene.objects if o.type=='MESH' and len(o.data.vertices)]
        row={'id':label,'source':fingerprint(path),'blender':bpy.app.version_string,'unit_scale_length':bpy.context.scene.unit_settings.scale_length,
             'armatures':[{'name':o.name,'bones':len(o.data.bones)} for o in bpy.context.scene.objects if o.type=='ARMATURE'],'meshes':[]}
        allpoints=[]
        for obj in meshes:
            report,points=describe(obj);row['meshes'].append(report);allpoints.append(points)
        if allpoints:
            points=np.concatenate(allpoints);row['combined_extents']=np.ptp(points,axis=0).tolist()
            if images:render(label,meshes,points)
        rows.append(row);(OUT/'inventaire-maillages.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
        print('REFERENCE_AUDIT',label,len(meshes),row.get('combined_extents'),flush=True)
    package=next(SOURCE.glob('Ultimate*/metahuman/UE_5.6/*.mhpkg'));info=fingerprint(package)
    info['zip_container']=zipfile.is_zipfile(package)
    if info['zip_container']:
        with zipfile.ZipFile(package) as z:
            info['entries']=[{'name':i.filename,'bytes':i.file_size} for i in z.infolist()]
    else:
        with package.open('rb') as f:info['header_hex']=f.read(32).hex()
    (OUT/'inventaire-metahuman.json').write_text(json.dumps(info,indent=2),encoding='utf-8')
    print('ADDED_HUMANS_AUDIT_FINISHED',flush=True)


if __name__=='__main__':main()
