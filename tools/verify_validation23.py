"""Check the delivered boards and rasterize the actual PDF for visual review."""
from pathlib import Path
import json, hashlib, zipfile
from html.parser import HTMLParser
from urllib.parse import unquote
from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader
import pypdfium2 as pdfium

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'validation/planches-modelisation-23'
qa = OUT / 'tmp/pdf-qa'
qa.mkdir(parents=True, exist_ok=True)
plan = json.loads((OUT/'plan.json').read_text(encoding='utf-8'))
delivery = json.loads((OUT/'livraison.json').read_text(encoding='utf-8'))
assert delivery['partial'] is False
assert (delivery['boards'], delivery['unique_views_in_plan'], delivery['configurations']) == (103,380,93)
records = {}
for p in OUT.glob('render-shard-*-diagnostic-light.json'):
    records.update(json.loads(p.read_text(encoding='utf-8')))
for view in plan['views']:
    entry = records[view['id']]
    with Image.open(OUT/'images'/(view['id']+'-sans-ombres.png')) as im:
        assert im.size == tuple(entry['resolution'])
        im.verify()
    assert entry['render_subdivision'] == 2 and entry['shape_schema'] == 9
for case in plan['cases']:
    preset = json.loads((OUT/'presets'/(case['id']+'.json')).read_text(encoding='utf-8'))
    assert len(preset['controls']) == 48
    assert preset['morphology'] == case['morph'] and preset['age_stage'] == case['age']
    for key,value in case['controls'].items():
        assert abs(preset['controls'][key]-value) < 1e-6
for board in plan['boards']:
    with Image.open(OUT/'planches'/(board['id']+'.jpg')) as im:
        assert im.size == (2480,3508)
        im.verify()

class Links(HTMLParser):
    def handle_starttag(self, tag, attrs):
        for name,value in attrs:
            if name in ('src','href') and value and not value.startswith(('#','http','data:')):
                assert (OUT/unquote(value)).is_file(),value
Links().feed((OUT/'index.html').read_text(encoding='utf-8'))
asset_hash = hashlib.sha256((ROOT/'extension/data/realistic.blend').read_bytes()).hexdigest()
assert asset_hash == delivery['source_asset_sha256']
pdf_path = OUT/'output/pdf/Validation-modelisation-0.14.pdf'
reader=PdfReader(str(pdf_path))
assert len(reader.pages) == 105
assert 'Validation' in reader.pages[0].extract_text()
assert 'Sommaire' in reader.pages[1].extract_text()
pdf=pdfium.PdfDocument(str(pdf_path))
font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',15)
sheets=[]
for start in range(0,len(pdf),25):
    sheet=Image.new('RGB',(1100,1640),'#cbd3df')
    draw=ImageDraw.Draw(sheet)
    for index in range(start,min(start+25,len(pdf))):
        page=pdf[index]
        bitmap=page.render(scale=.34)
        thumb=bitmap.to_pil().convert('RGB')
        thumb.thumbnail((210,300))
        local=index-start;x=(local%5)*220+5;y=(local//5)*328+21
        sheet.paste(thumb,(x,y))
        draw.text((x,y-19),'Intro '+str(index+1) if index<2 else 'P'+str(index-1).zfill(3),font=font,fill='#172b43')
        if index in (0,1,2,19,41,53,56,71,72,104):
            large=page.render(scale=1.5)
            large.to_pil().save(qa/f'page-{index+1:03d}.png')
            large.close()
        thumb.close();bitmap.close();page.close()
    target=qa/f'overview-{start//25+1}.jpg'
    sheet.save(target,quality=90);sheets.append(str(target.relative_to(OUT)))
pdf.close()
readme='''VALIDATION DE LA MODELISATION 0.14 - BLENDER 5.2
103 planches HD, 380 vues distinctes, 93 configurations.
Les fichiers P001 a P103 contiennent chacun quatre cases A/B/C/D.
Pose de reference A : les cameras tournent autour du personnage, sans rig.
Les cadrages sont ajustes : les echelles ne sont pas identiques entre cases.
Geometrie actuelle, subdivision 2, sans cheveux ni textures, eclairage de controle.
Ces images servent a relever les defauts ; elles ne certifient pas l'anatomie.
Pour signaler une correction : Pxxx, case A/B/C/D, zone concernee.
Le PDF, les rendus originaux et les scenes editables sont dans le dossier local
validation/planches-modelisation-23 ; ouvrir index.html pour les parcourir.
'''
(OUT/'LIRE-MOI.txt').write_text(readme,encoding='utf-8')
archive=OUT/'Planches-HD.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_STORED) as z:
    z.write(OUT/'LIRE-MOI.txt','LIRE-MOI.txt')
    for board in plan['boards']:
        z.write(OUT/'planches'/(board['id']+'.jpg'),'planches/'+board['id']+'.jpg')
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None and len(z.namelist())==104
result={'status':'passed','boards':103,'views':380,'presets':93,'pdf_pages':105,'source_unchanged':True,'gallery_links_exist':True,'pdf_contact_sheets':sheets,'zip_bytes':archive.stat().st_size}
(OUT/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
