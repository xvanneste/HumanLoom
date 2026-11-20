"""Import supplied editable characters into this isolated study project only."""
from pathlib import Path
import json,traceback
import unreal

project=Path(unreal.Paths.project_dir()).resolve()
assert project.name=='HumanReferenceStudy',project
workspace=project.parents[1]
out=workspace/'validation/unreal-17';out.mkdir(parents=True,exist_ok=True)
report={'project':str(project),'engine':unreal.SystemLibrary.get_engine_version(),'status':'starting'}
try:
    source=next(Path('G:/_dev/BlenderDev').glob('Ultimate*/metahuman/UE_5.6/*.mhpkg'))
    task=unreal.AssetImportTask()
    task.set_editor_property('filename',str(source))
    task.set_editor_property('destination_path','/Game/ReferenceImports')
    task.set_editor_property('automated',True)
    task.set_editor_property('replace_existing',False)
    task.set_editor_property('save',True)
    task.set_editor_property('factory',unreal.MetaHumanPackageFactory())
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    report['import_task_paths']=list(task.get_editor_property('imported_object_paths'))
    assets=unreal.EditorAssetLibrary.list_assets('/Game/',recursive=True,include_folder=False)
    report['assets']=list(assets);characters=[]
    for path in assets:
        if '/MHC_Base_' in path:
            obj=unreal.load_asset(path)
            if isinstance(obj,unreal.MetaHumanCharacter):
                characters.append({'path':path,'class':obj.get_class().get_name(),
                                   'methods':[n for n in dir(obj) if any(s in n for s in ('mesh','export','body','face','dna'))]})
    report['characters']=characters
    sub=unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    report['subsystem_methods']={name:str(getattr(sub,name).__doc__) for name in dir(sub)
                                 if not name.startswith('_') and any(s in name for s in ('export','mesh','edit','preview','dna','build','body'))}
    report['export_classes']=[name for name in dir(unreal) if 'MetaHuman' in name and any(s in name for s in ('Export','Editor','Mesh','DNA'))]
    unreal.EditorAssetLibrary.save_directory('/Game/ReferenceImports',only_if_is_dirty=True,recursive=True)
    report['status']='imported' if len(characters)==2 else 'inspect_import_result'
except Exception:
    report['status']='error';report['traceback']=traceback.format_exc();unreal.log_error(report['traceback'])
(out/'metahuman-import-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
unreal.log('HUMAN_REFERENCE_IMPORT_STATUS '+report['status'])
