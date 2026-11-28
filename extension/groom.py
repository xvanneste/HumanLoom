"""HumanLoom grooming: native Hair Curves, UV attachment and 5.2 dynamics.

No particles, handlers, external packages or mutation of body shape keys.
One editable groom per region and per character. Sculpted guides are preserved
until the explicit reconstruction operator is invoked.
"""
from pathlib import Path
import json,math
import bpy
import numpy as np
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
from bpy_extras.io_utils import ImportHelper,ExportHelper
from .groom_fibers import fiber
from . import human

REGIONS=(('SCALP','Cheveux',''),('BROWS','Sourcils',''),('BEARD','Barbe',''),('MOUSTACHE','Moustache',''),('CHEST','Torse',''),('ABDOMEN','Abdomen',''),('BACK','Dos',''),('ARMS','Bras',''),('LEGS','Jambes',''),('AXILLA','Aisselles',''),('PUBIC','Pubis',''))
LABELS={i:label for i,label,_ in REGIONS}
DEFAULTS={
 'SCALP':(.055,850,1800000.,.000045), 'BROWS':(.009,240,4500000.,.000035),
 'BEARD':(.025,500,950000.,.000050), 'MOUSTACHE':(.014,240,2000000.,.000045),
 'CHEST':(.014,420,45000.,.000025), 'ABDOMEN':(.013,280,40000.,.000025),
 'BACK':(.012,350,25000.,.000022), 'ARMS':(.009,550,35000.,.000020),
 'LEGS':(.013,800,45000.,.000025), 'AXILLA':(.025,160,250000.,.000035),
 'PUBIC':(.025,220,220000.,.000035),
}
FORMAT='humanloom.groom';SCHEMA=1
QUALITY_PRESETS=(('CUSTOM','Personnalisé',''),('LIGHT','Léger · 10 %',''),('BALANCED','Équilibré · 30 %',''),('FULL','Complet · 100 %',''))
QUALITY_AMOUNTS={'LIGHT':.10,'BALANCED':.30,'FULL':1.}
FLOAT32_TOLERANCE=1e-6
# Canonical stack: guides are simulated first only in XPBD mode; interpolation, profile and material always follow.
STACK_ANIMATION=('HumanLoom · densité','HumanLoom · suivi 5.2','HumanLoom · profil','HumanLoom · matériau')
STACK_XPBD=('HumanLoom · suivi 5.2','HumanLoom · densité','HumanLoom · profil','HumanLoom · matériau')


def local_tree(tree,memo=None):
    """Embed native node dependencies; a saved character must be portable."""
    memo={} if memo is None else memo
    key=tree.as_pointer()
    if key in memo:return memo[key]
    result=tree.copy() if tree.library else tree
    memo[key]=result
    for node in result.nodes:
        if node.type=='GROUP' and node.node_tree:node.node_tree=local_tree(node.node_tree,memo)
    return result


def body_from(context):
    return human.body_of(context.active_object)


def find(body,region):
    return next((o for o in body.children if o.type=='CURVES' and o.get('hl_groom_region')==region),None)


def set_input(mod,name,value,kind=None):
    items=[s for s in mod.node_group.interface.items_tree if s.item_type=='SOCKET' and s.in_out=='INPUT' and s.name==name and (kind is None or s.socket_type==kind)]
    if len(items)!=1:raise ValueError('Entrée native absente ou ambiguë : '+name)
    getattr(mod.properties.inputs,items[0].identifier).value=value


def input_value(mod,name):
    socket=next(s for s in mod.node_group.interface.items_tree if s.item_type=='SOCKET' and s.in_out=='INPUT' and s.name==name)
    return getattr(mod.properties.inputs,socket.identifier).value


def mask_area(hair):
    """Effective area of the density mask as painted now (area x mask weight), not as it was at build time."""
    stored=hair.get('hl_mask_area_m2',0.)
    body=hair.parent
    group=body.vertex_groups.get('hl_density_'+hair['hl_groom_region'].lower()) if body is not None else None
    if group is None:return stored
    mesh=body.data;mesh.calc_loop_triangles()
    w=np.zeros(len(mesh.vertices))
    for v in mesh.vertices:
        for g in v.groups:
            if g.group==group.index:w[v.index]=g.weight
    p=np.array([v.co[:] for v in mesh.vertices]);tri=np.array([t.vertices[:] for t in mesh.loop_triangles]);corner=p[tri]
    areas=np.linalg.norm(np.cross(corner[:,1]-corner[:,0],corner[:,2]-corner[:,0]),axis=1)/2
    return float(np.sum(areas*w[tri].mean(axis=1)))


def check_viewport_budget(hair,fraction):
    if not math.isfinite(fraction) or not 0<=fraction<=1:raise ValueError('La quantité d’aperçu doit être comprise entre 0 et 100 %.')
    density=input_value(hair.modifiers['HumanLoom · densité'],'Density')
    points=max(len(c.points) for c in hair.data.curves)
    estimated=(mask_area(hair)*density+len(hair.data.curves))*points*fraction
    if estimated>12000000:raise ValueError('Cette quantité d’aperçu dépasse le budget pour cette zone. Choisissez un pourcentage inférieur.')


def viewport_quality(hair,fraction):
    """Change display interpolation only; keep guides, render and XPBD untouched."""
    check_viewport_budget(hair,fraction)
    set_input(hair.modifiers['HumanLoom · densité'],'Viewport Amount',fraction)
    hair.hl_groom.viewport=fraction
    hair.update_tag()


def native(name):
    for group in bpy.data.node_groups:
        if group.get('hl_native_source')==name:return group
    path=Path(bpy.utils.system_resource('DATAFILES'))/'assets/nodes/procedural_hair_node_assets.blend'
    with bpy.data.libraries.load(str(path),link=False) as (src,dst):
        if name not in src.node_groups:raise ValueError('Groupe Blender 5.2 absent : '+name)
        dst.node_groups=[name]
    group=local_tree(dst.node_groups[0]);group['hl_native_source']=name
    return group


def attribute(data,name,kind,domain,values,field='value'):
    a=data.attributes.get(name) or data.attributes.new(name,kind,domain)
    a.data.foreach_set(field,np.asarray(values).ravel());return a


