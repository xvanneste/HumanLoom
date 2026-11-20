"""Lay out honest density comparisons: viewport geometry previews versus final render."""
from pathlib import Path
import json,html,zipfile
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'validation/apercus-rendus-27'
rows=json.loads((OUT/'captures.json').read_text(encoding='utf-8'))
lookup={(r['view'],r['kind'],r.get('fraction')):r for r in rows}
assert len(rows)==12
(OUT/'planches').mkdir(exist_ok=True)
font=lambda n,b=False:ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf' if b else 'C:/Windows/Fonts/segoeui.ttf',n)
boards=[]
for i,(view,title) in enumerate((('face','Face'),('profil','Profil'),('dos','Dos'),('detail','Détail des mèches')),1):
    image=Image.new('RGB',(2400,1200),'#edf2f6');d=ImageDraw.Draw(image)
    identifier=f'Q{i:02d}'
    d.text((32,22),'HUMANLOOM 0.15.1 - '+identifier+' - '+title,font=font(39,True),fill='#172b43')
    d.text((32,85),'Même coiffure, caméra et lumière - aperçu allégé et rendu dense',font=font(29),fill='#536879')
    entries=[lookup[(view,'viewport_geometry_cycles_lighting',.1)],lookup[(view,'viewport_geometry_cycles_lighting',1.)],lookup[(view,'native_cycles_final',None)]]
    labels=['Aperçu léger - 10 %','Aperçu complet - 100 %','Rendu final - densité complète']
    for col,(entry,label) in enumerate(zip(entries,labels)):
        x=32+col*790
        d.text((x,154),label,font=font(30,True),fill='#216aa3')
        if 'curve_counts' in entry:note=f"Cheveux évalués : {entry['curve_counts']['SCALP']:,}".replace(',',' ')
        else:note='Rendu Cycles natif - aperçu réglé à 10 %'
        d.text((x,202),note,font=font(24),fill='#536879')
        with Image.open(OUT/entry['file']) as source:
            source.load();thumb=source.convert('RGB');thumb.thumbnail((755,880),Image.Resampling.LANCZOS)
        image.paste(thumb,(x+(755-thumb.width)//2,245))
    d.text((32,1144),'Aperçus : géométrie évaluée du viewport présentée sous éclairage Cycles pour comparer la densité.',font=font(25),fill='#536879')
    path=OUT/'planches'/(identifier+'.jpg');image.save(path,quality=94,subsampling=0)
    boards.append({'id':identifier,'title':title,'file':path.relative_to(OUT).as_posix(),'sources':[e['file'] for e in entries]})
cards=''.join(f'<section><h2>{b["id"]} - {html.escape(b["title"])}</h2><a href="{b["file"]}"><img src="{b["file"]}"></a><p>'+ ' · '.join(f'<a href="{s}">{html.escape(s)}</a>' for s in b['sources'])+'</p></section>' for b in boards)
page='''<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>HumanLoom - aperçus et rendus</title><style>body{max-width:1800px;padding:26px;margin:auto;background:#edf2f6;color:#172b43;font:17px/1.5 Segoe UI,Arial}section{background:white;padding:18px;margin:25px 0;border-radius:10px}img{width:100%;height:auto}a{color:#1965a1}</style><h1>HumanLoom - aperçu léger et rendu dense</h1><p>De gauche à droite : géométrie du viewport à 10 %, géométrie du viewport à 100 %, puis rendu Cycles natif. Les aperçus sont présentés avec le même éclairage Cycles afin de comparer la densité. Ils ne sont pas des captures de l'interface.</p><p>Le rendu final conserve sa densité complète même lorsque l'aperçu est réglé à 10 %. Les réglages d'implantation et de coiffure sont conservés pour cette comparaison.</p><p><a href="Apercus-et-rendus-HD.zip">Télécharger les quatre planches et les douze images HD</a> · <a href="../groom-25/index.html">Autres coiffures et pilosité</a></p>'''
page+=cards
(OUT/'index.html').write_text(page,encoding='utf-8')
with zipfile.ZipFile(OUT/'Apercus-et-rendus-HD.zip','w',compression=zipfile.ZIP_STORED) as z:
    for b in boards:
        z.write(OUT/b['file'],b['file'])
        for s in b['sources']:z.write(OUT/s,'images/'+s)
(OUT/'planches.json').write_text(json.dumps(boards,ensure_ascii=False,indent=2),encoding='utf-8')
print('QUALITY27_ASSEMBLED',len(boards),'boards',len(rows),'original images')
