"""Review new face controls on both endpoints, including full-body frames."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import render_modeling_review as review

review.VARIANTS=tuple((label+' · '+name,sex,settings) for sex,label in ((0.,'Féminine'),(1.,'Masculine'))
    for name,settings in (
        ('Référence',{}),
        ('Fin',{'ears_size':-.6,'nose_bridge':-.5,'eyelid_aperture':.5,'lip_thickness':.6,'jaw_angle':-.5}),
        ('Marqué',{'ears_size':.6,'ears_angle':.5,'nose_bridge':.7,'eyelid_aperture':-.5,'mouth_corner':-.3,'jaw_angle':.6,'facial_asymmetry':.65})))
if __name__=='__main__':review.main()
