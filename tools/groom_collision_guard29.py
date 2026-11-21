"""Prototype: preserve curve vertices, subdivide long segments and project below skin.

This is a geometric interpolation guard, not a new physical solver.
"""
import bpy
from extension import groom

def add_guard(hair,body,passes=3):
 g=bpy.data.node_groups.new('HumanLoom · protection de surface · prototype','GeometryNodeTree');g['hl_owned']=True
 for name,kind,direction in [('Geometry','NodeSocketGeometry','INPUT'),('Surface','NodeSocketObject','INPUT'),('Geometry','NodeSocketGeometry','OUTPUT')]:g.interface.new_socket(name=name,socket_type=kind,in_out=direction)
 src=g.nodes.new('NodeGroupInput');dst=g.nodes.new('NodeGroupOutput');link=g.links.new
 pos=g.nodes.new('GeometryNodeInputPosition');idx=g.nodes.new('GeometryNodeInputIndex')
 nxt=g.nodes.new('GeometryNodeOffsetPointInCurve');nxt.inputs['Offset'].default_value=1;link(idx.outputs['Index'],nxt.inputs['Point Index'])
 sample=g.nodes.new('GeometryNodeFieldAtIndex');sample.data_type='FLOAT_VECTOR';sample.domain='POINT'
 link(nxt.outputs['Point Index'],sample.inputs['Index']);link(pos.outputs['Position'],sample.inputs['Value'])
 dist=g.nodes.new('ShaderNodeVectorMath');dist.operation='DISTANCE';link(pos.outputs['Position'],dist.inputs[0]);link(sample.outputs['Value'],dist.inputs[1])
 div=g.nodes.new('ShaderNodeMath');div.operation='DIVIDE';div.inputs[1].default_value=.001;link(dist.outputs['Value'],div.inputs[0])
 ceil=g.nodes.new('ShaderNodeMath');ceil.operation='CEIL';link(div.outputs[0],ceil.inputs[0])
 sub=g.nodes.new('ShaderNodeMath');sub.operation='SUBTRACT';sub.inputs[1].default_value=1.;link(ceil.outputs[0],sub.inputs[0])
 clamp=g.nodes.new('ShaderNodeClamp');clamp.inputs['Min'].default_value=0.;clamp.inputs['Max'].default_value=64.;link(sub.outputs[0],clamp.inputs['Value'])
 geometry=src.outputs['Geometry']
 for i in range(passes):
  split=g.nodes.new('GeometryNodeSubdivideCurve');link(geometry,split.inputs['Curve']);link(clamp.outputs['Result'],split.inputs['Cuts'])
  project=g.nodes.new('GeometryNodeGroup');project.node_tree=groom.native('Shrinkwrap Hair Curves')
  link(split.outputs['Curve'],project.inputs['Geometry'])
  link(src.outputs['Surface'],next(s for s in project.inputs if s.name=='Surface' and s.type=='OBJECT'))
  for name,value in [('Factor',1.),('Offset Distance',.0005),('Above Surface',0.),('Smoothing Steps',0),('Lock Roots',True)]:project.inputs[name].default_value=value
  geometry=project.outputs['Geometry']
 link(geometry,dst.inputs['Geometry'])
 mod=hair.modifiers.new('Test · protection adaptative','NODES');mod.node_group=g
 groom.set_input(mod,'Surface',body)
 return mod
