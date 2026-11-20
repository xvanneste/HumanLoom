"""Normalized visual comparison and explicit non-clinical section descriptors."""
from pathlib import Path
import sys,json,math,importlib
import bpy,numpy as np
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit_added_humans16 import render
from atlas_fit14 import perimeter
from experimental_growth_field import anatomy

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'validation/references-humaines-16'
source=next(Path('G:/_dev/BlenderDev').glob('FREE_Stylized*/maya/*extracted/Cena_FBX.fbx'))
for obj in tuple(bpy.context.scene.objects):bpy.data.objects.remove(obj,do_unlink=True)
bpy.ops.import_scene.fbx(filepath=str(source),use_anim=False)
external=next(o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.endswith(':Body'))
external.name='Référence ajoutée · Homme stylisé'
# FBX null parents carry the centimetre conversion and Y-up rotation. Keep
# their world transform when removing presentation objects and hierarchy.
transform=external.matrix_world.copy();external.parent=None;external.matrix_world=transform
eyes=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.endswith(':Eye')]
for eye in eyes:
    transform=eye.matrix_world.copy();eye.parent=external;eye.matrix_world=transform
for obj in tuple(bpy.context.scene.objects):
    if obj!=external and obj not in eyes:bpy.data.objects.remove(obj,do_unlink=True)
external.modifiers.new('Comparaison surface lissée niveau 2','SUBSURF').levels=2
addon=importlib.import_module('bl_ext.user_default.human_modeling')
addon.ASSET_PATH=ROOT/'validation/proportions-14/candidat-adulte-15.blend'
bpy.ops.human_modeling.create();native=bpy.context.object;native.name='Notre candidat adulte · Masculin neutre'
keys=native.data.shape_keys;keys.key_blocks['Morphologie'].value=1.;keys['human_modeling_age']=2.;keys['hm_whole_body']=0.;keys['hm_muscles']=0.;keys.update_tag()
native.modifiers['Human Modeling · Surface'].levels=2
bpy.context.view_layer.update();reports=[]
def surface(obj):
    evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
    try:
        p=np.array([obj.matrix_world@v.co for v in mesh.vertices]);mesh.calc_loop_triangles()
        return p,np.array([t.vertices[:] for t in mesh.loop_triangles])
    finally:evaluated.to_mesh_clear()

for body,x in ((native,-.55),(external,.55)):
    points,faces=surface(body);floor=float(points[:,2].min());height=float(np.ptp(points[:,2]));rows=[]
    if body==external:assert 2.<height<2.1,('FBX import transform was lost',height)
    centered=points.copy();centered[:,0]-=(points[:,0].max()+points[:,0].min())/2
    for fraction in (.25,.37,.53,.61,.72,.82):
        row={'height_fraction':fraction}
        try:
            loops,_=anatomy.section_loops(centered,faces,floor+height*fraction)
            # A central closed loop is a technical torso section. Otherwise
            # choose the right leg. No measured anatomical name is inferred.
            central=[loop for loop in loops if anatomy.encloses_axis(loop)]
            selected=central if central else [loop for loop in loops if loop[:,0].mean()>0]
            loop=max(selected,key=lambda loop:perimeter(loop))
            row.update(loop_count=len(loops),selection='central' if central else 'positive-X component',
                       width_over_height=float(np.ptp(loop[:,0])/height),depth_over_height=float(np.ptp(loop[:,1])/height),
                       convex_perimeter_over_height=perimeter(loop)/height)
            if central and fraction>=.70 and len(loops)==1:
                row['interpretation']='Connected upper-body contour may include arms; do not interpret as an isolated torso girth'
        except (ValueError,IndexError) as error:row['unavailable']=str(error)
        rows.append(row)
    reports.append({'body':body.name,'evaluated_height_before_normalization':height,'subdivision':2,'sections':rows})
    factor=1.8/height;body.scale*=factor;body.location.x+=x;body.location.z-=floor*factor
    for obj in (body,*body.children):
        if obj.type=='MESH':
            for polygon in obj.data.polygons:polygon.use_smooth=True
bpy.context.view_layer.update()
for body in (native,external):assert abs(np.ptp(surface(body)[0][:,2])-1.8)<1e-4,'Normalization mismatch'
allpoints=np.concatenate([surface(body)[0] for body in (native,external)])
render('comparaison-masculine-normalisee',[native,external],allpoints,paired=True)
(OUT/'comparaison-sections.json').write_text(json.dumps({'scope':'Technical surface sections at common stature fractions, not palpated landmarks or clinical girths. The reference is stylized, not a population norm. Both preview bodies normalized to 1.80 scene units for shape comparison only. Native on left, supplied stylized reference on right.','bodies':reports},indent=2),encoding='utf-8')
print('NORMALIZED_REFERENCE_COMPARISON_SAVED',flush=True)
