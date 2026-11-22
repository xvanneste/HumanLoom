"""Reproducible camera plan for modeling review; no posing or geometry edits."""
from pathlib import Path
import json,hashlib

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'validation/planches-modelisation-23'


def make_plan():
    cases=[];views=[];boards=[];case_map={};view_map={}
    def case(morph,age=2,profile='REFERENCE',controls=None):
        data={'morph':morph,'age':age,'profile':profile,'controls':controls or {}}
        key=json.dumps(data,sort_keys=True)
        if key not in case_map:
            data['id']=f'C{len(cases)+1:03d}';cases.append(data);case_map[key]=data['id']
        return case_map[key]
    def view(c,region,yaw,elevation=0,label=None,wire=False):
        data={'case':c,'region':region,'yaw':yaw,'elevation':elevation,'wire':wire}
        key=json.dumps(data,sort_keys=True)
        if key not in view_map:
            data.update(id=f'V{len(views)+1:04d}',label=label or f'{region} / {yaw} deg / {elevation} deg')
            views.append(data);view_map[key]=data['id']
        return view_map[key]
    def board(section,title,items):
        assert len(items)==4
        boards.append({'id':f'P{len(boards)+1:03d}','section':section,'title':title,'views':items})
    directions=[(0,0,'Face'),(45,0,'Trois-quarts avant +X'),(90,0,'Profil +X'),(135,0,'Trois-quarts arriere +X'),(180,0,'Dos'),(225,0,'Trois-quarts arriere -X'),(270,0,'Profil -X'),(315,0,'Trois-quarts avant -X'),(35,45,'Plongee avant'),(35,-25,'Contre-plongee avant'),(0,90,'Dessus'),(0,-90,'Dessous')]
    standard=[(0,0,'Face'),(90,0,'Profil +X'),(45,0,'Trois-quarts'),(180,0,'Dos')]
    def four(c,region='body'):
        return [view(c,region,y,e,label) for y,e,label in standard]
    sexes=((0.,'F'),(1.,'M'))
    for morph,name in sexes:
        c=case(morph)
        for i in range(3):board('01 Corps adultes',f'{name} adulte neutre - rotation {i+1}/3',[view(c,'body',y,e,label) for y,e,label in directions[i*4:i*4+4]])
    for morph,name in sexes:
        c=case(morph)
        for i in range(3):board('02 Visages adultes',f'{name} visage neutre - rotation {i+1}/3',[view(c,'head',y,e,label) for y,e,label in directions[i*4:i*4+4]])
    details=[('Buste et dos',[('torso',0,0,'Buste face'),('torso',180,0,'Dos'),('torso',45,0,'Buste trois-quarts'),('torso',90,0,'Buste profil')]),('Raccords et articulations',[('axilla_pos',45,-25,'Aisselle +X, vue basse'),('axilla_neg',315,-25,'Aisselle -X, vue basse'),('knees',0,0,'Genoux face'),('hips',45,-8,'Bassin et attaches des cuisses')]),('Mains avant et arriere',[('hand_pos',0,0,'Main +X vue avant'),('hand_pos',180,0,'Main +X vue arriere'),('hand_neg',0,0,'Main -X vue avant'),('hand_neg',180,0,'Main -X vue arriere')]),('Mains obliques et laterales',[('hand_pos',45,15,'Main +X oblique'),('hand_pos',90,0,'Main +X vue laterale'),('hand_neg',315,15,'Main -X oblique'),('hand_neg',270,0,'Main -X vue laterale')]),('Pieds et plantes',[('feet',0,0,'Pieds face'),('feet',90,0,'Pieds profil'),('feet',180,0,'Talons'),('feet',0,-90,'Plantes des pieds')]),('Details du visage',[('eyes',0,0,'Paupieres et orbites'),('mouth',45,-8,'Nez et levres'),('ear_pos',90,0,'Oreille +X'),('ear_neg',270,0,'Oreille -X')])]
    for morph,name in sexes:
        c=case(morph)
        for title,items in details:board('03 Details anatomiques',f'{name} - {title}',[view(c,r,y,e,label) for r,y,e,label in items])
    for morph,name in sexes:
        for age,label in enumerate((5,15,30,75)):
            c=case(morph,age)
            board('04 Ages',f'{name} - forme {label} ans - corps',four(c))
            board('04 Ages',f'{name} - forme {label} ans - visage',four(c,'head'))
    profiles=[('REFERENCE','Reference'),('MINCE','Mince'),('FITNESS','Fitness'),('MUSCLE','Muscle'),('AMPLE','Ample'),('AMPLE_MUSCLE','Ample et muscle'),('VERY_LEAN','Tres mince'),('LARGE','Forte corpulence')]
    for morph,name in sexes:
        for profile,label in profiles:board('05 Silhouettes',f'{name} adulte - {label}',four(case(morph,profile=profile)))
    for amount in (0.,.25,.5,.75,1.):board('06 Melange morphologique',f'Morphologie - {int(amount*100)} % vers M',four(case(amount)))
    regions=[('shoulders','Epaules','torso',45,135),('chest','Pectoraux','torso',0,90),('back','Dos','torso',180,135),('arms','Bras','arms',0,90),('abdomen','Abdomen','torso',0,90),('glutes','Fessiers','hips',180,90),('thighs','Cuisses','thighs',0,90),('calves','Mollets','calves',180,90)]
    for morph,name in sexes:
        for i in range(0,8,2):
            items=[];titles=[]
            for identifier,label,region,y1,y2 in regions[i:i+2]:
                c=case(morph,controls={'muscles_'+identifier:1.})
                titles.append(label)
                items.extend([view(c,region,y1,0,label+' +1 / vue A'),view(c,region,y2,0,label+' +1 / vue B')])
            board('07 Muscles regionaux',f'{name} - '+', '.join(titles),items)
    for morph,name in sexes:
        c=case(morph)
        board('08 Topologie',f'{name} - cage sur surface lissee',[view(c,'body',0,0,'Corps face / cage',True),view(c,'body',180,0,'Corps dos / cage',True),view(c,'head',0,0,'Visage face / cage',True),view(c,'head',90,0,'Visage profil / cage',True)])
    for morph,name in sexes:
        for age,label in ((0,5),(1,15),(3,75)):
            for profile,text in (('VERY_LEAN','tres mince'),('LARGE','forte corpulence')):board('09 Combinaisons ages et volumes',f'{name} - {label} ans - {text}',four(case(morph,age,profile)))
    face_controls=[('head_width','Largeur de tete',0,45),('jaw','Machoire',0,90),('nose_length','Avancee du nez',90,45),('nose_width','Largeur du nez',0,45),('mouth','Largeur de bouche',0,45),('eyelid_aperture','Ouverture des paupieres',0,45),('lip_thickness','Epaisseur des levres',0,90),('ears_angle','Orientation des oreilles',0,180),('forehead','Hauteur du front',0,90),('facial_asymmetry','Asymetrie du visage',0,45)]
    for morph,name in sexes:
        for identifier,label,y1,y2 in face_controls:
            items=[]
            for value in (-1.,1.):
                c=case(morph,controls={identifier:value})
                items.extend([view(c,'head',y1,0,f'{label} {value:+.0f} / vue A'),view(c,'head',y2,0,f'{label} {value:+.0f} / vue B')])
            board('10 Reglages du visage',f'{name} - {label} - extremes',items)
    plan={'version':'0.14.0','schema':9,'pose':'Reference A, sans rig ni modification de pose','cases':cases,'views':views,'boards':boards,'asset_sha256':hashlib.sha256((ROOT/'tools/data/realistic.blend').read_bytes()).hexdigest()}
    return plan


if __name__=='__main__':
    OUT.mkdir(exist_ok=True)
    plan=make_plan()
    (OUT/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
    print('REVIEW_PLAN',len(plan['boards']),'boards',len(plan['views']),'unique views',len(plan['cases']),'configurations')
