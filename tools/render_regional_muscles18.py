import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import render_musculature_review as review
review.PROFILES=(('Neutre',{}),('Muscles régionaux',{'muscles':1.}),('Épaules et dos',{'muscles_shoulders':1.,'muscles_back':1.}),('Jambes',{'muscles_thighs':1.,'muscles_calves':1.}))
if __name__=='__main__':review.main()
