"""Comparison boards with explicit provenance for the native simulation snapshot."""
from pathlib import Path
import json,zipfile
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'validation/groom-28'
report=json.loads((OUT/'review.json').read_text(encoding='utf-8'))
assert len(report['renders'])==6 and len(report['frames'])==12
font=lambda n,b=False:ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf' if b else 'C:/Windows/Fonts/segoeui.ttf',n)
stages=[('avant-70','Avant : 70 cheveux/cm²','Suivi sans physique'),('densite-180','Corrigé : 180 cheveux/cm²','Mêmes guides, suivi sans physique'),('gravite-180','Après gravité : 180 cheveux/cm²','128 guides XPBD, résultat à l’image 13')]
boards=[]
for view,title in [('face','Face'),('profil','Profil')]:
 board=Image.new('RGB',(2250,1120),'#edf2f6');d=ImageDraw.Draw(board)
 d.text((30,20),'HUMANLOOM 0.15.2 — Densité et gravité — '+title,font=font(34,True),fill='#172b43')
 for i,(stage,label,note) in enumerate(stages):
  x=30+i*740;d.text((x,85),label,font=font(28,True),fill='#216aa3');d.text((x,130),note,font=font(24),fill='#536879')
  with Image.open(OUT/f'{stage}-{view}.png') as im:
   im.verify()
  with Image.open(OUT/f'{stage}-{view}.png') as im:board.paste(im.convert('RGB'),(x,175))
 d.text((30,1040),'Troisième colonne : résultat natif figé après simulation puis interpolé pour ce rendu statique.',font=font(24),fill='#536879')
 d.text((30,1075),'Coiffure courte seulement ; cette revue ne valide pas encore les cheveux longs et les boucles en mouvement.',font=font(23),fill='#536879')
 path=OUT/f'Comparaison-{view}.jpg';board.save(path,quality=94,subsampling=0);boards.append(path.name)
page='''<!doctype html><html lang="fr"><meta charset="utf-8"><title>HumanLoom — densité et gravité</title><style>body{max-width:1700px;margin:auto;padding:28px;font:18px/1.5 Segoe UI,Arial;background:#edf2f6;color:#172b43}img{width:100%;height:auto}a{color:#216aa3}</style><h1>HumanLoom 0.15.2 — densité et gravité</h1><p>Avant : 70 cheveux/cm² sans physique. Correction : 180 cheveux/cm² sur les mêmes guides. Troisième colonne : 128 guides simulés par XPBD natif, avec collisions, puis résultat figé à l’image 13 et interpolé pour un rendu statique. La barbe et les sourcils ne sont pas simulés ici.</p><p><a href="Comparaisons-HD.zip">Images HD et planches</a> · <a href="HumanLoom-densite-gravite-revue.blend">Scène de revue statique</a> · <a href="review.json">Mesures et paramètres</a></p>'''
page+=''.join(f'<p><a href="{b}"><img src="{b}"></a></p>' for b in boards)
(OUT/'index.html').write_text(page,encoding='utf-8')
with zipfile.ZipFile(OUT/'Comparaisons-HD.zip','w',compression=zipfile.ZIP_STORED) as z:
 for f in boards+[r['file'] for r in report['renders']]:z.write(OUT/f,f)
print('ASSEMBLE28_PASS',boards)
