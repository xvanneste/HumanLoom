from pathlib import Path
import sys,json
import bpy,numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from validate_age_dimensions import surface
from bl_ext.user_default.human_modeling import geometry_quality as qa
bpy.ops.human_modeling.create();body=bpy.context.object;keys=body.data.shape_keys
body.modifiers['Human Modeling · Surface'].levels=2
keys.key_blocks['Morphologie'].value=1.;keys['human_modeling_age']=2.
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
keys['hm_whole_body']=float(args[0]) if args else -1.;keys['hm_muscles']=float(args[1]) if args else -1.;keys.update_tag();bpy.context.view_layer.update()
p,f=surface(body);report=qa.intersections(p,f,triangle_budget=400000)
report['crossing_vertices_m']=[[p[f[a]].tolist(),p[f[b]].tolist()] for a,b in report['sample_triangle_pairs']]
out=Path(args[2]).resolve() if len(args)>2 else Path(__file__).resolve().parents[1]/'validation/atlas-15/croisement-candidat-08.json'
out.write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report),flush=True)
