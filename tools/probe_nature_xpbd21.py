"""Zero-load native XPBD rest-shape test on sparse guides; no collision claim."""
from pathlib import Path
import sys,json
import bpy,numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
import hair_prototype20 as h20
from hair_nature21 import apply_to_hair

assert bpy.app.background and bpy.app.version[:2]==(5,2)
amount=float(sys.argv[sys.argv.index('--')+1])
loaded='gravity' in sys.argv[sys.argv.index('--')+2:]
iterations=next((int(arg.split('=')[1]) for arg in sys.argv if arg.startswith('iterations=')),12)
guide_count=4 if loaded and iterations>12 else 24
out=h20.ROOT/'validation/nature-cheveux-21';out.mkdir(exist_ok=True)
for obj in tuple(bpy.context.scene.objects):bpy.data.objects.remove(obj,do_unlink=True)
body=h20.load_body()
hair=h20.create_hair(body,count=guide_count)
fiber=apply_to_hair(hair,amount)
hair.data.set_types(type='POLY')
modifier=next(m for m in hair.modifiers if m.node_group and m.node_group.name=='Hair Dynamics')
mode=next(it for it in modifier.node_group.interface.items_tree if it.item_type=='SOCKET' and it.in_out=='INPUT' and it.name=='Mode')
value=getattr(modifier.properties.inputs,mode.identifier)
print('XPBD_MODE_ITEMS',[(item.identifier,item.name) for item in value.bl_rna.properties['value'].enum_items],flush=True)
value.value=next(item.identifier for item in value.bl_rna.properties['value'].enum_items if item.name=='Physics (Experimental)')
h20.set_input(modifier,'Substeps',4)
h20.set_input(modifier,'Constraint Steps',iterations)
h20.set_input(modifier,'Stretchiness',0.)
h20.set_input(modifier,'Bendiness',.2)
h20.set_input(modifier,'Root Bendiness',.1)
h20.set_input(modifier,'Randomness',False)
h20.set_input(modifier,'Surface Collision',False)
gravity=next(it for it in modifier.node_group.interface.items_tree if it.item_type=='SOCKET' and it.in_out=='INPUT' and it.name=='Gravity' and it.socket_type=='NodeSocketBool')
getattr(modifier.properties.inputs,gravity.identifier).value=loaded
for it in modifier.node_group.interface.items_tree:
 if it.item_type=='SOCKET' and it.in_out=='INPUT' and it.name in ('Stretchiness','Bendiness','Mass','Constraint Steps','Substeps'):
  v=getattr(modifier.properties.inputs,it.identifier);print('SETTING',it.name,'value',v.value,'type',v.type,'enum',[(a.identifier,a.name) for a in v.bl_rna.properties['type'].enum_items],flush=True)
hair.update_tag()
rows=[];reference=None
for frame in range(1,13):
    bpy.context.scene.frame_set(frame)
    p=h20.evaluated_points(hair)
    assert np.isfinite(p).all()
    if reference is None:reference=p.copy()
    error=float(np.linalg.norm(p-reference,axis=1).max())
    n=len(hair.data.points)//guide_count
    roots=float(np.linalg.norm(p.reshape((-1,n,3))[:,0]-reference.reshape((-1,n,3))[:,0],axis=1).max())
    stretch=np.linalg.norm(np.diff(p.reshape((-1,n,3)),axis=1),axis=2).sum(axis=1)
    rows.append({'frame':frame,'maximum_displacement_m':error,'root_displacement_m':roots,'maximum_contour_length_m':float(stretch.max())})
    print('NATURE21_XPBD_FRAME',amount,frame,error,flush=True)
if loaded:
    assert max(row['maximum_displacement_m'] for row in rows)>1e-6,'Positive control: gravity must move the simulated guides'
else:
    assert max(row['maximum_displacement_m'] for row in rows)<.001,'Native solver did not preserve unloaded rest shape within 1 mm'
print('PHYSICS_ATTRIBUTES',[(a.name,a.data_type,a.domain) for a in hair.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.attributes],flush=True)
print('PHYSICS_WARNINGS',[(str(w),[(p.identifier,str(getattr(w,p.identifier,None))) for p in w.bl_rna.properties]) for w in modifier.node_warnings],flush=True)
extension=max(row['maximum_contour_length_m']/fiber.length_m-1 for row in rows)
report={'nature':amount,'curvature_m_inv':fiber.curvature_m_inv,'material_twist_m_inv':fiber.material_twist_m_inv,'mode':'Physics','backend':'native Blender 5.2 Hair Dynamics / XPBD','solver_curve_type':'POLY','guides':guide_count,'points_per_guide':len(hair.data.points)//guide_count,'gravity':loaded,'collisions':False,'iterations':iterations,'scope':'rest preservation / positive gravity control only, not a calibrated hair material','bendiness_experimental':.2,'frames':rows,'test_pass':True,'material_response_validated':False,'maximum_relative_extension':extension,'extension_below_5_percent':extension<.05,'usable_for_production':False}
(out/('xpbd-'+('gravite-' if loaded else 'repos-')+str(amount)+'-iterations'+str(iterations)+'.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
print('NATURE21_XPBD_POSITIVE_CONTROL' if loaded else 'NATURE21_XPBD_REST_PASS',amount,'relative_extension',extension,flush=True)
