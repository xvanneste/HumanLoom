"""Review named modeling axes without claiming clinical body-type categories."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import render_musculature_review as review
review.PROFILES=(
    ('Volume bas',{'whole_body':-1.}),
    ('Référence adulte',{}),
    ('Volume haut',{'whole_body':1.}),
    ('Musculature',{'muscles':1.}),
)
if __name__=='__main__':review.main()
