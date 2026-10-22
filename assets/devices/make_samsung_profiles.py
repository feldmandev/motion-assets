"""Samsung slab profiles: published dimensions and native panel aspect, estimated small hardware."""
from make_device_branding import apply as apply_branding
import json
import math
import sys
from pathlib import Path
BASE=Path(__file__).resolve().parent
DOCUMENTS=BASE.parents[3]/'documents'
sys.path.insert(0,str(DOCUMENTS))
from generate_galaxy_s25_s26_svgs import MODELS, COLORS, wordmark
from svgelements import Path as SvgPath

SOURCES={
24:'https://images.samsung.com/is/content/samsung/assets/us/2401/business/mobile/phones/galaxy/Galaxy_S24_Series_B2B_Spec_Sheet.pdf',
25:'https://www.samsungsvc.co.kr/solution/3187302',
26:'https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2026_1Q_Interim_Report.pdf'}
# width,height,depth, published full-rectangle screen diagonal, native pixels, chassis corner.
DEVICES={
's24':(70.6,147,7.6,6.2,1080,2340,9.3),
's24_plus':(75.9,158.5,7.7,6.7,1440,3120,9.5),
's24_ultra':(79,162.3,8.6,6.8,1440,3120,2.5),
's25':(70.5,146.9,7.2,6.2,1080,2340,9.5),
's25_plus':(75.8,158.4,7.3,6.7,1440,3120,9.5),
's25_ultra':(77.6,162.8,8.2,6.9,1440,3120,6.7),
's26':(71.7,149.6,7.2,6.3,1080,2340,7),
's26_plus':(75.8,158.4,7.3,6.7,1440,3120,7),
's26_ultra':(78.1,163.6,7.9,6.9,1440,3120,7),
}
S24_COLORS={'Onyx Black':'#414143','Marble Gray':'#b9b9b4','Cobalt Violet':'#555568','Amber Yellow':'#e5dab5','Jade Green':'#bacfc1','Sandstone Orange':'#dfbea8','Sapphire Blue':'#b9c8dc'}
S24_ULTRA={'Titanium Gray':'#aca69c','Titanium Black':'#424345','Titanium Violet':'#6b6978','Titanium Yellow':'#e0d1ae','Titanium Blue':'#b5bdc5','Titanium Green':'#bdc4ae','Titanium Orange':'#d5baa6'}

def rgb(h):return [int(h[i:i+2],16)/255 for i in (1,3,5)]
def finish_name(n):
    for compact, spaced in [('icyblue','icy_blue'),('pinkgold','pink_gold'),('coralred','coral_red'),('blueblack','blue_black'),('whitesilver','white_silver'),('silverblue','silver_blue'),('jadegreen','jade_green'),('jetblack','jet_black')]:n=n.replace(compact,spaced)
    return n.replace('_',' ').title()

def logo_contours(width):
    path=SvgPath(wordmark(0,0,width));out=[]
    for sub in path.as_subpaths():
        points=[]
        for seg in sub:
            if seg.__class__.__name__ in ('Move','Close'):continue
            n=12 if seg.__class__.__name__ not in ('Line',) else 1
            for i in range(n+1):
                p=seg.point(i/n)
                if not points or points[-1]!=[p.x,p.y]:points.append([p.x,p.y])
        if len(points)>2:out.append(points)
    return out

