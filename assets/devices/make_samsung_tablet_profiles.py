"""Samsung tablet profiles: published chassis/display specs; estimated small geometry."""
from make_device_branding import apply as apply_branding
import json
import sys
from pathlib import Path
BASE = Path(__file__).resolve().parent
SOURCES = {
 's9': 'https://news.samsung.com/global/samsung-galaxy-tab-s9-sets-the-new-standard-to-bring-galaxys-premium-experience-to-a-tablet',
 's10': 'https://www.samsung.com/ae/support/mobile-devices/galaxy-tab-s10-series-colors-dimensions-and-weight/',
 's11': 'https://news.samsung.com/uk/meet-samsung-galaxy-tab-s11-series-packing-everything-you-expect-from-a-premium-tablet',
}
# Portrait coordinates keep the long-edge camera at the right side of the display.
MODELS = [
 ('s9',165.8,254.3,5.9,1600,2560,11,1,False),
 ('s9-plus',185.4,285.4,5.7,1752,2800,12.4,2,False),
 ('s9-ultra',208.6,326.4,5.5,1848,2960,14.6,2,True),
 ('s10-plus',185.4,285.4,5.6,1752,2800,12.4,2,False),
 ('s10-ultra',208.6,326.4,5.4,1848,2960,14.6,2,True),
 ('s11',165.3,253.8,5.5,1600,2560,11,1,False),
 ('s11-ultra',208.5,326.3,5.1,1848,2960,14.6,2,True),
]
def rgb(h):
 return [int(h[i:i+2],16)/255 for i in (0,2,4)]
def profile(row):
 suffix,w,h,d,rx,ry,diag,cameras,ultra=row
 generation=suffix.split('-')[0]
 colors={'Graphite':'53565a','Beige':'d9d5c9'} if generation=='s9' else ({'Moonstone Gray':'62636a','Platinum Silver':'c8c9cb'} if generation=='s10' else {'Grey':'62666b','Silver':'c9ccce'})
 finishes={name:{role:{'rgb':rgb(color),'metal':.75,'rough':.35} for role in ('back','rail','bar')} for name,color in colors.items()}
 default=next(iter(finishes))
 # Full rectangular display diagonal and exact native pixel aspect.
 scale=diag*25.4/(rx*rx+ry*ry)**.5
 sw,sh=rx*scale,ry*scale
 bezel=(w-sw)/2
 radius=9.5 if ultra else 9.0
 cutouts=[]
 if ultra:
  # Ultra's long-edge notch: S11 has a smaller single camera notch.
  length=12 if generation=='s11' else 21
  cutouts=[{'center_mm':[sw/2-1.6,0], 'size_mm':[5.0,length], 'radius_mm':2.3}]
 else:
  cutouts=[{'center_mm':[w/2-bezel/2,0], 'radius_mm':1.35}]
 x=w/2-12.0
 ys=[h/2-14-i*17 for i in range(cameras)]
 windows=[[x,y,10.5,10.5,5.25] for y in ys]
 return {'id':'galaxy-tab-'+suffix, 'name':'Galaxy Tab '+suffix.upper().replace('-PLUS','+').replace('-ULTRA',' Ultra'),
 'manufacturer':'Samsung','form_factor':'tablet','status':'provisional','finish':default,
 'body_mm':{'width':w,'height':h,'depth':d,'corner_radius':radius,'edge_roll':.32,'front_rail_mm':.45},
 'materials':{**finishes[default],'black':{'rgb':[.007,.009,.012],'rough':.5},'flash':{'rgb':[.85,.84,.77],'rough':.33}},
 'finishes':finishes,
 'screen':{'object':'Device screen','node':'Device screen','panel':'Body','resolution':[rx,ry],
 'fit_box_mm':[sw,sh],'center_mm':[0,0,d/2+.035],'corner_radius_mm':max(2,radius-bezel),
 'create_cutouts':True,'cutouts':cutouts},
 'camera':{'center_mm':[x,sum(ys)/len(ys)],'size_mm':[12,17*cameras,5.5],'bump_mm':0,
 'optical_bump_mm':1.1,'lens_ring_mm':.65,'windows':windows,
 'lenses':[{'kind':'main' if i==0 else 'ultrawide','center_mm':[x,y],'radius_mm':2.5 if i==0 else 2.0,'window':i} for i,y in enumerate(ys)],'flash':[]},
 'buttons':[{'name':'Side key','side':'right','center_y_mm':h/2-24,'length_mm':10,'width_mm':2,'thickness_mm':.35,'radius_mm':.8},
 {'name':'Volume rocker','side':'right','center_y_mm':h/2-44,'length_mm':18,'width_mm':2,'thickness_mm':.35,'radius_mm':.8}],
 'accuracy':{'body_dimensions':'Samsung published metric dimensions','screen_resolution':'Samsung native panel resolution; exact aspect ratio',
 'screen_geometry':'Published rectangular diagonal; corner radii and camera notch estimated from product design',
 'camera_geometry':'Separate rear lens rings, approximate diameter and position; illustrative optics',
 'details':'Wi-Fi chassis blockout; no S Pen accessory; rear wordmark, ports, antenna seams and charging strip not modeled',
 'finishes':'Approximate display RGB; not measured material samples'},
 'sources':[SOURCES[generation],'https://www.samsung.com/us/support/answer/ANS10003691/' if generation=='s9' else 'https://www.samsung.com/us/support/answer/ANS10003773/' if generation=='s10' else SOURCES[generation]]}
