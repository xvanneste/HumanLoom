"""Create reproducible surface-anchor candidates on the indexed native base.

Anchors are visual modeling approximations, not palpated skeletal landmarks.
Their barycentric addresses are shared by both morph endpoints and all ages.
Orthographic reviews are required before an anchor is used as a constraint.
"""
from pathlib import Path
import sys,json
import bpy,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from experimental_growth_field import endpoint
from experimental_age_transfer import coordinates
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'extension'))
from bl_ext.user_default.human_modeling.landmark_sets import topology


# Rays are placement gestures in the native female reference, in metres. They
# do not define target population ratios or change the geometry of the body.
RAYS={
 'suprasternale':('SN','front',(0.,-.6,1.365),(0,1,0),73),
 'cervicale':('C7','back',(0.,.6,1.390),(0,-1,0),37),
 'menton':('ME','front',(0.,-.6,1.445),(0,1,0),0),
 'omphalion':('OM','front',(0.,-.6,.990),(0,1,0),0),
 'acromion':('AC','top',(.165,0.,1.8),(0,0,-1),33),
 'radiale':('RA','side',(.6,.012,1.055),(-1,0,0),65),
 'stylion':('ST','medial',(.290,-.045,.855),(1,0,0),70),
 'ulnar_wrist':('UW','side',(.6,-.045,.855),(-1,0,0),0),
 'iliocristale':('IC','side',(.19,.005,1.015),(-1,0,0),49),
 'asis':('AS','front',(.116,-.6,.978),(0,1,0),0),
 'psis':('PS','back',(.045,.6,.978),(0,-1,0),0),
 'trochanterion':('TR','side',(.24,.002,.878),(-1,0,0),79),
 'midpatella':('PA','front',(.097,-.6,.455),(0,1,0),58),
 'lateral_malleolus':('LM','side',(.6,.005,.080),(-1,0,0),0),
 'gluteal_furrow':('GF','back',(.092,.6,.740),(0,-1,0),0),
 'chest_point':('CP','front',(.072,-.6,1.165),(0,1,0),111),
 'buttock_point':('BP','back',(.085,.6,.850),(0,-1,0),103),
}
PAIRED=set(RAYS)-{'suprasternale','cervicale','menton','omphalion'}


def position(points,anchor):
    return np.sum(points[anchor['triangle']]*np.array(anchor['barycentric'])[:,None],axis=0)


def main():
    source,out=[Path(p).resolve() for p in sys.argv[sys.argv.index('--')+1:]];out.parent.mkdir(parents=True,exist_ok=True)
    with bpy.data.libraries.load(str(source),link=False) as (_,t):t.collections=['Realistic Human Base']
    body=next(o for o in t.collections[0].objects if o.get('human_modeling_body'))
    points=endpoint(body,0);body.data.calc_loop_triangles();faces=np.array([t.vertices[:] for t in body.data.loop_triangles])
    tree=BVHTree.FromPolygons([Vector(p) for p in points],faces.tolist(),all_triangles=True)
    anchors={}
    for name,(short,view,origin,direction,page) in RAYS.items():
        for side in ((1,-1) if name in PAIRED else (1,)):
            start=np.array(origin,dtype=float);ray=np.array(direction,dtype=float);start[0]*=side;ray[0]*=side
            location,_,index,_=tree.ray_cast(Vector(start),Vector(ray),2.)
            assert location is not None,(name,side)
            # Pelvic rays start inside the arm envelope. A hit on a forearm is
            # not an acceptable fallback for an occluded pelvic landmark.
            if name in ('iliocristale','trochanterion'):
                assert 0 < side*location.x < (.19 if name=='iliocristale' else .23),(name,'outside pelvic search compartment',location)
            triangle=faces[index];a,b,c=points[triangle]
            uv=np.linalg.lstsq(np.column_stack((b-a,c-a)),np.array(location)-a,rcond=None)[0]
            weights=[float(1-uv.sum()),float(uv[0]),float(uv[1])]
            identifier=name+('_l' if side==1 else '_r') if name in PAIRED else name
            anchors[identifier]={'short':short+('L' if side==1 else 'R') if name in PAIRED else short,
              'triangle':triangle.tolist(),'barycentric':weights,'placement_view':view,
              'status':'candidate_surface_estimate','protocol_pdf_page':page or None,
              'scope':'Visual surface modeling anchor; not palpated bone or a clinical validation'}
    endpoints=[endpoint(body,sex) for sex in (0,1)]
    result={'format':'human_modeling.surface_atlas','version':1,'topology_sha256':topology(body),
      'source_asset':'Native Studio indexed base as preserved in 0.13','protocol_url':'https://tools.openlab.psu.edu/publicData/ANSURII-TR11-017.pdf',
      'status':'candidate_to_review_on_both_morphologies','anchors':anchors,
      'endpoint_positions_m':{str(s):{k:position(p,v).tolist() for k,v in anchors.items()} for s,p in enumerate(endpoints)}}
    out.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('SURFACE_ATLAS_CANDIDATES',len(anchors),flush=True)


if __name__=='__main__':main()
