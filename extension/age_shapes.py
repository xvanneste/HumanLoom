"""Reference-age metadata and explicit stature calibration sources."""
import hashlib
import json
from pathlib import Path

YEARS=(5,15,30,75)


def metadata(body):
    try:
        from . import human
    except ImportError:
        import human
    stage=human.get_value(body,'age',2.)
    index=round(stage)
    return {'stage_parameter':stage,'anchor_years':YEARS,
            'exact_anchor_years':YEARS[index] if 0<=index<4 and abs(stage-index)<1e-6 else None,
            'scope':'Reference shape interpolation; not a validated chronological growth trajectory'}


def stature_reference(body, sex):
    try:
        from . import human
    except ImportError:
        import human
    stage=human.get_value(body,'age',2.)
    index=round(stage)
    if abs(stage-index)>1e-6:
        raise ValueError('Choisissez une des quatre formes de référence avant calibration.')
    if index in (0,1):
        path=Path(__file__).parent/'data/references'/('who-60-months.json' if index==0 else 'who-180-months.json')
        raw=path.read_bytes();data=json.loads(raw)
        return {'id':data['id'],'age_years':YEARS[index],'sex':sex,'height_cm':data[sex]['height'],
                'source_url':data['sources']['height_'+sex],'sha256':hashlib.sha256(raw).hexdigest(),
                'statistic':data['statistic']}
    from . import measurements
    data=measurements.reference_data()
    group='30_39' if index==2 else '70_79'
    return {'id':data['id'],'age_years':YEARS[index],'group':group,'sex':sex,
            'height_cm':data['groups'][group][sex]['P50'],'source_url':data['source_url'],
            'sha256':data['sha256'],'statistic':'Published age-group median; US cross-sectional reference'}