def weights(points,region):
    """Soft original anatomical masks on the immutable base topology."""
    x,y,z=points.T;ax=abs(x);top=points[:,2].max();h=top-points[:,2].min();d=top-z
    def band(v,center,half):return np.clip(1-abs(v-center)/half,0,1)
    def window(v,lo,hi,edge):return np.clip((v-lo)/edge,0,1)*np.clip((hi-v)/edge,0,1)
    front=np.clip((-y-.005)/.035,0,1)
    if region=='SCALP':
        frontness=np.clip((-y-.015)/.13,0,1)
        return np.clip((z-(top-.145+.10*frontness))/.012,0,1)*(1-((ax>.071)&(d>.095)))
    if region=='BROWS':
        arch=.089+.010*np.clip((ax-.025)/.035,0,1)
        return band(d,arch,.008)*window(ax,.014,.065,.008)*front
    if region=='MOUSTACHE':return band(d,.164,.010)*window(ax,.003,.038,.009)*front
    if region=='BEARD':
        chin=window(d,.183,.235,.013)*window(ax,0,.065,.009)
        sides=window(d,.13,.211,.016)*window(ax,.035,.075,.009)
        return np.maximum(chin,sides)*np.clip((-y+.025)/.035,0,1)
    if region=='CHEST':return window(z/h,.665,.79,.035)*window(ax,0,.145,.03)*front
    if region=='ABDOMEN':return window(z/h,.53,.665,.035)*window(ax,0,.13,.035)*front
    if region=='BACK':return window(z/h,.56,.81,.045)*window(ax,0,.16,.03)*np.clip((y-.005)/.035,0,1)
    if region=='ARMS':return window(ax,.18,.365,.04)*window(z/h,.43,.78,.045)
    if region=='LEGS':return window(z/h,.07,.47,.045)*window(ax,.025,.18,.025)
    if region=='AXILLA':return band(ax,.14,.04)*band(z/h,.75,.035)*np.clip((.005-y)/.03,0,1)
    if region=='PUBIC':return band(z/h,.487,.034)*window(ax,0,.10,.035)*front
    raise ValueError('Zone de pilosité inconnue.')


def sample(body,region,count,seed):
    mesh=body.data
    if not mesh.uv_layers.active:raise ValueError('Une UV active est nécessaire pour l’attache.')
    mesh.calc_loop_triangles()
    p=np.array([v.co[:] for v in mesh.vertices]);tri=np.array([t.vertices[:] for t in mesh.loop_triangles])
    corner=p[tri];w=weights(p,region)
    painted=body.vertex_groups.get('hl_density_'+region.lower())
    if painted:
        w=np.array([next((g.weight for g in v.groups if g.group==painted.index),0.) for v in mesh.vertices])
    mask=w[tri].mean(axis=1)
    areas=np.linalg.norm(np.cross(corner[:,1]-corner[:,0],corner[:,2]-corner[:,0]),axis=1)/2
    # Reject triangles touching a zero-mask vertex: keep the eye and lip margins clear.
    chance=areas*mask*(w[tri].min(axis=1)>.025)
    if chance.sum()<=0:raise ValueError('Aucune surface valide pour cette zone sur cette base.')
    rng=np.random.default_rng(seed);ids=rng.choice(len(tri),count,p=chance/chance.sum())
    raw=rng.random((count,2));raw[raw.sum(axis=1)>1]=1-raw[raw.sum(axis=1)>1]
    bary=np.column_stack((1-raw.sum(axis=1),raw));root=np.einsum('ni,nij->nj',bary,corner[ids])
    normals=np.cross(corner[ids,1]-corner[ids,0],corner[ids,2]-corner[ids,0]);normals/=np.maximum(np.linalg.norm(normals,axis=1)[:,None],1e-12)
    uv=mesh.uv_layers.active.data
    uvc=np.array([[uv[loop].uv[:] for loop in mesh.loop_triangles[int(i)].loops] for i in ids])
    return root,normals,np.einsum('ni,nij->nj',bary,uvc),ids,bary,w,float(np.sum(areas*mask))


def points_per_strand(region,cfg):
    """Borne supérieure du nombre de points d'une mèche telle que `make_positions` la produit (GRM-011) : la résolution de l'analyse (fibre) ET celle du coiffage le long du crâne (un point tous les 4 mm) ; la longueur d'une mèche ne dépasse jamais `length`."""
    count=len(fiber(cfg['length'],cfg['nature']))
    if region=='SCALP' and cfg['style']!='UPRIGHT' and cfg['nature']<.35:count=max(count,int(cfg['length']/.004)+2)
    return count