NEW_SOURCES = {
 'a11':'https://www.samsung.com/uk/tablets/galaxy-tab-a/galaxy-tab-a11-grey-64gb-wi-fi-sm-x130nzaaeub/',
 'a11-plus':'https://www.samsung.com/uk/tablets/galaxy-tab-a/galaxy-tab-a11-plus-silver-128gb-wi-fi-sm-x230nzsreub/',
 's6':'https://news.samsung.com/us/samsung-galaxy-tab-s6-new-tablet-enhances-creativity-and-productivity/',
 's6-lite-2020':'https://news.samsung.com/tw/galaxy-tab-s6-lite',
 's6-lite-2022':'https://news.samsung.com/id/samsung-galaxy-tab-s6-lite-2022-semakin-powerful-ditenagai-snapdragon',
 's6-lite-2024':'https://api.samsungmobilepress.com/press-releases/samsung-galaxy-tab-s6-lite-2024-style-and-function-in-a-compact-package',
 's7':'https://news.samsung.com/uk/samsung-announces-new-mystic-navy-colour-for-galaxy-tab-s7-and-tab-s7-further-expanding-the-samsung-galaxy-ecosystem',
 's7-fe':'https://news.samsung.com/ca/power-your-productivity-and-play-with-the-samsung-galaxy-tab-s7-fe',
 's8':'https://news.samsung.com/global/breaking-the-rules-with-galaxy-tab-s8-series-the-biggest-boldest-most-versatile-galaxy-tablet-ever',
 's9-fe':'https://news.samsung.com/global/samsung-galaxy-s23-fe-galaxy-tab-s9-fe-and-galaxy-buds-fe-bring-standout-features-to-even-more-users',
 's10-fe':'https://news.samsung.com/es/la-serie-galaxy-tab-s10-fe-acerca-las-experiencias-inteligentes-a-todo-el-mundo-con-un-diseno-premium-y-versatil',
 's10-lite':'https://www.samsung.com/uk/tablets/galaxy-tab-s/galaxy-tab-s10-lite-grey-128gb-wi-fi-sm-x400nzareub/',
 's12-plus':'https://www.samsung.com/uk/tablets/galaxy-tab-s/galaxy-tab-s12-plus-grey-256gb-sm-x840nzareub/',
 's12-ultra':'https://www.samsung.com/uk/tablets/galaxy-tab-s/galaxy-tab-s12-ultra-grey-256gb-sm-x940nzareub/',
}
# Published width, height, depth, portrait native pixels, full rectangular diagonal (mm).
# Use published metric diagonals where available rather than rounded inch marketing sizes.
NEW_MODELS = {
 'a11':(124.7,211,8,800,1340,220.5),
 'a11-plus':(168.7,257.1,6.9,1200,1920,278.2),
 's6':(159.5,244.5,5.7,1600,2560,267.2),
 's6-lite-2020':(154.3,244.5,7,1200,2000,263.1),
 's6-lite-2022':(154.3,244.5,7,1200,2000,263.1),
 's6-lite-2024':(154.3,244.5,7,1200,2000,263.1),
 's7':(165.3,253.8,6.3,1600,2560,278.1),
 's7-fe':(185,284.8,6.3,1600,2560,315),
 's7-plus':(185,285,5.7,1752,2800,315),
 's8':(165.3,253.8,6.3,1600,2560,278.1),
 's8-plus':(185,285,5.7,1752,2800,315),
 's8-ultra':(208.6,326.4,5.5,1848,2960,369.9),
 's9-fe':(165.8,254.3,6.5,1440,2304,277),
 's9-fe-plus':(185.4,285.4,6.5,1600,2560,315),
 's10-fe':(165.8,254.3,6,1440,2304,277),
 's10-fe-plus':(194.7,300.6,6,1800,2880,332.8),
 's10-lite':(165.8,254.3,6.6,1320,2112,277),
 's12-plus':(187.8,289.5,5.3,1752,2800,320.4),
 's12-ultra':(208.5,326.3,5.1,1848,2960,369.9),
}

