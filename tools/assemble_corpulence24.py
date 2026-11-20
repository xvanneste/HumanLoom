"""Make side-by-side comparison boards; never resize bodies independently."""
from pathlib import Path
import json,html,zipfile
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'validation/comparaison-corpulence-24'
entries=json.loads((OUT/'comparaisons.json').read_text(encoding='utf-8'))
assert len(entries)==16
for d in ('planches','vignettes'):(OUT/d).mkdir(exist_ok=True)
def font(size,bold=False):return ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf' if bold else 'C:/Windows/Fonts/segoeui.ttf',size)
boards=[]
for sex in ('F','M'):
    for mode,prefix in (('curseur','CG'),('prereglage','PR')):
        cases=[e for e in entries if e['sex']==sex and e['mode']==mode]
        for angle in ('face','profil','trois-quarts','dos','ventre'):
            close=angle=='ventre';rows=('ventre-face','ventre-profil') if close else (angle,)
            height=2460 if close else 1900
            im=Image.new('RGB',(3840,height),'#f1f4f7');draw=ImageDraw.Draw(im)
            title=f"{sex} - {'Corpulence globale seule' if mode=='curseur' else 'Préréglages de silhouette'} - {angle}"
            identifier=f'{prefix}-{sex}-{angle}'
            draw.rectangle((0,0,3840,14),fill='#216aa3')
            draw.text((40,30),title,font=font(52,True),fill='#172b43')
            subtitle='Même caméra, même échelle, même âge adulte (30 ans), muscles inchangés à 0.' if mode=='curseur' else 'Même caméra et même échelle. Les préréglages maigre et mince modifient aussi les muscles (-0,5).'
            draw.text((40,103),subtitle,font=font(29),fill='#536879')
            for col,case in enumerate(cases):
                x=40+col*950
                draw.text((x,170),case['label'].upper(),font=font(43,True),fill='#172b43')
                setting=f"Corpulence globale : {case['value']:+.2f}" if mode=='curseur' else 'Préréglage : '+case['profile']
                draw.text((x,227),setting,font=font(28),fill='#536879')
                for row,key in enumerate(rows):
                    y=290+row*1040
                    path=OUT/case['images'][key]
                    with Image.open(path) as source:
                        assert source.size==((900,1000) if close else (900,1500))
                        im.paste(source,(x,y))
                    if close:draw.text((x+15,y+10),'FACE' if row==0 else 'PROFIL',font=font(26,True),fill='white')
            draw.text((40,height-66),f'{identifier} | Géométrie 0.14 inchangée - subdivision 2 - éclairage sans ombres projetées',font=font(28),fill='#536879')
            path=OUT/'planches'/(identifier+'.jpg');im.save(path,quality=94,subsampling=0)
            im.thumbnail((1000,1000));im.save(OUT/'vignettes'/(identifier+'.jpg'),quality=88)
            boards.append({'id':identifier,'title':title,'image':path.relative_to(OUT).as_posix()})
cards=''.join(f'<article><h2>{html.escape(b["title"])}</h2><a href="{b["image"]}"><img src="vignettes/{b["id"]}.jpg" loading="lazy"></a><p><a href="{b["image"]}">{b["id"]} - Ouvrir en HD</a></p></article>' for b in boards)
page='''<!doctype html><html lang="fr"><meta charset="utf-8"><title>Diagnostic corpulence 0.14</title><style>body{font:17px Segoe UI,Arial;background:#eef2f6;color:#172b43;margin:30px}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(650px,1fr));gap:24px}article{background:white;padding:16px;border-radius:8px}h2{font-size:20px}img{width:100%}a{color:#1965a1}</style><h1>Maigre / mince / normal / gros</h1><p>20 planches, 96 rendus. Caméras et échelles verrouillées. Formes artistiques du générateur actuel, sans correction de géométrie.</p><p>CG : curseur « Corpulence globale » seul. PR : préréglages complets. F et M : les deux pôles morphologiques. Âge adulte, pose A.</p><p><a href="Planches-comparaison.zip">Toutes les planches HD</a> · <a href="diagnostic-controles.json">Mesures des quatre commandes de volume</a></p><main>'''+cards+'</main></html>'
(OUT/'index.html').write_text(page,encoding='utf-8')
(OUT/'planches.json').write_text(json.dumps(boards,ensure_ascii=False,indent=2),encoding='utf-8')
with zipfile.ZipFile(OUT/'Planches-comparaison.zip','w',compression=zipfile.ZIP_STORED) as z:
    for b in boards:z.write(OUT/b['image'],b['image'])
print('COMPARISON24_ASSEMBLED',len(boards))
