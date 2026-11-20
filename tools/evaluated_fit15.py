"""Measure the actual subdivided fitting surface, including torso face tags."""
import bpy,numpy as np
from semantic_torso14 import classify,plane_points
from atlas_fit14 import perimeter,section


class SurfaceMeter:
    def __init__(self,body,rest,levels,anatomy):
        self.anatomy=anatomy;self.levels=levels
        body.data.calc_loop_triangles();labels=classify(body.data,rest,levels['chest'],anatomy)
        self.mesh=bpy.data.meshes.new('Temporary evaluated fitting cage')
        self.mesh.from_pydata(rest.tolist(),[],[p.vertices[:] for p in body.data.polygons]);self.mesh.update()
        self.obj=bpy.data.objects.new('Temporary evaluated fitting surface',self.mesh)
        bpy.context.scene.collection.objects.link(self.obj)
        self.materials=[bpy.data.materials.new('Fitting torso tag'),bpy.data.materials.new('Fitting arm tag')]
        for material in self.materials:self.mesh.materials.append(material)
        for polygon,label in zip(self.mesh.polygons,labels):polygon.material_index=int(label)
        mod=self.obj.modifiers.new('Render surface for fitting','SUBSURF');mod.levels=2
        self.faces=None;self.torso=None

    def __call__(self,points):
        self.mesh.vertices.foreach_set('co',np.asarray(points,dtype=np.float32).ravel());self.mesh.update()
        bpy.context.view_layer.update();obj=self.obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=obj.to_mesh()
        try:
            p=np.empty(len(mesh.vertices)*3);mesh.vertices.foreach_get('co',p);p=p.reshape(-1,3)
            if self.faces is None:
                mesh.calc_loop_triangles();self.faces=np.array([t.vertices[:] for t in mesh.loop_triangles])
                self.torso=np.array([t.material_index==0 for t in mesh.loop_triangles])
            return np.array([perimeter(plane_points(p,self.faces[self.torso],self.levels[name])) if name=='chest'
                             else perimeter(section(p,self.faces,self.levels[name],self.anatomy))
                             for name in ('chest','waist','hips')])
        finally:obj.to_mesh_clear()

    def close(self):
        bpy.data.objects.remove(self.obj,do_unlink=True);bpy.data.meshes.remove(self.mesh)
        for material in self.materials:bpy.data.materials.remove(material)
