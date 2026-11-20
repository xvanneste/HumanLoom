"""Standalone geometric comparison at equal contour length, not a biological chart."""
from pathlib import Path
import math,sys,json
import bpy,numpy as np
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from hair_nature21 import nature,sample_rest
import hair_prototype20 as h20

assert bpy.app.background and bpy.app.version[:2]==(5,2)
out=h20.ROOT/'validation/nature-cheveux-21';out.mkdir(exist_ok=True)
for obj in tuple(bpy.context.scene.objects):bpy.data.objects.remove(obj,do_unlink=True)
scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.render.resolution_x=1800;scene.render.resolution_y=850
scene.world.color=(.4,.4,.4)
mat=h20.material('Fibre de démonstration',(.14,.045,.012))
textmat=h20.material('Légendes',(.75,.75,.75))
def text(value,x,z,size=.005):
    data=bpy.data.curves.new(value,'FONT');data.body=value;data.size=size;data.align_x='CENTER'
    obj=bpy.data.objects.new(value,data);scene.collection.objects.link(obj)
    obj.location=(x,-.02,z);obj.rotation_euler=(math.pi/2,0,0)
    data.materials.append(textmat)
rows=[]
for index,(amount,label) in enumerate(((0.,'Lisse'),(.25,'Ondule'),(.5,'Boucle'),(.75,'Frise'),(1.,'Crepu'))):
    fiber=nature(amount)
    points=sample_rest(fiber)
    q=math.hypot(fiber.curvature_m_inv,fiber.material_twist_m_inv)
    if q>1e-9:
        sine=fiber.curvature_m_inv/q;cosine=fiber.material_twist_m_inv/q
        t=np.array([sine,0.,cosine]);d1=np.array([-cosine,0.,sine]);d2=np.cross(t,d1)
        points=points@np.column_stack((d1,d2,t)).T
    x=(index-2)*.062
    points[:,0]+=x
    data=bpy.data.curves.new(label+' · 60 mm','CURVE');data.dimensions='3D';data.bevel_depth=.00030;data.bevel_resolution=3
    line=data.splines.new('POLY');line.points.add(len(points)-1)
    for point,position in zip(line.points,points):point.co=(*position,1)
    obj=bpy.data.objects.new(data.name,data);scene.collection.objects.link(obj);data.materials.append(mat)
    text(label,x,-.010)
    text('60 mm',x,-.019,.0038)
    rows.append({'label':label,'nature':amount,'length_m':fiber.length_m,'points_m':points.tolist()})
text('Meme longueur de fibre, formes au repos differentes',0,.081,.0058)
text('Exemples geometriques · epaisseur exageree pour la lisibilite',0,-.033,.004)
h20.frame_camera(scene,(0,0,.026),.34,(0,-1,.05))
for location,power in [((0,-.4,.4),8),((-.3,-.2,.25),4)]:
    data=bpy.data.lights.new('Eclairage','AREA');data.energy=power;data.size=.35
    obj=bpy.data.objects.new(data.name,data);scene.collection.objects.link(obj);obj.location=location
    obj.rotation_euler=(Vector((0,0,.03))-obj.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(out/'Comparaison-fibres-60mm.png')
bpy.ops.render.render(write_still=True)
(out/'fibres-comparaison.json').write_text(json.dumps(rows),encoding='utf-8')
print('FIBER21_FIGURE_DONE',flush=True)