def new_profile(suffix):
 # Preserve the existing front geometry and sampled finish hues.
 documents=BASE.parents[3]/'documents'
 sys.path.insert(0,str(documents))
 from generate_brand_svgs import TABLETS, COLORS
 key='galaxy_tab_'+suffix.replace('-','_')
 g=TABLETS[key]
 w,h,d,rx,ry,diagonal=NEW_MODELS[suffix]
 elements=g['el'];count=sum(e[0]=='lens' for e in elements)
 ultra=suffix.endswith('ultra')
 p=profile(('s9',w,h,d,rx,ry,diagonal/25.4,count,ultra))
 p['id']='galaxy-tab-'+suffix
 p['name']='Galaxy Tab '+suffix.upper().replace('-PLUS','+').replace('-ULTRA',' Ultra').replace('-FE',' FE').replace('-LITE-',' Lite (')
 if 'lite-' in suffix:p['name']+=')'
 if suffix=='s10-lite':p['name']='Galaxy Tab S10 Lite'
 finishes={}
 for name,samples in COLORS[key].items():
  name={'chiffon_rose':'Chiffon Pink','coral_red':'Coralred'}.get(name,name.replace('_',' ').title())
  c=rgb(samples[1].lstrip('#'))
  finishes[name]={role:{'rgb':c,'metal':.75,'rough':.35} for role in ('back','rail')}
  finishes[name]['bar']={'rgb':[.035,.039,.045],'rough':.35}
  finishes[name]['logo']={'rgb':[v*.55 for v in c],'rough':.5}
 p['finish']=next(iter(finishes));p['finishes']=finishes
 p['materials']={**finishes[p['finish']], 'black':p['materials']['black'],'flash':p['materials']['flash']}
 sw,sh=p['screen']['fit_box_mm'];bx=(w-sw)/2;by=(h-sh)/2
 radius=min(w,h)*g['r'];p['body_mm']['corner_radius']=radius
 p['screen']['corner_radius_mm']=max(.5,radius-min(bx,by))
 # S6 / S6 Lite / A11 have a portrait-top selfie; later families use the long edge.
 if suffix=='a11' or suffix.startswith('s6'):
  cuts=[{'center_mm':[0,h/2-by/2],'radius_mm':1.25}]
 elif ultra:
  # S8 Ultra dual-camera notch; S12 Ultra single-camera notch. Dimensions are photo estimates.
  cuts=[{'center_mm':[sw/2-1.5,0],'size_mm':[5,21 if suffix=='s8-ultra' else 12],'radius_mm':2.3}]
 else:
  cuts=[{'center_mm':[w/2-bx/2,0],'radius_mm':1.3}]
 p['screen']['cutouts']=cuts
 p['accuracy'].update(screen_geometry='Published rectangular diagonal and exact native aspect; inferred bezels. Concentric corner radii, selfie aperture/notch dimensions are photo estimates.',
  finishes='Official names (regional availability varies); source-icon sampled/representative RGB, not measured material samples.')
 source_key={'s7-plus':'s7','s8-plus':'s8','s8-ultra':'s8','s9-fe-plus':'s9-fe','s10-fe-plus':'s10-fe'}.get(suffix,suffix)
 p['sources']=[NEW_SOURCES[source_key],str(documents/'generate_brand_svgs.py'),str(documents/'brand_colors.json')]
 metric_sources={
  's6-lite-2020':'https://www.samsung.com/al/business/tablets/galaxy-tab-s/galaxy-tab-s6-lite-10-4-inch-gray-64gb-wi-fi-sm-p610nzaasee/',
  's6-lite-2022':'https://www.samsung.com/hk_en/tablets/galaxy-tab-s/galaxy-tab-s6-lite-2022-edition-wi-fi-blue-128gb-sm-p613nzbetgy/',
  's6-lite-2024':'https://www.samsung.com/al/tablets/galaxy-tab-s/galaxy-tab-s6-lite-pink-64gb-sm-p625nziaeuc/',
  's6':'https://www.samsung.com/ie/business/tablets/galaxy-tab-s/galaxy-tab-s6-128gb-sm-t860nzaabtu/',
  's7':'https://www.samsung.com/es/business/tablets/galaxy-tab-s/galaxy-tab-s7-4g-t875-sm-t875nzkaeub/',
  's8':'https://www.samsung.com/ae/tablets/galaxy-tab-s/galaxy-tab-s8-wifi-graphite-128gb-sm-x700nzaamea/'}
 if suffix in metric_sources:p['sources'].insert(1,metric_sources[suffix])
 return p

