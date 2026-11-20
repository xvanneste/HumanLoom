"""Minimal loaded rod diagnostics, independent of hair density or curls."""
from pathlib import Path
import argparse,sys,json
import bpy,numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
import hair_prototype20 as h20

parser=argparse.ArgumentParser()
parser.add_argument('--points',type=int,default=2)
parser.add_argument('--iterations',type=int,default=32)
parser.add_argument('--length',type=float,default=.06)
parser.add_argument('--explicit-length',action='store_true')
parser.add_argument('--threshold',type=float,default=.001)
parser.add_argument('--frames',type=int,default=12)
parser.add_argument('--curvature',type=float,default=0.)
parser.add_argument('--twist',type=float,default=0.)
parser.add_argument('--guides',type=int,default=1)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
assert bpy.app.background and bpy.app.version[:2]==(5,2)
out=h20.ROOT/'validation/physique-cheveux-22';out.mkdir(exist_ok=True)
for obj in tuple(bpy.context.scene.objects):bpy.data.objects.remove(obj,do_unlink=True)
body=h20.load_body()
hair=h20.create_hair(body,count=args.guides)
roots=np.array([hair.data.points[c.first_point_index].position[:] for c in hair.data.curves])
directions=np.array([hair.data.points[c.first_point_index+1].position[:] for c in hair.data.curves])-roots
directions/=np.linalg.norm(directions,axis=1)[:,None]
hair.data.resize_curves([args.points]*args.guides)
hair.data.set_types(type='POLY')
positions=roots[:,None,:]+np.linspace(0,args.length,args.points)[None,:,None]*directions[:,None,:]
if args.curvature or args.twist:
    from hair_nature21 import RestFiber,sample_rest
    local=sample_rest(RestFiber(args.curvature,args.twist,args.length),samples=args.points)
    positions=[]
    for root,direction in zip(roots,directions):
        side=np.array([0.,1.,0.]);side-=direction*np.dot(side,direction);side/=np.linalg.norm(side)
        frame=np.column_stack((side,np.cross(direction,side),direction))
        positions.append(root+local@frame.T)
hair.data.attributes['position'].data.foreach_set('vector',np.asarray(positions).ravel())
mod=hair.modifiers[0]
if args.explicit_length or args.threshold!=.001:
    mod.node_group=mod.node_group.copy()
if args.threshold!=.001:
    for node in mod.node_group.nodes:
        if node.type=='GROUP' and node.node_tree.name in ('Rod Stretch/Shear Constraint','Pin Positions'):
            node.inputs['Error Threshold'].default_value=args.threshold
if args.explicit_length:
    node=next(n for n in mod.node_group.nodes if n.type=='GROUP' and n.node_tree.name=='Rod Stretch/Shear Constraint')
    node.inputs['Custom Length'].default_value=True
    node.inputs['Length'].default_value=args.length/(args.points-1)
for item in mod.node_group.interface.items_tree:
    if item.item_type!='SOCKET' or item.in_out!='INPUT':continue
    value=getattr(mod.properties.inputs,item.identifier)
    if item.name=='Mode':value.value='Physics (Experimental)'
    if item.name=='Gravity' and item.socket_type=='NodeSocketBool':value.value=True
for name,value in [('Substeps',4),('Constraint Steps',args.iterations),('Stretchiness',0.),('Bendiness',.2),('Root Bendiness',.1),('Randomness',False),('Surface Collision',False)]:h20.set_input(mod,name,value)
hair.update_tag()
rows=[];reference=None;attributes={}
for frame in range(1,args.frames+1):
    bpy.context.scene.frame_set(frame)
    p=h20.evaluated_points(hair)
    data=hair.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
    if reference is None:
        reference=p.copy()
        for name in ('rest_length','rest_rotation','rotation','mass','moment_of_inertia'):
            attr=data.attributes.get(name)
            if attr:
                attributes[name]=[{'value':getattr(v,'value',None),'vector':list(v.vector) if hasattr(v,'vector') else None} for v in attr.data][:4]
    strands=p.reshape((args.guides,args.points,3));ref=reference.reshape(strands.shape)
    rows.append({'frame':frame,'length_m':float(np.linalg.norm(np.diff(strands,axis=1),axis=2).sum(axis=1).max()),'root_motion_m':float(np.linalg.norm(strands[:,0]-ref[:,0],axis=1).max()),'tip_motion_m':float(np.linalg.norm(strands[:,-1]-ref[:,-1],axis=1).max())})
label=f'points{args.points}-iterations{args.iterations}-explicit{int(args.explicit_length)}'+('threshold'+str(args.threshold) if args.threshold!=.001 else '')+(f'-frames{args.frames}' if args.frames!=12 else '')+(f'-curvature{args.curvature}' if args.curvature else '')+(f'-guides{args.guides}' if args.guides!=1 else '')
(out/(label+'.json')).write_text(json.dumps({'args':vars(args),'attributes':attributes,'frames':rows},indent=2,default=str),encoding='utf-8')
print('ROD22_DIAGNOSTIC',label,rows[-1],flush=True)