def make_positions(body,root,normals,region,cfg):
    rng=np.random.default_rng(cfg['seed']+17);arrays=[]
    bvh=BVHTree.FromPolygons([v.co[:] for v in body.data.vertices],[p.vertices[:] for p in body.data.polygons]) if region=='SCALP' else None
    for r,n in zip(root,normals):
        length=cfg['length']*rng.uniform(1-cfg['variation'],1.)
        local=fiber(length,cfg['nature'],rng.uniform(0,2*math.pi))
        if region=='SCALP':
            if cfg['style']=='PARTED':flow=np.array([np.sign(r[0]-.012)*.7,1.,-.25])
            elif cfg['style']=='UPRIGHT':flow=n.copy()
            else:flow=np.array([.25,1.,-.35])
        elif region=='BROWS':flow=np.array([np.sign(r[0]),0.,-.1])
        elif region=='MOUSTACHE':flow=np.array([np.sign(r[0])*.7,0.,-.7])
        else:flow=np.array([0.,0.,-1.])
        tangent=flow-n*np.dot(flow,n);tangent/=max(np.linalg.norm(tangent),1e-9)
        axis=n*.8+tangent*.6 if region=='SCALP' else n*.35+tangent*.94
        if region=='SCALP' and cfg['style']=='UPRIGHT':axis=n.copy()
        axis/=max(np.linalg.norm(axis),1e-9)
        side=np.cross(axis,np.array([0.,1.,0.]));side/=max(np.linalg.norm(side),1e-9)
        other=np.cross(axis,side)
        frame=np.column_stack((side,other,axis))
        points=r+local@frame.T
        t=np.linspace(0,1,len(points))
        if region=='SCALP' and cfg['style']!='UPRIGHT' and cfg['nature']<.35:
            # Walk straight/wavy styles along the skull, then let long tips fall.
            # A 30 cm strand must not become a 30 cm outward spike.
            intrinsic=points.copy()
            steps=max(len(local),int(length/.004)+2)
            samples=np.linspace(0,length,steps);path=[r.copy()];p=r.copy()
            for a,b in zip(samples[:-1],samples[1:]):
                hit,normal,_,distance=bvh.find_nearest(Vector(p))
                normal=np.array(normal)
                drop=np.clip((a-.025)/.07,0,1) if length>.08 else 0.
                desired=flow*(1-drop*.65)+np.array([0.,0.,-1.])*drop
                if distance<.003:
                    desired-=normal*min(np.dot(desired,normal),0.)
                    desired+=normal*.12
                desired/=max(np.linalg.norm(desired),1e-9);p=p+desired*(b-a)
                hit,normal,_,distance=bvh.find_nearest(Vector(p))
                if (Vector(p)-hit).dot(normal)<.001:p=np.array(hit+normal*.001)
                path.append(p.copy())
            points=np.asarray(path);t=np.linspace(0,1,len(points))
            if cfg['nature']>0:
                points+=side[None,:]*(np.sin(t*math.pi*6)*t*cfg['nature']*.006)[:,None]
            # Blend the coiffage regimes continuously; no jump at a curl label.
            blend=float(np.clip((cfg['nature']-.20)/.15,0,1))
            blend=blend*blend*(3-2*blend)
            if blend:
                parameter=np.linspace(0,1,len(intrinsic))
                resampled=np.column_stack([np.interp(t,parameter,intrinsic[:,axis]) for axis in range(3)])
                points=points*(1-blend)+resampled*blend
        # Small reproducible irregularity, distinct from the rest curvature.
        points+=side[None,:]*(np.sin(t*math.pi*4+rng.uniform(0,6))*t*cfg['frizz']*min(length,.08)*.08)[:,None]
        points[0]=r
        # Preserve the requested contour length after the coiffage displacement.
        contour=np.linalg.norm(np.diff(points,axis=0),axis=1).sum()
        if contour>1e-9:points=r+(points-r)*(length/contour)
        arrays.append(points)
    return arrays


FIELDS=('length','nature','variation','frizz','style','seed','guides','density','viewport','radius','color','roughness','grey','visible','physics','substeps','iterations','bendiness','root_bendiness','collisions')


def state(settings):
    return {k:list(getattr(settings,k)) if k=='color' else getattr(settings,k) for k in FIELDS}


def validate(cfg):
    if not isinstance(cfg,dict) or set(cfg)!=set(FIELDS):raise ValueError('Réglages de groom incomplets ou inconnus.')
    bounds={'length':(.001,.45),'nature':(0,1),'variation':(0,.8),'frizz':(0,1),'seed':(0,2147483647),'guides':(20,3000),'density':(0,8000000),'viewport':(0,1),'radius':(.000005,.00015),'roughness':(.05,1),'grey':(0,1),'substeps':(1,32),'iterations':(16,32768),'bendiness':(0,1),'root_bendiness':(0,1)}
    for key,(lo,hi) in bounds.items():
        v=cfg[key]
        # Blender stores floats in single precision: a slider bound read back (0.8, 5e-6, 1.5e-4) differs from the double bound by up to ~6e-8 relative. Integers stay strict.
        slack=FLOAT32_TOLERANCE if type(v) is float else 0
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not lo-abs(lo)*slack<=v<=hi+abs(hi)*slack:raise ValueError('Valeur invalide : '+key)
    for key in ('seed','guides','substeps','iterations'):
        if type(cfg[key]) is not int:raise ValueError('Entier attendu : '+key)
    if cfg['style'] not in ('SWEPT','PARTED','UPRIGHT') or cfg['physics'] not in ('ANIMATION','XPBD'):raise ValueError('Mode de groom invalide.')
    for key in ('visible','collisions'):
        if type(cfg[key]) is not bool:raise ValueError('Booléen attendu : '+key)
    if not isinstance(cfg['color'],(list,tuple)) or len(cfg['color'])!=3 or not all(type(v) in (int,float) and math.isfinite(v) and 0<=v<=1 for v in cfg['color']):raise ValueError('Couleur invalide.')
    return cfg


SAFE_SUBSTEPS = 19  # manuel Blender 5.2 (Hair Dynamics) : rester sous 20 sous-pas à cause des erreurs d'arrondi liées à l'inverse du carré du pas
VERIFIED_XPBD_LENGTH = .06  # profil historique vérifié (tools/hair_physics22.py : mèches de 6 cm) ; au-delà, aucun résultat de convergence n'est publié


def domain_warnings(cfg):
    """Avertissements de domaine (GRM-012) : l'interface accepte plus large que ce qui est justifié ; ils sont affichés, jamais bloquants."""
    warnings=[]
    if cfg['physics']=='XPBD':
        warnings.append('Simulation XPBD expérimentale de Blender : résultats non validés, aucun résidu natif exposé.')
        if cfg['substeps']>SAFE_SUBSTEPS:warnings.append(f'Sous-pas {cfg["substeps"]} : le manuel 5.2 conseille moins de 20 (erreurs d’arrondi) ; augmenter ne garantit pas la convergence.')
        if cfg['length']>VERIFIED_XPBD_LENGTH:warnings.append(f'Longueur {cfg["length"]*100:.0f} cm : hors du domaine vérifié (6 cm) pour la simulation.')
    return warnings


def render_warnings(scene):
    """Avertissements de rendu (GRM-019) : le shader Principled Hair BSDF n'existe que sous Cycles (manuel 5.2 : non pris en charge par EEVEE). Ne change jamais le moteur de la scène."""
    engine=scene.render.engine
    if engine=='CYCLES':return []
    return ['Le matériau des fibres (Principled Hair BSDF) demande le moteur Cycles : avec le moteur actuel les fibres s’affichent sans ce shader. Le moteur n’est pas modifié.']


