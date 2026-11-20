"""Inspect the exported reference bodies in Blender 5.2, without editing sources."""
from pathlib import Path
import sys,json,math
import bpy,numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
import audit_added_humans16 as audit

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'validation/unreal-17/blender';OUT.mkdir(parents=True,exist_ok=True)
audit.OUT=OUT;rows=[]
for source_name,label in (('MHC_Base_Female','MetaHuman-feminin'),('MHC_Base_Male','MetaHuman-masculin')):
    path=ROOT/'validation/unreal-17/exports'/(source_name+'_FullBody.fbx')
    if not path.exists() or path.stat().st_size<1000:path=path.with_suffix('.obj')
    assert path.exists() and path.stat().st_size>1000,path
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if path.suffix=='.fbx':bpy.ops.import_scene.fbx(filepath=str(path),use_anim=False)
    else:bpy.ops.wm.obj_import(filepath=str(path),forward_axis='NEGATIVE_Y',up_axis='Z')
    objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and len(o.data.vertices)]
    # Asset-local axes differ from Unreal actor-forward axes. Review confirmed
    # the CPU export faces -X; rotate the inspection copy to Blender's -Y.
    if path.suffix=='.obj':
        for obj in objects:
            obj.rotation_euler.z+=math.pi/2
            for polygon in obj.data.polygons:polygon.use_smooth=True
        bpy.context.view_layer.update()
    row={'id':label,'source':audit.fingerprint(path),'blender':bpy.app.version_string,
         'armatures':[{'name':o.name,'bones':len(o.data.bones)} for o in bpy.context.scene.objects if o.type=='ARMATURE'],
         'display_rotation_z_degrees':90 if path.suffix=='.obj' else 0,
         'meshes':[]};chunks=[]
    for obj in objects:
        report,points=audit.describe(obj);row['meshes'].append(report);chunks.append(points)
    points=np.concatenate(chunks);row['combined_extents']=np.ptp(points,axis=0).tolist()
    assert np.isfinite(points).all() and np.ptp(points[:,2])>.5,'Import scale/orientation needs review'
    audit.render(label,objects,points)
    rows.append(row);(OUT/'inventaire-metahuman-blender.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    print('METAHUMAN_BLENDER_INSPECTION',label,row['combined_extents'],flush=True)
