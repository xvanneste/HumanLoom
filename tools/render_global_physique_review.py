"""Whole-body review: independently varied fat and muscle, no legacy belly field."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import render_musculature_review as review
review.PROFILES=(
    ('Mince · reliefs osseux',{'whole_body':-1.,'muscles':-.7}),
    ('Référence',{}),
    ('Musclé · peu de graisse',{'whole_body':-.35,'muscles':1.,'muscle_definition':1.}),
    ('Corpulence répartie',{'whole_body':1.}),
)
if __name__=='__main__':review.main()