def add_interpolation(hair,region):
    group=bpy.data.node_groups.new('HumanLoom · densité · '+LABELS[region],'GeometryNodeTree');group['hl_owned']=True
    group.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry')
    group.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
    for name,kind in (('Density','NodeSocketFloat'),('Viewport Amount','NodeSocketFloat'),('Seed','NodeSocketInt')):group.interface.new_socket(name=name,in_out='INPUT',socket_type=kind)
    src=group.nodes.new('NodeGroupInput');dst=group.nodes.new('NodeGroupOutput')
    inter=group.nodes.new('GeometryNodeGroup');inter.node_tree=native('Interpolate Hair Curves')
    inter.inputs['Resting Surface'].default_value=True;inter.inputs['Distance to Guides'].default_value=.08
    attr=group.nodes.new('GeometryNodeInputNamedAttribute');attr.data_type='FLOAT';attr.inputs['Name'].default_value='hl_density_'+region.lower()
    group.links.new(src.outputs['Geometry'],inter.inputs['Geometry']);group.links.new(attr.outputs['Attribute'],inter.inputs['Density Mask'])
    for name in ('Density','Viewport Amount','Seed'):group.links.new(src.outputs[name],inter.inputs[name])
    group.links.new(inter.outputs['Geometry'],dst.inputs['Geometry'])
    src.location=(-500,100);attr.location=(-500,-150);inter.location=(-150,100);dst.location=(200,100)
    mod=hair.modifiers.new('HumanLoom · densité','NODES');mod.node_group=group;hair.modifiers.move(len(hair.modifiers)-1,0)
    return mod


def make_material(hair,cfg):
    mat=bpy.data.materials.new('HumanLoom · '+LABELS[hair['hl_groom_region']]);mat['hl_owned']=True;mat.use_nodes=True
    nodes=mat.node_tree.nodes;nodes.clear()
    shader=nodes.new('ShaderNodeBsdfHairPrincipled');shader.parametrization='COLOR'
    info=nodes.new('ShaderNodeHairInfo');mix=nodes.new('ShaderNodeMixRGB');mix.blend_type='MIX'
    step=nodes.new('ShaderNodeMath');step.operation='LESS_THAN';step.inputs[1].default_value=cfg['grey']
    mat.node_tree.links.new(info.outputs['Random'],step.inputs[0]);mat.node_tree.links.new(step.outputs[0],mix.inputs[0])
    mix.inputs[1].default_value=(*cfg['color'],1);mix.inputs[2].default_value=(.55,.57,.6,1)
    mat.node_tree.links.new(mix.outputs[0],shader.inputs['Color']);shader.inputs['Roughness'].default_value=cfg['roughness']
    output=nodes.new('ShaderNodeOutputMaterial');mat.node_tree.links.new(shader.outputs[0],output.inputs['Surface'])
    mat.diffuse_color=(*cfg['color'],1);hair.data.materials.append(mat)
    group=bpy.data.node_groups.new('HumanLoom · matériau','GeometryNodeTree');group['hl_owned']=True
    group.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry');group.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
    src=group.nodes.new('NodeGroupInput');dst=group.nodes.new('NodeGroupOutput');assign=group.nodes.new('GeometryNodeSetMaterial');assign.inputs['Material'].default_value=mat
    group.links.new(src.outputs[0],assign.inputs['Geometry']);group.links.new(assign.outputs[0],dst.inputs[0])
    mod=hair.modifiers.new('HumanLoom · matériau','NODES');mod.node_group=group


def order_modifiers(hair,physics):
    """Impose the canonical stack with explicit indices.

    The native hair modifier added by curves_empty_hair_add is pinned to last (use_pin_to_last),
    which turns every modifiers.move into a silent no-op and leaves it at the end of the Cheveux zone.
    """
    for mod in hair.modifiers:mod.use_pin_to_last=False
    for index,name in enumerate(STACK_XPBD if physics=='XPBD' else STACK_ANIMATION):
        current=list(hair.modifiers).index(hair.modifiers[name])
        if current!=index:hair.modifiers.move(current,index)


def configure(hair,cfg):
    density=hair.modifiers['HumanLoom · densité']
    for name,value in (('Density',cfg['density']),('Viewport Amount',cfg['viewport']),('Seed',cfg['seed'])):set_input(density,name,value)
    dynamics=hair.modifiers['HumanLoom · suivi 5.2']
    set_input(dynamics,'Mode','Animation')
    order_modifiers(hair,cfg['physics'])
    inter=next(n for n in density.node_group.nodes if n.type=='GROUP');inter.inputs['Resting Surface'].default_value=True
    if cfg['physics']=='XPBD':
        # Run the native solver on guides, then interpolate on the deformed surface (order set by order_modifiers).
        inter=next(n for n in density.node_group.nodes if n.type=='GROUP');inter.inputs['Resting Surface'].default_value=False
        set_input(dynamics,'Mode','Physics (Experimental)')
        for name,value,kind in [('Substeps',cfg['substeps'],None),('Constraint Steps',cfg['iterations'],None),('Bendiness',cfg['bendiness'],None),('Root Bendiness',cfg['root_bendiness'],None),('Stretchiness',0.,None),('Randomness',False,None),('Gravity',True,'NodeSocketBool'),('Surface Collision',cfg['collisions'],None)]:set_input(dynamics,name,value,kind)
    hair.hide_render=not cfg['visible'];hair.hide_set(not cfg['visible']);hair.update_tag()


def appearance(hair,cfg):
    """Apply non-geometric settings without losing a sculpted strand."""
    validate(cfg)
    points=max(len(c.points) for c in hair.data.curves)
    budget=(mask_area(hair)*cfg['density']+len(hair.data.curves))*points
    if budget>40000000 or budget*cfg['viewport']>12000000:raise ValueError('Réduisez la densité ou la quantité en aperçu pour ce niveau de détail.')
    configure(hair,cfg)
    set_input(hair.modifiers['HumanLoom · profil'],'Radius',cfg['radius'])
    mat=hair.data.materials[0]
    nodes=mat.node_tree.nodes
    next(n for n in nodes if n.type=='MIX_RGB').inputs[1].default_value=(*cfg['color'],1)
    next(n for n in nodes if n.type=='MATH').inputs[1].default_value=cfg['grey']
    next(n for n in nodes if n.type=='BSDF_HAIR_PRINCIPLED').inputs['Roughness'].default_value=cfg['roughness']
    mat.diffuse_color=(*cfg['color'],1)
    hair.update_tag()


