"""Package the real groom renders into numbered review boards and a local gallery."""
from pathlib import Path
import json,html,zipfile
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'validation/groom-25'
font=lambda s,b=False:ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf' if b else 'C:/Windows/Fonts/segoeui.ttf',s)
groups=[
 ('G01','Cheveux, sourcils, barbe et moustache',[('Adulte-pilosite-face','Face'),('Adulte-pilosite-profil','Profil'),('Adulte-pilosite-dos','Dos'),('Sourcils-barbe-moustache','Détails du visage')],2),
 ('G02','Nature de fibre - même longueur de contour demandée : 10 cm',[('Nature-lisse','Lisse : 0'),('Nature-ondule','Ondulé : 0,25'),('Nature-boucle','Bouclé : 0,50'),('Nature-frise','Frisé : 0,75'),('Nature-crepu','Crépu : 1')],5),
 ('G03','Cheveux longs - direction avec raie',[('Cheveux-longs-face','Face'),('Cheveux-longs-profil','Profil'),('Cheveux-longs-dos','Dos')],3),
 ('G04','Pilosité corporelle - vues de contrôle',[('Adulte-pilosite-corps','Corps entier'),('Poils-torse','Torse et abdomen'),('Poils-bras','Bras'),('Poils-jambes','Jambes')],2),
 ('G05','Pilosité - corps entier face et dos',[('Adulte-pilosite-corps','Face'),('Adulte-pilosite-corps-dos','Dos')],2),
]
(OUT/'planches').mkdir(exist_ok=True);manifest=[]
for identifier,title,items,columns in groups:
    cellw,cellh=760,960;rows=(len(items)+columns-1)//columns
    im=Image.new('RGB',(columns*cellw+60,rows*cellh+240),'#edf2f6');draw=ImageDraw.Draw(im)
    draw.text((30,25),'HUMANLOOM 0.15 - '+identifier,font=font(32,True),fill='#216aa3')
    draw.text((30,80),title,font=font(36,True),fill='#172b43')
    draw.text((30,135),'Rendus Blender 5.2 - guides procéduraux éditables - mode suivi du corps',font=font(25),fill='#536879')
    for i,(name,label) in enumerate(items):
        x=30+(i%columns)*cellw;y=200+(i//columns)*cellh
        draw.text((x,y),label,font=font(29,True),fill='#172b43')
        with Image.open(OUT/(name+'.png')) as source:
            source.load();thumb=source.convert('RGB');thumb.thumbnail((730,890),Image.Resampling.LANCZOS)
        im.paste(thumb,(x+(730-thumb.width)//2,y+50))
    target=OUT/'planches'/(identifier+'.jpg');im.save(target,quality=93,subsampling=0)
    manifest.append({'id':identifier,'title':title,'image':target.relative_to(OUT).as_posix(),'renders':[n for n,l in items]})
cards=''.join(f'<section><h2>{b["id"]} - {html.escape(b["title"])}</h2><a href="{b["image"]}"><img src="{b["image"]}" loading="lazy"></a><p>'+ ' · '.join(f'<a href="{n}.png">{html.escape(n)}</a>' for n in b['renders'])+'</p></section>' for b in manifest)
(OUT/'index.html').write_text('''<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>HumanLoom 0.15 - revue groom</title><style>body{max-width:1500px;margin:auto;padding:30px;font:17px/1.5 Segoe UI,Arial;background:#edf2f6;color:#172b43}section{background:white;padding:20px;border-radius:12px;margin:28px 0}img{width:100%;height:auto}a{color:#1965a1}h2{font-size:24px}</style><h1>HumanLoom 0.15 - cheveux et pilosité</h1><p>Onze zones intégrées, cinq planches et dix-sept rendus originaux. Les coiffures restent des points de départ artistiques. Les images sont produites en suivi Animation, sans simulation physique.</p><p><a href="human_modeling-0.15.0.zip">Extension installable Blender 5.2</a> · <a href="HumanLoom-groom-revue.blend">Scène éditable</a> · <a href="Planches-groom.zip">Toutes les planches</a></p><p>La physique XPBD reste expérimentale. Le banc court testé ne valide pas toutes les coiffures ou collisions. Les paramètres scientifiques sont documentés dans le dépôt.</p>'''+cards,encoding='utf-8')
with zipfile.ZipFile(OUT/'Planches-groom.zip','w',compression=zipfile.ZIP_STORED) as z:
    for b in manifest:z.write(OUT/b['image'],b['image'])
(OUT/'planches.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
names=set(n for b in manifest for n in b['renders'])
assert len(names)==17 and all((OUT/(n+'.png')).exists() for n in names)
print('GROOM25_ASSEMBLY_PASS',len(manifest),'boards',len(names),'renders')
