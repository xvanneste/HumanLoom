"""Lay out real Blender renders as numbered boards, a PDF and a local gallery."""
from pathlib import Path
from functools import lru_cache
import sys,json,html,os,argparse
from PIL import Image,ImageDraw,ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pypdf import PdfReader
sys.path.insert(0,str(Path(__file__).resolve().parent))
from validation_boards23 import ROOT,OUT

parser=argparse.ArgumentParser();parser.add_argument('--partial',action='store_true');args=parser.parse_args()
plan=json.loads((OUT/'plan.json').read_text(encoding='utf-8'))
cases={c['id']:c for c in plan['cases']};views={v['id']:v for v in plan['views']}
records={}
for path in OUT.glob('render-shard-*-diagnostic-light.json'):records.update(json.loads(path.read_text(encoding='utf-8')))
font_path=Path('C:/Windows/Fonts/segoeui.ttf');bold_path=Path('C:/Windows/Fonts/segoeuib.ttf')
assert font_path.exists() and bold_path.exists()
for folder in ('planches','vignettes','tmp/pdf','output/pdf'):(OUT/folder).mkdir(parents=True,exist_ok=True)

@lru_cache(maxsize=32)
def font(size,bold=False):return ImageFont.truetype(str(bold_path if bold else font_path),size)

def fitted(draw,text,box,size=42,bold=False,fill='#17202e'):
    while draw.textlength(text,font=font(size,bold))>box[2]-box[0] and size>20:size-=1
    draw.text((box[0],box[1]),text,font=font(size,bold),fill=fill)

def raw_path(identifier):return OUT/'images'/(identifier+'-sans-ombres.png')

profile_names={'REFERENCE':'Référence','MINCE':'Mince','FITNESS':'Fitness','MUSCLE':'Musclé','AMPLE':'Ample','AMPLE_MUSCLE':'Ample et musclé','VERY_LEAN':'Très mince','LARGE':'Forte corpulence'}
def description(case):
    morph='F' if case['morph']==0 else 'M' if case['morph']==1 else f"{round(case['morph']*100)} % vers M"
    return f"{case['id']} | {morph} | forme {(5,15,30,75)[case['age']]} ans | {profile_names[case['profile']]}"