def discard(hair):
    data=hair.data;groups=[m.node_group for m in hair.modifiers if m.type=='NODES' and m.node_group and m.node_group.get('hl_owned')]
    mats=list(data.materials);bpy.data.objects.remove(hair,do_unlink=True)
    if data.users==0:bpy.data.hair_curves.remove(data)
    for group in groups:
        if group.users==0:bpy.data.node_groups.remove(group)
    for mat in mats:
        if mat and mat.get('hl_owned') and mat.users==0:bpy.data.materials.remove(mat)


def build(body,region,cfg):
    validate(cfg)
    if bpy.app.version[:2]!=(5,2):raise ValueError('HumanLoom nécessite Blender 5.2.')
    if not (human.is_native(body) or (human.is_legacy(body) and body.data.get('human_modeling_schema',0)>=9)):raise ValueError('Une base HumanLoom à jour est nécessaire.')
    if not body.is_editable or not body.data.is_editable:raise ValueError('Le personnage doit être éditable.')
    if region not in LABELS:raise ValueError('Zone inconnue.')
    root,normals,uv,ids,bary,mask,area=sample(body,region,cfg['guides'],cfg['seed'])
    estimate=(area*cfg['density']+cfg['guides'])*points_per_strand(region,cfg)
    if estimate>40000000 or estimate*cfg['viewport']>12000000:
        raise ValueError('Cette combinaison dépasse le budget de mèches. Réduisez densité ou quantité en aperçu, puis reconstruisez.')
    positions=make_positions(body,root,normals,region,cfg)
    old=find(body,region);selected=list(bpy.context.selected_objects);active=bpy.context.view_layer.objects.active
    hair=None
    try:
        for obj in selected:obj.select_set(False)
        body.select_set(True);bpy.context.view_layer.objects.active=body
        template=next((h for h in body.children if h.type=='CURVES' and h.get('hl_groom_region')),None)
        if template:
            hair=bpy.data.objects.new('HumanLoom · '+LABELS[region],bpy.data.hair_curves.new('HumanLoom · guides'))
            body.users_collection[0].objects.link(hair)
            dynamic=hair.modifiers.new('HumanLoom · suivi 5.2','NODES');dynamic.node_group=template.modifiers['HumanLoom · suivi 5.2'].node_group
        else:
            if bpy.ops.object.curves_empty_hair_add()!={'FINISHED'}:raise ValueError('Impossible de créer les Hair Curves natives.')
            hair=bpy.context.object;hair.name='HumanLoom · '+LABELS[region]
            for collection in tuple(hair.users_collection):collection.objects.unlink(hair)
            body.users_collection[0].objects.link(hair)
            hair.modifiers[0].node_group=local_tree(hair.modifiers[0].node_group)
            for modifier in body.modifiers:
                if modifier.type=='NODES' and modifier.node_group and modifier.node_group.name.startswith('Capture Rest Geometry'):
                    modifier.node_group=local_tree(modifier.node_group)
        hair['hl_groom_region']=region;hair['hl_groom_schema']=SCHEMA;hair['hl_surface_vertices']=len(body.data.vertices)
        hair['hl_mask_area_m2']=area
        hair.parent=body;hair.matrix_parent_inverse=Matrix.Identity(4);hair.matrix_basis=Matrix.Identity(4)
        data=hair.data;data.surface=body;data.surface_uv_map=body.data.uv_layers.active.name
        data.use_sculpt_collision=True;data.surface_collision_distance=.001
        data.add_curves([len(p) for p in positions]);data.set_types(type='POLY')
        attribute(data,'position','FLOAT_VECTOR','POINT',np.concatenate(positions),'vector')
        radii=np.concatenate([np.linspace(cfg['radius'],cfg['radius']*.12,len(p)) for p in positions])
        attribute(data,'radius','FLOAT','POINT',radii)
        attribute(data,'surface_uv_coordinate','FLOAT2','CURVE',uv,'vector')
        attribute(data,'hl_root_triangle','INT','CURVE',ids)
        attribute(data,'hl_root_barycentric','FLOAT_VECTOR','CURVE',bary,'vector')
        group_name='hl_density_'+region.lower()
        if not body.vertex_groups.get(group_name):
            painted=body.vertex_groups.new(name=group_name)
            for index,amount in enumerate(mask):
                if amount>0:painted.add([index],float(amount),'REPLACE')
        hair.modifiers[0].name='HumanLoom · suivi 5.2'
        add_interpolation(hair,region)
        profile=hair.modifiers.new('HumanLoom · profil','NODES');profile.node_group=native('Set Hair Curve Profile')
        set_input(profile,'Replace Radius',True);set_input(profile,'Radius',cfg['radius'])
        make_material(hair,cfg);configure(hair,cfg)
        for key,value in cfg.items():setattr(hair.hl_groom,key,value)
        hair['hl_built_settings']=json.dumps(cfg,sort_keys=True)
        data.update_tag();hair.update_tag()
    except Exception:
        if hair is not None:discard(hair)
        raise
    finally:
        for obj in tuple(bpy.context.selected_objects):obj.select_set(False)
        for obj in selected:
            if obj.name in bpy.context.view_layer.objects:obj.select_set(True)
        if active and active.name in bpy.context.view_layer.objects:bpy.context.view_layer.objects.active=active
    if old:
        was_active=active==old;was_selected=old in selected
        discard(old)
        if was_selected:hair.select_set(True)
        if was_active:bpy.context.view_layer.objects.active=hair
    return hair


