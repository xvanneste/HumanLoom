"""Separate rest-shape showcase, preserving the first hair prototype."""
from pathlib import Path
import sys,json
import bpy,numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
import hair_prototype20 as h20
from hair_nature21 import apply_to_hair

assert bpy.app.background and bpy.app.version[:2]==(5,2)
out=h20.ROOT/'validation/nature-cheveux-21';out.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(h20.OUT/'Prototype-cheveux-01.blend'))
body=next(o for o in bpy.context.scene.objects if o.get('human_modeling_body'))
original=next(o for o in bpy.context.scene.objects if o.get('hm_hair_prototype'))
original.hide_render=True
original.hide_set(True)
scene=bpy.context.scene
scene.cycles.samples=16
scene.render.resolution_x=800;scene.render.resolution_y=900
rows=[]
for amount,label in ((0.,'lisse'),(.25,'ondule'),(.5,'boucle'),(.75,'frise'),(1.,'crepu')):
    hair=original.copy();hair.data=original.data.copy()
    body.users_collection[0].objects.link(hair)
    hair.hide_render=False;hair.hide_set(False)
    hair.name='Nature · '+label
    # Prototype preview budget, independent of the biological nature parameter.
    h20.set_input(hair.modifiers['Prototype · densité'],'Density',120000.)
    h20.set_input(hair.modifiers['Prototype · densité'],'Viewport Amount',.35)
    root_uv=np.array([v.vector[:] for v in hair.data.attributes['surface_uv_coordinate'].data])
    fiber=apply_to_hair(hair,amount,length_m=.06)
    assert np.array_equal(root_uv,np.array([v.vector[:] for v in hair.data.attributes['surface_uv_coordinate'].data]))
    evaluated=h20.evaluated_points(hair)
    assert np.isfinite(evaluated).all()
    rows.append({'label':label,'amount':amount,'guides':len(hair.data.curves),'points_per_guide':len(hair.data.points)//len(hair.data.curves),'curvature_m_inv':fiber.curvature_m_inv,'material_twist_m_inv':fiber.material_twist_m_inv,'length_m':fiber.length_m,'root_uv_preserved':True})
    h20.frame_camera(scene,(0,-.045,1.52),.53,(.8,-1,.2))
    scene.render.filepath=str(out/('nature-'+label+'.png'))
    bpy.ops.render.render(write_still=True)
    hair.hide_render=True;hair.hide_set(True)
chosen=bpy.data.objects['Nature · crepu']
chosen.hide_render=False;chosen.hide_set(False)
for obj in bpy.context.selected_objects:obj.select_set(False)
chosen.select_set(True);bpy.context.view_layer.objects.active=chosen
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA'
bpy.ops.wm.save_as_mainfile(filepath=str(out/'Prototype-nature-cheveux-02.blend'),compress=True)
(out/'geometries-au-repos.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print('NATURE21_SHOWCASE_DONE',flush=True)
