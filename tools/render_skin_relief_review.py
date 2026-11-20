"""Compare disabled, reference and stronger geometric skin detail."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import render_modeling_review as review
review.VARIANTS=tuple((label+' · '+name,sex,{'age_stage':3.,'skin_relief':amount})
    for sex,label in ((0.,'Féminine'),(1.,'Masculine'))
    for name,amount in (('Sans relief',-1.),('Référence',0.),('Accentué',1.)))
if __name__=='__main__':review.main()