def defaults(region):
    length,count,density,radius=DEFAULTS[region]
    return {'length':length,'guides':count,'density':density,'radius':radius,'nature':.08 if region not in ('PUBIC','AXILLA') else .45,'variation':.25,'frizz':.15,'style':'SWEPT','seed':2026,'viewport':.3,'color':[.035,.012,.006],'roughness':.4,'grey':0.,'visible':True,'physics':'ANIMATION','substeps':8,'iterations':1024,'bendiness':.2,'root_bendiness':.1,'collisions':True}


class HL_GroomSettings(bpy.types.PropertyGroup):
    length:bpy.props.FloatProperty(name='Longueur de contour',default=.055,min=.001,max=.45,unit='LENGTH')
    nature:bpy.props.FloatProperty(name='Lisse → crépu',default=.08,min=0,max=1)
    variation:bpy.props.FloatProperty(name='Variation de longueur',default=.25,min=0,max=.8,subtype='FACTOR')
    frizz:bpy.props.FloatProperty(name='Irrégularité',default=.15,min=0,max=1)
    style:bpy.props.EnumProperty(name='Direction',items=(('SWEPT','Vers l’arrière',''),('PARTED','Avec raie',''),('UPRIGHT','Dressé','')))
    seed:bpy.props.IntProperty(name='Graine',default=2026,min=0,max=2147483647)
    guides:bpy.props.IntProperty(name='Guides éditables',default=850,min=20,max=3000)
    density:bpy.props.FloatProperty(name='Densité au rendu / m²',default=1800000,min=0,max=8000000,description='Densité complète utilisée au rendu ; 1 800 000 / m² = 180 cheveux / cm² avant modulation par le masque')
    viewport:bpy.props.FloatProperty(name='Viewport (% du rendu)',default=.3,min=0,max=1,subtype='FACTOR',description='Fraction de mèches affichées dans le viewport ; aucun effet sur la densité au rendu')
    radius:bpy.props.FloatProperty(name='Rayon à la racine',default=.000045,min=.000005,max=.00015,unit='LENGTH',precision=6)
    color:bpy.props.FloatVectorProperty(name='Couleur',subtype='COLOR',size=3,min=0,max=1,default=(.035,.012,.006))
    roughness:bpy.props.FloatProperty(name='Rugosité',default=.4,min=.05,max=1)
    grey:bpy.props.FloatProperty(name='Cheveux gris',default=0,min=0,max=1,subtype='FACTOR')
    visible:bpy.props.BoolProperty(name='Visible',default=True)
    physics:bpy.props.EnumProperty(name='Dynamique',items=(('ANIMATION','Suivi sans physique','Suit le corps sans simuler la gravité'),('XPBD','XPBD expérimental','Simule les guides avec gravité ; appliquer puis lire la timeline depuis sa première image')))
    substeps:bpy.props.IntProperty(name='Sous-pas',default=8,min=1,max=32,soft_max=19,description='Le manuel 5.2 conseille moins de 20 sous-pas')
    iterations:bpy.props.IntProperty(name='Itérations',default=1024,min=16,max=32768)
    bendiness:bpy.props.FloatProperty(name='Souplesse',default=.2,min=0,max=1)
    root_bendiness:bpy.props.FloatProperty(name='Souplesse des racines',default=.1,min=0,max=1)
    collisions:bpy.props.BoolProperty(name='Collision avec le corps',default=True)


class HL_OT_groom_build(bpy.types.Operator):
    bl_idname='humanloom.groom_build';bl_label='Ajouter cette pilosité';bl_options={'REGISTER','UNDO'}
    bl_description='Crée la zone sélectionnée ; reconstruire remplace ses guides sculptés (annulable)'
    @classmethod
    def poll(cls,context):return context.mode=='OBJECT' and body_from(context) is not None
    def execute(self,context):
        body=body_from(context);region=body.hl_groom_region;old=find(body,region)
        try:build(body,region,state(old.hl_groom) if old else defaults(region))
        except (ValueError,RuntimeError,OSError,KeyError) as error:self.report({'ERROR'},str(error));return {'CANCELLED'}
        self.report({'INFO'},LABELS[region]+' : guides créés.');return {'FINISHED'}


class HL_OT_groom_select(bpy.types.Operator):
    bl_idname='humanloom.groom_select';bl_label='Sélectionner les guides';bl_options={'REGISTER','UNDO'}
    @classmethod
    def poll(cls,context):return HL_OT_groom_build.poll(context)
    def execute(self,context):
        body=body_from(context);hair=find(body,body.hl_groom_region)
        if not hair:return {'CANCELLED'}
        for obj in tuple(context.selected_objects):obj.select_set(False)
        hair.hide_set(False);hair.select_set(True);context.view_layer.objects.active=hair
        return {'FINISHED'}


class HL_OT_groom_apply(bpy.types.Operator):
    bl_idname='humanloom.groom_apply';bl_label='Appliquer matière et densité';bl_options={'REGISTER','UNDO'}
    bl_description='Applique densité, diamètre, matériau et dynamique sans reconstruire les guides sculptés'
    @classmethod
    def poll(cls,context):return HL_OT_groom_build.poll(context)
    def execute(self,context):
        body=body_from(context);hair=find(body,body.hl_groom_region)
        if not hair:return {'CANCELLED'}
        try:appearance(hair,state(hair.hl_groom))
        except (ValueError,RuntimeError,KeyError) as error:self.report({'ERROR'},str(error));return {'CANCELLED'}
        return {'FINISHED'}


class HL_OT_groom_density(bpy.types.Operator):
    bl_idname='humanloom.groom_density';bl_label='Densité des cheveux';bl_options={'REGISTER','UNDO'}
    bl_description='Applique une densité de cheveux sans remplacer les guides sculptés ni le niveau d’aperçu'
    preset:bpy.props.EnumProperty(items=(('SPARSE','Clairsemé','70 cheveux/cm²'),('NORMAL','Normal','180 cheveux/cm²'),('DENSE','Dense','250 cheveux/cm²')),default='NORMAL')
    @classmethod
    def poll(cls,context):return HL_OT_groom_build.poll(context) and find(body_from(context),'SCALP') is not None
    def execute(self,context):
        hair=find(body_from(context),'SCALP')
        density={'SPARSE':700000.,'NORMAL':1800000.,'DENSE':2500000.}[self.preset]
        try:
            points=max(len(c.points) for c in hair.data.curves)
            budget=(mask_area(hair)*density+len(hair.data.curves))*points
            fraction=input_value(hair.modifiers['HumanLoom · densité'],'Viewport Amount')
            if budget>40000000 or budget*fraction>12000000:raise ValueError('Réduisez la quantité d’aperçu ou choisissez une densité inférieure.')
            set_input(hair.modifiers['HumanLoom · densité'],'Density',density)
        except (ValueError,RuntimeError,KeyError) as error:self.report({'ERROR'},str(error));return {'CANCELLED'}
        hair.hl_groom.density=density;hair.update_tag()
        return {'FINISHED'}


