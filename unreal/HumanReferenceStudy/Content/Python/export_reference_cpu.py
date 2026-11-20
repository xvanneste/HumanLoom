"""Export source LOD0 geometry using Geometry Script, without render components."""
from pathlib import Path
import json,traceback
import unreal
project=Path(unreal.Paths.project_dir()).resolve();assert project.name=='HumanReferenceStudy'
out=project.parents[1]/'validation/unreal-17';dest=out/'exports';dest.mkdir(parents=True,exist_ok=True)
report={'engine':unreal.SystemLibrary.get_engine_version(),'method':'GeometryScript CopyMeshFromSkeletalMesh SourceModel LOD0','characters':[],
        'coordinates':'OBJ in metres, Blender Z-up, (x,y,z)=(UE.y,-UE.x,UE.z)*0.01; geometry only, no UV/rig transfer'}
sub=unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
for name in ('MHC_Base_Female','MHC_Base_Male'):
    row={'character':name,'status':'starting'};report['characters'].append(row)
    try:
        folder='/Game/ReferenceGeometry/'+name;asset=folder+'/'+name+'_FullBody'
        character=None
        if not unreal.EditorAssetLibrary.does_asset_exist(asset):
            character=unreal.load_asset('/Game/ReferenceImports/'+name)
            assert sub.try_add_object_to_edit(character)
            params=unreal.MetaHumanGeometryExportParams();params.project_path=folder
            params.head_skeletal_mesh=False;params.body_skeletal_mesh=False;params.full_body_skeletal_mesh=True
            unreal.MetaHumanCharacterExportBlueprintLibrary.export_geometry(character,params)
            unreal.EditorAssetLibrary.save_directory(folder,only_if_is_dirty=True,recursive=True)
        row['asset']=asset;row['status']='geometry_generated'
        (out/'metahuman-cpu-export-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        mesh=unreal.load_asset(asset);assert isinstance(mesh,unreal.SkeletalMesh)
        dynamic=unreal.DynamicMesh();lod=unreal.GeometryScriptMeshReadLOD()
        lod.lod_type=unreal.GeometryScriptLODType.SOURCE_MODEL;lod.lod_index=0
        copied=unreal.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,dynamic,unreal.GeometryScriptCopyMeshFromAssetOptions(),lod)
        row['copy_outcome']=str(copied[-1]);assert 'SUCCESS' in str(copied[-1]).upper(),copied
        positions=unreal.GeometryScript_MeshQueries.get_all_vertex_positions(dynamic,False)
        triangles=unreal.GeometryScript_MeshQueries.get_all_triangle_indices(dynamic,False)
        vectors=unreal.GeometryScript_List.convert_vector_list_to_array(positions[1])
        indices=unreal.GeometryScript_List.convert_triangle_list_to_array(triangles[1])
        faces=[(t.x,t.y,t.z) for t in indices if min(t.x,t.y,t.z)>=0]
        used=sorted({i for face in faces for i in face});mapping={old:new+1 for new,old in enumerate(used)}
        path=dest/(name+'_FullBody.obj')
        with path.open('w',encoding='utf-8') as f:
            f.write('# Local MetaHuman reference study; metres; Blender Z-up\n')
            for i in used:
                v=vectors[i];f.write(f'v {v.y*.01:.9f} {-v.x*.01:.9f} {v.z*.01:.9f}\n')
            for a,b,c in faces:f.write(f'f {mapping[a]} {mapping[b]} {mapping[c]}\n')
        row.update(status='exported',file=str(path),vertices=len(used),triangles=len(faces),bytes=path.stat().st_size)
        if character:sub.remove_object_to_edit(character)
    except Exception:
        row['status']='error';row['traceback']=traceback.format_exc();unreal.log_error(row['traceback'])
    (out/'metahuman-cpu-export-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    unreal.log('HUMAN_REFERENCE_CPU_EXPORT '+name+' '+row['status'])
