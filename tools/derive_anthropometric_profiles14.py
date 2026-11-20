"""Choose coherent ANSUR records, rather than combining marginal percentiles.

The selected records supply provisional adult modeling targets. Waist/stature
strata describe girths; they do not identify fat percentage or muscularity.
"""
from pathlib import Path
import csv,json,statistics,hashlib,math

ROOT=Path(__file__).resolve().parents[1]/'validation/proportions-14'
DIMENSIONS=('stature','acromialheight','biacromialbreadth','bicristalbreadth','chestheight',
 'waistheightomphalion','iliocristaleheight','buttockheight','crotchheight','kneeheightmidpatella',
 'acromionradialelength','radialestylionlength','chestcircumference','waistcircumference',
 'buttockcircumference','thighcircumference','calfcircumference','neckcircumference',
 'suprasternaleheight','tenthribheight')
FRAME=('acromialheight','biacromialbreadth','bicristalbreadth','kneeheightmidpatella','crotchheight')
result={'source_url':'https://www.openlab.psu.edu/ansur2/',
 'protocol_url':'https://tools.openlab.psu.edu/publicData/ANSURII-TR11-017.pdf',
 'scope':'Adult US Army sample, age 25-39; individual coherent reference rows, not general-population norms. Linear stature normalization is a modeling assumption. Girth strata do not measure adiposity or muscle mass.',
 'sexes':{}}
for sex,label,h in ((0,'FEMALE',1639.),(1,'MALE',1690.)):
    path=ROOT/'source'/f'ANSUR_II_{label}_Public.csv'
    allrows=list(csv.DictReader(path.open(encoding='cp1252')))
    rows=[r for r in allrows if 25<=float(r['Age'])<=39 and abs(float(r['stature'])/h-1)<.045]
    def ratio(r,name):return float(r[name])/float(r['stature'])
    centers={name:statistics.median(ratio(r,name) for r in rows) for name in DIMENSIONS if name!='stature'}
    spread={name:max(statistics.median(abs(ratio(r,name)-centers[name]) for r in rows)*1.4826,.004) for name in centers}
    neutral=min(rows,key=lambda r:sum(((ratio(r,name)-centers[name])/spread[name])**2 for name in centers))
    ranked=sorted(ratio(r,'waistcircumference') for r in rows)
    profiles={}
    for name,q in (('thin',.10),('reference',.50),('fat',.90)):
        target=ranked[round((len(ranked)-1)*q)]
        girths=('chestcircumference','waistcircumference','buttockcircumference','calfcircumference','neckcircumference')
        choices=rows if name=='reference' else [r for r in rows if all((ratio(r,k)>ratio(neutral,k)) if name=='fat' else (ratio(r,k)<ratio(neutral,k)) for k in girths)]
        assert choices,(label,name,'No coherent ordered reference records')
        selected=neutral if name=='reference' else min(choices,key=lambda r:
            8*((ratio(r,'waistcircumference')-target)/spread['waistcircumference'])**2+
            sum(((ratio(r,k)-ratio(neutral,k))/spread[k])**2 for k in FRAME))
        profiles[name]={'subject_id':selected.get('subjectid',selected.get('SubjectId')),'selection_candidates':len(choices),
          'age':int(selected['Age']),'measurements_mm':{k:float(selected[k]) for k in DIMENSIONS},
          'normalized_by_stature':{k:ratio(selected,k) for k in DIMENSIONS if k!='stature'}}
    result['sexes'][str(sex)]={'source_count':len(allrows),'eligible_count':len(rows),
       'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'profiles':profiles}
(ROOT/'anthropometric-profiles.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({sex:{p:{k:round(v['normalized_by_stature'][k],4) for k in ('chestheight','iliocristaleheight','buttockheight','acromialheight','chestcircumference','waistcircumference','buttockcircumference')} for p,v in data['profiles'].items()} for sex,data in result['sexes'].items()},indent=2))