def make(key, data):
    w,h,d,diag,px,py,r=data;gen=int(key[1:3]);ultra='ultra' in key
    g=MODELS[key if gen!=24 else key.replace('24','25')]
    scale=diag*25.4/math.hypot(px,py);sw,sh=px*scale,py*scale
    inset=min((w-sw)/2,(h-sh)/2);sr=max(.4,r-inset)
    palette=(S24_ULTRA if ultra else S24_COLORS) if gen==24 else {finish_name(n):v[1] for n,v in COLORS[key].items()}
    finishes={}
    for name,color in palette.items():
        c=rgb(color);rail=[v*.8+.1 for v in c]
        finishes[name]={'back':{'rgb':c},'rail':{'rgb':rail},'bar':{'rgb':[v*.93+.04 for v in c]},'logo':{'rgb':[v*.58 for v in c]}}
    name=next(iter(finishes));m={**finishes[name],'black':{'rgb':[.006,.008,.011],'rough':.4},'flash':{'rgb':[.86,.84,.73],'rough':.4}}
    m['back']['rough']=.37;m['rail'].update(metal=.8,rough=.3);m['bar'].update(metal=.3,rough=.32)
    def xy(x,y):return [w/2-x*w,h/2-y*w]
    lenses=[];windows=[];sensors=[]
    for i,(x,y,diam) in enumerate(g['lenses']):
        p=xy(x,y);diam*=w
        if ultra and i==3:
            sensors.append([*p,diam/2]);continue
        wr=diam/2-.45
        windows.append([*p,wr*2,wr*2,wr]);lenses.append({'kind':'main' if i==1 else 'ultrawide','center_mm':p,'radius_mm':wr*.58,'window':len(windows)-1})
    island=g['island'] if gen==26 else None
    cam={'center_mm':[0,0],'size_mm':[1,1,.5],'bump_mm':0,'optical_bump_mm':1.4 if gen==24 else 1.9,'lens_ring_mm':.45,'windows':windows,'lenses':lenses,'flash':[[*xy(*g['flash'][:2]),g['flash'][2]*w/2]],'flash_surface':'body','sensors':sensors,'sensor_surface':'body'}
    if island:
        x0,y0,x1,y1=island;cw=(x1-x0)*w;ch=(y1-y0)*w
        cam.update(center_mm=xy((x0+x1)/2,(y0+y1)/2),size_mm=[cw,ch,cw/2],bump_mm=.8,roll_mm=.18,optical_bump_mm=1.2,integrated_plateau=True)
    if island and ultra:cam['body_windows']=[3]
    return {'id':'galaxy-'+key.replace('_','-'),'name':'Galaxy '+key.replace('s','S',1).replace('_plus','+').replace('_ultra',' Ultra'),'manufacturer':'Samsung','form_factor':'phone','status':'provisional','finish':name,
      'body_mm':{'width':w,'height':h,'depth':d,'corner_radius':r,'edge_roll_mm':[.30,.25],'front_rail_mm':.45,'rear_inset':.45},'materials':m,'finishes':finishes,
      'screen':{'object':'Device screen','node':'Device screen','panel':'Body','resolution':[px,py],'fit_box_mm':[sw,sh],'center_mm':[0,0,d/2+.035],'corner_radius_mm':sr,'create_cutouts':True,'cutouts':[{'center_mm':[0,h/2-5.0],'radius_mm':1.35}]},
      'camera':cam,'buttons':[{'name':'Volume','side':'right','center_y_mm':h/2-40,'length_mm':21,'width_mm':2.4,'thickness_mm':.35,'radius_mm':1.1},{'name':'Power','side':'right','center_y_mm':h/2-66,'length_mm':12,'width_mm':2.4,'thickness_mm':.35,'radius_mm':1.1}],
      'rear_logo':{'kind':'samsung','center_mm':[0,-h*.405],'contours_mm':logo_contours(w*.28)},
      'accuracy':{'body_dimensions':'Samsung published width, height and thickness; S26 chassis radius 7 mm published in 2026 Q1 report; other radii visual estimates.','screen_resolution':'Samsung native panel resolution; active rectangle derived from published full diagonal and native aspect.','screen_geometry':'Concentric chassis/display corners; front hole location and bezel sizes are estimates pending measured artwork.','camera_geometry':'Rear positions scaled from official render measurements used by the icon collection. Individual lens collars; Ultra laser sensor distinguished from four cameras. Protrusion and internal optics illustrative, not CAD.','finishes':'Official finish names with approximate sRGB and material roughness.','omissions':'USB port, speaker perforations, antenna seams and Ultra S Pen silo pending detail pass.'},
      'sources':[SOURCES[gen],'https://www.samsung.com/uk/smartphones/galaxy-s26/specs/' if gen==26 else f'https://www.samsung.com/uk/smartphones/galaxy-s{gen}/specs/']}

def coverage():
    catalog=json.loads((DOCUMENTS/'tmp/ref5/all_phones/catalog.json').read_text());items=[]
    for item in catalog:
        if item['brand']!='samsung':continue
        pid=item['model'].replace('_','-');profile=BASE/'profiles'/f'{pid}.json'
        if not profile.exists():profile=BASE/'profiles'/f'{pid}-unfolded.json'
        export=BASE/'exports'/profile.stem/'model.glb'
        items.append({'catalog_id':item['model'],'profile_id':pid,'kind':item['kind'],'status':'built-provisional' if export.exists() else 'profile-ready' if profile.exists() else 'pending','reason':None if profile.exists() else 'Requires device-specific reference and geometry work; not substituted with a generic model.'})
    (BASE/'research/samsung-model-coverage.json').write_text(json.dumps({'models':items,'counts':{s:sum(i['status']==s for i in items) for s in ('built-provisional','profile-ready','pending')}},indent=2))

if __name__=='__main__':
    for key,data in DEVICES.items():
        p=apply_branding(make(key,data));(BASE/'profiles'/f"{p['id']}.json").write_text(json.dumps(p,indent=2))
    coverage();print('Generated',len(DEVICES),'Samsung phone profiles')
