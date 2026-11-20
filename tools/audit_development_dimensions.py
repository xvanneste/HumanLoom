"""Record evaluated developmental dimensions without conflating clinical protocols."""
import json
from pathlib import Path
import sys
import bpy
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from validate_age_dimensions import surface
from experimental_growth_field import head_section


def main():
    from bl_ext.user_default.human_modeling import age_shapes
    output=Path(sys.argv[sys.argv.index('--')+1]).resolve()
    bpy.ops.human_modeling.create();body=bpy.context.object;keys=body.data.shape_keys
    rows=[]
    for sex,label in ((0.,'F'),(1.,'M')):
        keys.key_blocks['Morphologie'].value=sex
        for index,years in enumerate((5,15,30,75)):
            keys['human_modeling_age']=float(index);keys.update_tag();bpy.context.view_layer.update()
            points,faces=surface(body)
            eyes=[surface(eye)[0] for eye in body.children]
            eye_z=float(np.concatenate(eyes)[:,2].mean())
            contour,level=head_section(points,faces,eye_z)
            row={'sex':label,'age_target_years':years,'stature_cm':float(np.ptp(points[:,2])*100),
                 'head_section_proxy_cm':contour*100,'head_section_level_m':level,
                 'eye_envelope_y_mm':[float(np.ptp(eye[:,1])*1000) for eye in eyes],
                 'stature_reference':age_shapes.stature_reference(body,label)}
            rows.append(row);print('DEVELOPMENT_DIMENSIONS',label,years,row['stature_cm'],row['eye_envelope_y_mm'],flush=True)
    output.write_text(json.dumps({'measurements':rows,
        'protocol_limits':{'head':'Horizontal surface section; not validated as clinical occipitofrontal tape circumference',
                           'eye':'Local Y mesh envelope; not validated as biometric axial length. No automatic fitting to ophthalmic norms is performed.'},
        'bibliographic_followup':['https://pmc.ncbi.nlm.nih.gov/articles/PMC6520278/','https://pubmed.ncbi.nlm.nih.gov/33960004/']},indent=2),encoding='utf-8')


if __name__=='__main__':main()