def correct_rear(p):
 from make_samsung_profiles import logo_contours
 suffix=p['id'].removeprefix('galaxy-tab-')
 measurements=json.loads((BASE/'research/samsung-tablet-rear-measurements.json').read_text())
 family=next(g for g in measurements['groups'].values() if suffix in g['models'])
 w,h=(p['body_mm'][axis] for axis in ('width','height'))
 landscape=family['reference_orientation']=='landscape'
 rw,rh=(h,w) if landscape else (w,h)
 def xy(u,v):
  return [w*(.5-v),h*(u-.5)] if landscape else [w*(.5-u),h*(.5-v)]
 def rectangle(bounds):
  left,top,right,bottom,radius=bounds
  size=[(right-left)*rw,(bottom-top)*rh]
  return xy((left+right)/2,(top+bottom)/2),[*(size[::-1] if landscape else size),radius*rw]
 # FE+ has the same physical camera and edge margins as FE on a larger body.
 scale=254.3/h if suffix=='s10-fe-plus' else 1
 windows=[];lenses=[]
 ring=.25
 for i,(u,v,diameter) in enumerate(family['lenses']):
  if scale!=1:u=1-(1-u)*scale;v=v*165.8/w
  center=xy(u,v);radius=diameter*rw*scale/2-ring
  windows.append([*center,2*radius,2*radius,radius])
  lenses.append({'kind':'main' if i==0 else 'ultrawide','center_mm':center,'radius_mm':radius*.48,'window':i})
 camera={'center_mm':windows[0][:2],'size_mm':[1,1,.5],'bump_mm':0,
  'optical_bump_mm':.75,'lens_ring_mm':ring,'ring_material':'camera_ring',
  'windows':windows,'lenses':lenses,'flash':[[*xy(u,v),diameter*rw/2] for u,v,diameter in family.get('flash',[])],
  'flash_surface':'body','sensors':[[*xy(1-(1-u)*scale if scale!=1 else u,v*165.8/w if scale!=1 else v),radius*rw*scale] for u,v,radius in family.get('sensors',[])],
  'sensor_surface':'body'}
 if 'housing' in family:
  center,size=rectangle(family['housing'])
  camera.update(center_mm=center,size_mm=size,bump_mm=.35,optical_bump_mm=.12,
   roll_mm=.10,integrated_plateau=True,flash_surface='camera',sensor_surface='housing')
 p['camera']=camera
 p['rear_details']=[]
 if 'strip' in family:
  center,size=rectangle(family['strip'])
  p['rear_details'].append({'name':'S Pen charging strip','center_mm':center,'size_mm':size,'depth_mm':.04,'material':'strip'})
 u,v,width=family['logo'];contours=logo_contours(width*rw)
 # Geometry mirrors local SVG coordinates on the rear. Rotate the glyphs with
 # their positions so landscape marks read horizontally with the cameras up.
 if landscape:contours=[[[y,-x] for x,y in contour] for contour in contours]
 p['rear_logo']={'kind':'samsung','center_mm':xy(u,v),'contours_mm':contours}
 for finish,settings in p['finishes'].items():
  color=settings['back']['rgb'];dark=sum(color)/3<.5
  settings['bar']={'rgb':[.025,.028,.032],'rough':.34}
  settings['logo']={'rgb':[min(1,v*1.45+.06) if dark else v*.52 for v in color],'metal':.3,'rough':.45}
  settings['strip']={'rgb':[v*.85 if suffix=='s6' else min(1,v*1.13+.015) for v in color],'metal':.5,'rough':.5}
  if suffix in ('s7','s7-plus','s8','s8-plus','s8-ultra'):
   settings['strip']={'rgb':[.045,.05,.06],'metal':.15,'rough':.48}
  settings['camera_ring']={'rgb':color if suffix.startswith(('s11','s12')) else [.13,.14,.15],'metal':.75,'rough':.3}
 p['materials'].update(p['finishes'][p['finish']])
 p['accuracy'].update(camera_geometry='Official rear-render normalized measurements; model-family housing/charging insert, separate glass windows, rims, apertures and flash. Protrusion and internal optics estimated, not OEM CAD.',
  details='Rear wordmark and built-in charging surface where present; no S Pen accessory. Ports, speaker holes and antenna seams omitted. See research/samsung-tablet-rear-measurements.json for measurements and family transfer limits.')
 p['sources']+=list(dict.fromkeys([family['source']['page'],family['source'].get('render',family['source']['page'])]))
 return p

if __name__=='__main__':
 profiles=[new_profile(key) for key in NEW_MODELS] if '--new' in sys.argv else [profile(row) for row in MODELS]
 for p in profiles:
  correct_rear(p)
  apply_branding(p)
  (BASE/'profiles'/f'{p["id"]}.json').write_text(json.dumps(p,indent=2)+'\n')
  print(p['id'])
