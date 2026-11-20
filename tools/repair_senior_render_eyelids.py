"""Local reversible female senior repair, checked on subdivision two."""
import json
from pathlib import Path
import sys
import bpy
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from validate_age_dimensions import surface
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'extension'))
import geometry_quality as qa


def main():
    asset,output=[Path(p).resolve() for p in sys.argv[sys.argv.index('--')+1:]]
    with bpy.data.libraries.load(str(asset),link=False) as (_,target):target.collections=['Realistic Human Base']
    col=target.collections[0];bpy.context.scene.collection.children.link(col)
    body=next(o for o in col.objects if o.get('human_modeling_body'));keys=body.data.shape_keys
    keys.key_blocks['Morphologie'].value=0.;keys['human_modeling_age']=3.;keys['hm_skin_relief']=-1.
    preview=body.modifiers.new('QA surface','SUBSURF');preview.levels=2
    body.modifiers.move(len(body.modifiers)-1,0)
    keys.update_tag();bpy.context.view_layer.update()
    points,faces=surface(body)
    initial=qa.intersections(points,faces,triangle_budget=400000)
    pairs=initial['sample_triangle_pairs']
    if not pairs:raise ValueError('No collisions to repair')
    centers=np.array([points[faces[pair].reshape(-1)].mean(axis=0) for pair in pairs])
    if np.any(centers[:,2]<1.48):raise ValueError('Unexpected collision region')
    for modifier in body.modifiers:modifier.show_viewport=False
    bpy.context.view_layer.update();rest,_=surface(body)
    for modifier in body.modifiers:modifier.show_viewport=True
    distances=np.linalg.norm(rest[:,None,:]-centers[None,:,:],axis=2).min(axis=1)
    mask=np.exp(-(distances/.004)**2);mask[distances>.009]=0.
    edges=np.array([e.vertices[:] for e in body.data.edges])
    degree=np.bincount(edges.reshape(-1),minlength=len(rest)).clip(min=1)
    basis=np.array([v.co[:] for v in keys.key_blocks[0].data])
    repair=body.shape_key_add(name='Age · Senior · Surface · Raccord interne')
    repair.value=1.
    candidate=rest.copy();steps=[]
    for iteration in range(1,31):
        neighbors=np.zeros_like(rest)
        np.add.at(neighbors,edges[:,0],candidate[edges[:,1]])
        np.add.at(neighbors,edges[:,1],candidate[edges[:,0]])
        candidate+=(neighbors/degree[:,None]-candidate)*(.28*mask[:,None])
        delta=candidate-rest
        lengths=np.linalg.norm(delta,axis=1)
        delta*=np.minimum(1.,.0006/np.maximum(lengths,1e-12))[:,None]
        candidate=rest+delta
        repair.data.foreach_set('co',(basis+delta).reshape(-1))
        keys.update_tag();bpy.context.view_layer.update()
        points,faces=surface(body)
        result=qa.intersections(points,faces,triangle_budget=400000)
        row={'iteration':iteration,'crossings':result['crossing_triangle_pairs'],'max_displacement_m':float(np.linalg.norm(delta,axis=1).max())}
        steps.append(row);print('SENIOR_REPAIR',row,flush=True)
        if not row['crossings']:break
    assert not steps[-1]['crossings']
    driver=repair.driver_add('value').driver;driver.type='SCRIPTED'
    for name,path in (('stage','["human_modeling_age"]'),('morph','key_blocks["Morphologie"].value')):
        variable=driver.variables.new();variable.name=name;variable.type='SINGLE_PROP'
        variable.targets[0].id_type='KEY';variable.targets[0].id=keys;variable.targets[0].data_path=path
    driver.expression='max(0,stage-2)*(1-morph)'
    body.modifiers.remove(preview)
    keys['human_modeling_age']=2.;keys['hm_skin_relief']=0.;keys.key_blocks['Morphologie'].value=1.
    bpy.data.libraries.write(str(output),{col,body.data,*(o.data for o in body.children)},fake_user=True,compress=True)
    output.with_suffix('.repair.json').write_text(json.dumps({'initial_crossings':initial['crossing_triangle_pairs'],'steps':steps,
        'scope':'Female senior inner orbital surface, subdivision two; original cage coordinates preserved in a separate key'},indent=2),encoding='utf-8')


if __name__=='__main__':main()