class HL_OT_groom_quality(bpy.types.Operator):
    bl_idname='humanloom.groom_quality';bl_label='Appliquer la qualité d’aperçu';bl_options={'REGISTER','UNDO'}
    bl_description='Allège le viewport en conservant les guides, la densité au rendu et les réglages de dynamique'
    preset:bpy.props.EnumProperty(name='Qualité',items=QUALITY_PRESETS,default='CUSTOM')
    all_layers:bpy.props.BoolProperty(name='Toutes les zones',default=False)
    @classmethod
    def poll(cls,context):return HL_OT_groom_build.poll(context)
    def execute(self,context):
        body=body_from(context);active=find(body,body.hl_groom_region)
        if active is None:return {'CANCELLED'}
        amount=active.hl_groom.viewport if self.preset=='CUSTOM' else QUALITY_AMOUNTS[self.preset]
        targets=[h for h in body.children if h.type=='CURVES' and h.get('hl_groom_region')] if self.all_layers else [active]
        try:
            for hair in targets:check_viewport_budget(hair,amount)
            for hair in targets:viewport_quality(hair,amount)
        except (ValueError,RuntimeError,KeyError) as error:self.report({'ERROR'},str(error));return {'CANCELLED'}
        self.report({'INFO'},f'Viewport : {amount:.0%}. Densité au rendu conservée.');return {'FINISHED'}


class HL_OT_groom_paint(bpy.types.Operator):
    bl_idname='humanloom.groom_paint';bl_label='Peindre la densité';bl_options={'REGISTER','UNDO'}
    @classmethod
    def poll(cls,context):return HL_OT_groom_build.poll(context)
    def execute(self,context):
        body=body_from(context);group=body.vertex_groups.get('hl_density_'+body.hl_groom_region.lower())
        if not group:return {'CANCELLED'}
        for obj in tuple(context.selected_objects):obj.select_set(False)
        body.hide_set(False);body.select_set(True);context.view_layer.objects.active=body;body.vertex_groups.active_index=group.index
        bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
        return {'FINISHED'}


class HL_OT_groom_remove(bpy.types.Operator):
    bl_idname='humanloom.groom_remove';bl_label='Supprimer cette zone';bl_options={'REGISTER','UNDO'}
    @classmethod
    def poll(cls,context):return HL_OT_groom_build.poll(context)
    def execute(self,context):
        body=body_from(context);hair=find(body,body.hl_groom_region)
        if hair:
            context.view_layer.objects.active=body;body.select_set(True);discard(hair)
        return {'FINISHED'}


class HL_OT_groom_preset(bpy.types.Operator):
    bl_idname='humanloom.groom_preset';bl_label='Coiffure de départ';bl_options={'REGISTER','UNDO'}
    preset:bpy.props.EnumProperty(items=(('SHORT','Court',''),('LONG','Long',''),('CURLY','Bouclé',''),('COILY','Crépu',''),('STUBBLE','Barbe courte',''),('ALL','Pilosité adulte','')))
    @classmethod
    def poll(cls,context):return HL_OT_groom_build.poll(context)
    def execute(self,context):
        body=body_from(context)
        if self.preset=='ALL':regions=('SCALP','BROWS','BEARD','MOUSTACHE','CHEST','ABDOMEN','BACK','ARMS','LEGS')
        else:regions=('BEARD','MOUSTACHE') if self.preset=='STUBBLE' else ('SCALP','BROWS')
        created=[]
        try:
            for region in regions:
                # Starter buttons add missing layers only, preserving existing sculptures.
                if find(body,region):continue
                cfg=defaults(region)
                if region=='SCALP':
                    cfg.update({'length':{'SHORT':.055,'LONG':.30,'CURLY':.13,'COILY':.10}.get(self.preset,.055),'nature':{'CURLY':.5,'COILY':1.}.get(self.preset,.08),'style':'PARTED' if self.preset=='LONG' else 'SWEPT'})
                if self.preset=='STUBBLE':cfg.update(length=.003,nature=0.)
                created.append(build(body,region,cfg))
        except (ValueError,RuntimeError,OSError,KeyError) as error:
            for hair in created:discard(hair)
            self.report({'ERROR'},str(error));return {'CANCELLED'}
        if not created:self.report({'INFO'},'Aucune zone ajoutée : toutes les zones de cette coiffure existent déjà.');return {'FINISHED'}
        self.report({'INFO'},f'{len(created)} zone(s) ajoutée(s) : '+', '.join(LABELS[h['hl_groom_region']] for h in created)+'.');return {'FINISHED'}


class HL_OT_groom_export(bpy.types.Operator,ExportHelper):
    bl_idname='humanloom.groom_export';bl_label='Exporter le groom';filename_ext='.json'
    filter_glob:bpy.props.StringProperty(default='*.json',options={'HIDDEN'})
    @classmethod
    def poll(cls,context):return HL_OT_groom_build.poll(context)
    def execute(self,context):
        body=body_from(context);layers={r:state(find(body,r).hl_groom) for r in LABELS if find(body,r)}
        try:Path(self.filepath).write_text(json.dumps({'format':FORMAT,'version':SCHEMA,'layers':layers},ensure_ascii=False,indent=2),encoding='utf-8')
        except OSError as error:self.report({'ERROR'},str(error));return {'CANCELLED'}
        return {'FINISHED'}


