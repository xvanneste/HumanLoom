"""Export neutral geometry from the imported MetaHuman study copies."""
from pathlib import Path
import json,traceback
import unreal

project=Path(unreal.Paths.project_dir()).resolve();assert project.name=='HumanReferenceStudy'
if '-nullrhi' in unreal.SystemLibrary.get_command_line().lower():
    raise RuntimeError('FBX exporter requires a rendered editor. Use export_reference_cpu.py for this geometry study under NullRHI.')
workspace=project.parents[1];out=workspace/'validation/unreal-17';dest=out/'exports';dest.mkdir(parents=True,exist_ok=True)
report={'engine':unreal.SystemLibrary.get_engine_version(),'characters':[],'scope':'Local neutral geometry study; no auto-rig service or texture-source download requested'}
sub=unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
for name in ('MHC_Base_Female','MHC_Base_Male'):
    row={'character':name,'status':'starting'};report['characters'].append(row)
    try:
        character=unreal.load_asset('/Game/ReferenceImports/'+name)
        assert isinstance(character,unreal.MetaHumanCharacter)
        row['opened_for_edit']=bool(sub.try_add_object_to_edit(character))
        assert row['opened_for_edit'],'Could not initialize character geometry'
        params=unreal.MetaHumanGeometryExportParams()
        params.project_path='/Game/ReferenceGeometry/'+name
        params.head_skeletal_mesh=False;params.body_skeletal_mesh=False;params.full_body_skeletal_mesh=True
        params.overwrite_existing_assets=False
        unreal.MetaHumanCharacterExportBlueprintLibrary.export_geometry(character,params)
        paths=unreal.EditorAssetLibrary.list_assets(params.project_path,recursive=True,include_folder=False)
        row['generated_assets']=list(paths);exports=[]
        unreal.EditorAssetLibrary.save_directory(params.project_path,only_if_is_dirty=True,recursive=True)
        row['status']='geometry_generated'
        (out/'metahuman-export-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        for path in paths:
            mesh=unreal.load_asset(path)
            if not isinstance(mesh,unreal.SkeletalMesh):continue
            target=dest/(mesh.get_name()+'.fbx')
            task=unreal.AssetExportTask();task.object=mesh;task.filename=str(target)
            task.automated=True;task.prompt=False;task.replace_identical=True
            task.exporter=unreal.SkeletalMeshExporterFBX();task.options=unreal.FbxExportOption()
            # Geometry study does not require material baking, which creates a
            # render mesh component and asserts when Unreal runs with NullRHI.
            task.options.bake_material_inputs=unreal.FbxMaterialBakeMode.DISABLED
            task.options.level_of_detail=False
            task.options.export_morph_targets=False
            ok=unreal.Exporter.run_asset_export_task(task)
            exports.append({'asset':path,'file':str(target),'success':bool(ok),
                            'bytes':target.stat().st_size if target.exists() else 0,
                            'errors':list(task.errors)})
        row['exports']=exports
        row['status']='exported' if exports and all(e['success'] and e['bytes']>0 for e in exports) else 'inspect_export_result'
        unreal.EditorAssetLibrary.save_directory(params.project_path,only_if_is_dirty=True,recursive=True)
        sub.remove_object_to_edit(character)
    except Exception:
        row['status']='error';row['traceback']=traceback.format_exc();unreal.log_error(row['traceback'])
    (out/'metahuman-export-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    unreal.log('HUMAN_REFERENCE_EXPORT_STATUS '+name+' '+row['status'])