boards=[]
for board in plan['boards']:
    missing=[identifier for identifier in board['views'] if not raw_path(identifier).exists() or identifier not in records]
    if missing:
        if args.partial:continue
        raise RuntimeError('Missing rendered view(s): '+str(missing))
    image=Image.new('RGB',(2480,3508),'#f4f6f8');draw=ImageDraw.Draw(image)
    draw.rectangle((0,0,2480,20),fill='#2069a5')
    draw.text((76,52),board['section'].upper(),font=font(33,True),fill='#2069a5')
    draw.rounded_rectangle((2190,50,2400,135),radius=14,fill='#172b43')
    draw.text((2224,64),board['id'],font=font(49,True),fill='white')
    fitted(draw,board['title'],(76,118,2380,200),64,True)
    draw.text((78,215),'Géométrie 0.14 - pose de référence - éclairage de contrôle sans ombres projetées',font=font(29),fill='#566574')
    links=[]
    for index,identifier in enumerate(board['views']):
        view=views[identifier];case=cases[view['case']];entry=records[identifier]
        x=76+(index%2)*1190;y=300+(index//2)*1515
        draw.rounded_rectangle((x,y,x+1138,y+1465),radius=12,fill='white',outline='#d4dce4',width=2)
        fitted(draw,f"{'ABCD'[index]} - {view['label']} | {identifier}",(x+24,y+18,x+1110,y+70),38,True)
        fitted(draw,description(case),(x+24,y+72,x+1110,y+112),29,False,'#566574')
        with Image.open(raw_path(identifier)) as source:
            assert source.size==tuple(entry['resolution'])
            source.load()
            thumb=source.convert('RGB');thumb.thumbnail((1090,1265),Image.Resampling.LANCZOS)
        px=x+24+(1090-thumb.width)//2;py=y+130+(1265-thumb.height)//2
        image.paste(thumb,(px,py))
        if view['region']=='body':note=f"Hauteur de cage mesurée : {entry['model_height_m']:.3f} m - cadrage ajusté"
        else:note='Vue rapprochée - cadrage ajusté à la région montrée'
        fitted(draw,note,(x+24,y+1400,x+1110,y+1440),27,False,'#566574')
        links.append({'label':'ABCD'[index],'view':identifier,'case':case['id'],'image':str(raw_path(identifier).relative_to(OUT)).replace('\\','/')})
    draw.text((78,3430),'Les cadrages sont adaptés : les échelles entre cases ne sont pas identiques.',font=font(27),fill='#566574')
    path=OUT/'planches'/(board['id']+'.jpg');image.save(path,quality=94,subsampling=0)
    small=image.copy();small.thumbnail((380,538),Image.Resampling.LANCZOS);small.save(OUT/'vignettes'/(board['id']+'.jpg'),quality=82)
    pdfimage=image.copy();pdfimage.thumbnail((1900,2688),Image.Resampling.LANCZOS);pdfimage.save(OUT/'tmp/pdf'/(board['id']+'.jpg'),quality=88)
    boards.append({**board,'image':str(path.relative_to(OUT)).replace('\\','/'),'links':links})
    print('BOARD23_ASSEMBLED',board['id'],flush=True)

if not boards:raise RuntimeError('No complete board to assemble')
pdfmetrics.registerFont(TTFont('Review',str(font_path)));pdfmetrics.registerFont(TTFont('ReviewBold',str(bold_path)))
pdf_path=OUT/'output/pdf/Validation-modelisation-0.14.pdf'
pdf=canvas.Canvas(str(pdf_path),pagesize=A4,pageCompression=1);W,H=A4
pdf.setTitle('Validation de la modélisation Human Modeling 0.14');pdf.setAuthor('BlenderDev')
def line(value,y,size=12,bold=False,color='#172b43'):
    pdf.setFillColor(color);pdf.setFont('ReviewBold' if bold else 'Review',size);pdf.drawString(42,y,value)
pdf.setFillColor('#f4f6f8');pdf.rect(0,0,W,H,fill=1,stroke=0)
line('HUMAN MODELING 0.14',H-80,14,True,'#2069a5')
line('Validation de la',H-160,32,True);line('modélisation',H-201,32,True)
line(f"{len(boards)} planches - {len(views)} vues distinctes prévues",H-258,17)
line('Corps, visage, âges, silhouettes et réglages régionaux',H-295,12)
notes=[
 'La géométrie est celle du générateur 0.14, à subdivision 2.',
 'Les personnages conservent leur pose de référence : aucun rig n’est appliqué.',
 'Les caméras tournent autour du modèle ; elles ne modifient pas les formes.',
 'Les vues de dessus et de dessous comportent des occultations normales.',
 'Les cadrages sont ajustés : comparer les proportions, pas la taille sur la page.',
 'Les variantes d’âge et de corpulence sont des formes artistiques en validation.',
 'Ces planches servent à repérer les défauts ; elles ne certifient pas l’anatomie.',
 'Les images HD et les préréglages sont accessibles dans la galerie locale.',
 'Pour un retour précis : numéro de planche, case A/B/C/D et zone concernée.',
]
for i,note in enumerate(notes):line(note,H-370-i*27,10.2)
line('Exemple : « P015, case B : raccord du poignet à revoir ».',100,11,True)
line('Blender 5.2 uniquement - dossier de revue du 20 novembre 2026',68,9)
pdf.showPage()
line('Sommaire des planches',H-70,24,True)
sections=[]
for board in boards:
    if board['section'] not in [item[0] for item in sections]:sections.append([board['section'],board['id'],board['id']])
    else:next(item for item in sections if item[0]==board['section'])[2]=board['id']
for i,(section,start,end) in enumerate(sections):
    y=H-133-i*48
    line(section,y,12,True);line(start+' à '+end,y-19,10,False,'#566574')
    pdf.linkRect('',start,(40,y-23,W-40,y+18),relative=0,thickness=0)
line('F et M désignent les deux pôles de morphologie du générateur.',150,10)
line('+X et -X désignent les côtés dans le repère du modèle.',127,10)
line('La cage bleue des vues de topologie est un repère ajouté pour la revue.',104,10)
pdf.showPage()
section=None
for board in boards:
    pdf.bookmarkPage(board['id'])
    if section!=board['section']:
        section=board['section'];pdf.addOutlineEntry(section,board['id'],level=0,closed=False)
    pdf.addOutlineEntry(board['id']+' - '+board['title'],board['id'],level=1,closed=True)
    pdf.drawImage(str(OUT/'tmp/pdf'/(board['id']+'.jpg')),0,0,width=W,height=H)
    pdf.showPage()
pdf.save()
reader=PdfReader(str(pdf_path));assert len(reader.pages)==len(boards)+2

cards=[]
for board in boards:
    links=' '.join(f'<a href="{html.escape(v["image"])}" target="_blank">{v["label"]} · {v["view"]} HD</a>' for v in board['links'])
    presets=' '.join(f'<a href="presets/{case}.json">{case}</a>' for case in dict.fromkeys(v['case'] for v in board['links']))
    cards.append(f'<article data-search="{html.escape(board["id"]+" "+board["section"]+" "+board["title"],quote=True)}"><a href="{board["image"]}" target="_blank"><img loading="lazy" src="vignettes/{board["id"]}.jpg" alt="{html.escape(board["title"])}"></a><div><small>{html.escape(board["section"])}</small><h2>{board["id"]} - {html.escape(board["title"])}</h2><p><a href="{board["image"]}" target="_blank">Ouvrir la planche HD</a></p><p class="links">{links}</p><p class="links">Préréglages : {presets}</p></div></article>')
page='''<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Validation modélisation 0.14</title><style>
*{box-sizing:border-box}body{margin:0;background:#eef2f6;color:#172b43;font:16px/1.5 Segoe UI,Arial,sans-serif}header{padding:36px max(24px,calc((100vw - 1450px)/2));background:#172b43;color:white}header h1{margin:0 0 8px;font-size:34px}header a{color:#bce4ff}main{max-width:1500px;margin:auto;padding:24px}input{width:100%;padding:15px;border:1px solid #bbc8d5;border-radius:8px;font:inherit;margin-bottom:20px}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(310px,1fr));gap:22px}article{background:white;border-radius:12px;overflow:hidden;box-shadow:0 2px 7px #182e4014}article img{width:100%;display:block}article>div{padding:16px}h2{font-size:18px;line-height:1.35;margin:7px 0}small{color:#53718b}a{color:#1965a1}.links{display:flex;flex-wrap:wrap;gap:8px;font-size:14px}article[hidden]{display:none}#count{margin-bottom:16px;color:#53718b}</style>
<header><h1>Validation de la modélisation 0.14</h1><p>__COUNT__ planches · 380 vues distinctes · 93 configurations · Blender 5.2</p><p>Pose de référence, géométrie inchangée. Cadrages adaptés, échelles non communes. Les formes d’âge et de corpulence restent en validation.</p><p><a href="output/pdf/Validation-modelisation-0.14.pdf">Télécharger le PDF complet</a> · <a href="Revue-editable-0.blend">Scène F éditable</a> · <a href="Revue-editable-1.blend">Scène M éditable</a></p><p>Pour un retour : planche Pxxx, case A/B/C/D, puis la zone à corriger. Les liens HD ouvrent les rendus originaux.</p></header><main><input id="search" type="search" placeholder="Rechercher : visage, mains, 75 ans, P015, muscles…" aria-label="Filtrer les planches"><div id="count"></div><div class="grid">__CARDS__</div></main><script>
const input=document.querySelector('#search'),cards=[...document.querySelectorAll('article')],count=document.querySelector('#count');function filter(){let q=input.value.normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase(),n=0;for(let c of cards){c.hidden=!c.dataset.search.normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase().includes(q);if(!c.hidden)n++}count.textContent=n+' planches affichées'}input.addEventListener('input',filter);filter();</script></html>'''
(OUT/'index.html').write_text(page.replace('__COUNT__',str(len(boards))).replace('__CARDS__',''.join(cards)),encoding='utf-8')
(OUT/'planches.json').write_text(json.dumps(boards,ensure_ascii=False,indent=2),encoding='utf-8')
summary={'boards':len(boards),'unique_views_in_plan':len(views),'configurations':len(cases),'pdf_pages':len(reader.pages),'pdf_bytes':pdf_path.stat().st_size,'lighting':'Workbench studio, cavity, no projected shadows','partial':args.partial,'source_asset_sha256':plan['asset_sha256']}
(OUT/'livraison.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print('VALIDATION23_ASSEMBLED',summary,flush=True)