class HL_OT_groom_import(bpy.types.Operator,ImportHelper):
    bl_idname='humanloom.groom_import';bl_label='Importer le groom';bl_options={'REGISTER','UNDO'};filename_ext='.json'
    filter_glob:bpy.props.StringProperty(default='*.json',options={'HIDDEN'})
    @classmethod
    def poll(cls,context):return HL_OT_groom_build.poll(context)
    def execute(self,context):
        body=body_from(context)
        try:
            if Path(self.filepath).stat().st_size>500000:raise ValueError('Fichier de réglages trop volumineux.')
            payload=json.loads(Path(self.filepath).read_text(encoding='utf-8'))
            if not isinstance(payload,dict) or payload.get('format')!=FORMAT or payload.get('version')!=SCHEMA or not isinstance(payload.get('layers'),dict):raise ValueError('Préréglage HumanLoom invalide.')
            for region,cfg in payload['layers'].items():
                if region not in LABELS:raise ValueError('Zone de groom inconnue.')
                validate(cfg)
                if find(body,region):raise ValueError('Supprimez les zones correspondantes avant import ; les guides sculptés sont conservés.')
            created=[]
            try:
                for region,cfg in payload['layers'].items():created.append(build(body,region,cfg))
            except Exception:
                for hair in created:discard(hair)
                raise
        except (OSError,ValueError,RuntimeError,KeyError) as error:self.report({'ERROR'},str(error));return {'CANCELLED'}
        return {'FINISHED'}


class HL_PT_groom(bpy.types.Panel):
    bl_label='HumanLoom · Cheveux et pilosité';bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='Humain';bl_parent_id='HUMANMODELING_PT_model'
    @classmethod
    def poll(cls,context):return body_from(context) is not None
    def draw(self,context):
        body=body_from(context);layout=self.layout;layout.use_property_split=True
        grid=layout.grid_flow(columns=2,align=True)
        for p,label in (('SHORT','Court'),('LONG','Long'),('CURLY','Bouclé'),('COILY','Crépu'),('STUBBLE','Barbe courte'),('ALL','Pilosité adulte')):grid.operator('humanloom.groom_preset',text=label).preset=p
        layout.prop(body,'hl_groom_region');hair=find(body,body.hl_groom_region)
        if not hair:layout.operator('humanloom.groom_build');return
        cfg=hair.hl_groom
        for name in ('length','nature','variation','frizz') :layout.prop(cfg,name)
        if body.hl_groom_region=='SCALP':layout.prop(cfg,'style')
        for name in ('guides','radius','seed'):layout.prop(cfg,name)
        quality=layout.box();quality.label(text='Viewport et rendu')
        quality.prop(cfg,'density');quality.prop(cfg,'viewport',slider=True)
        if body.hl_groom_region=='SCALP':
            quality.label(text=f'Densité nominale : {cfg.density/10000:.0f} cheveux / cm²')
            row=quality.row(align=True)
            for preset,label in (('SPARSE','Clairsemé'),('NORMAL','Normal'),('DENSE','Dense')):
                row.operator('humanloom.groom_density',text=label).preset=preset
        quality.prop(body,'hl_groom_quality_all')
        row=quality.row(align=True)
        for preset,label in (('LIGHT','Léger'),('BALANCED','Équilibré'),('FULL','Complet')):
            op=row.operator('humanloom.groom_quality',text=label);op.preset=preset;op.all_layers=body.hl_groom_quality_all
        op=quality.operator('humanloom.groom_quality',text='Appliquer mon pourcentage');op.all_layers=body.hl_groom_quality_all
        quality.label(text='Rendu : densité complète, aperçu indépendant')
        box=layout.box();box.label(text='Matériau des fibres')
        for line in render_warnings(context.scene):box.label(text=line,icon='ERROR')
        for name in ('color','grey','roughness','visible'):box.prop(cfg,name)
        box=layout.box();box.prop(cfg,'physics')
        mode=input_value(hair.modifiers['HumanLoom · suivi 5.2'],'Mode')
        box.label(text='Actif : gravité XPBD' if mode=='Physics (Experimental)' else 'Actif : suivi du corps, sans gravité',icon='INFO')
        if cfg.physics=='XPBD':
            for line in domain_warnings(state(cfg)):box.label(text=line,icon='ERROR')
            for name in ('substeps','iterations','bendiness','root_bendiness','collisions'):box.prop(cfg,name)
            box.label(text='Revenir à la première image après changement')
            box.label(text='Puis lire la timeline pour calculer la chute')
        layout.operator('humanloom.groom_apply',text='Appliquer matière / densité / dynamique')
        layout.label(text='Longueur, nature, direction : reconstruire',icon='INFO')
        layout.operator('humanloom.groom_build',text='Reconstruire les guides (remplace la sculpture)')
        row=layout.row(align=True);row.operator('humanloom.groom_select');row.operator('humanloom.groom_remove',text='',icon='TRASH')
        layout.operator('humanloom.groom_paint')
        layout.label(text='Puis utiliser Curves Sculpt pour le coiffage')
        row=layout.row(align=True);row.operator('humanloom.groom_export',text='Exporter réglages');row.operator('humanloom.groom_import',text='Importer réglages')


CLASSES=(HL_GroomSettings,HL_OT_groom_build,HL_OT_groom_select,HL_OT_groom_apply,HL_OT_groom_density,HL_OT_groom_quality,HL_OT_groom_paint,HL_OT_groom_remove,HL_OT_groom_preset,HL_OT_groom_export,HL_OT_groom_import,HL_PT_groom)


def register():
    for cls in CLASSES:bpy.utils.register_class(cls)
    bpy.types.Object.hl_groom=bpy.props.PointerProperty(type=HL_GroomSettings)
    bpy.types.Object.hl_groom_region=bpy.props.EnumProperty(name='Zone de pilosité',items=REGIONS)
    bpy.types.Object.hl_groom_quality_all=bpy.props.BoolProperty(name='Toutes les zones du personnage',default=False)


def unregister():
    del bpy.types.Object.hl_groom_quality_all
    del bpy.types.Object.hl_groom_region;del bpy.types.Object.hl_groom
    for cls in reversed(CLASSES):bpy.utils.unregister_class(cls)
