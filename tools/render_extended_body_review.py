"""Review the extended volume range in full-body front/profile/back views."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import render_musculature_review as review
review.PROFILES=(
    ('Très mince',{'body_mass':-1.,'corpulence':-.7,'adiposity':-.56,'muscles':-.5}),
    ('Référence',{}),
    ('Forte corpulence',{'body_mass':1.,'corpulence':1.,'adiposity':.8}),
    ('Forte et musclée',{'body_mass':1.,'corpulence':1.,'adiposity':.8,'muscles':1.,'muscle_definition':.3}),
)
if __name__=='__main__':review.main()
