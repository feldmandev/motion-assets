"""OnePlus profiles from official metric specifications and rear product renders."""
from make_device_branding import apply as apply_branding
import json
import math
import sys
from pathlib import Path
from svgelements import Path as SvgPath
BASE=Path(__file__).resolve().parent
DOCUMENTS=BASE
COLORS=json.loads((DOCUMENTS/'brand_colors.json').read_text())
LOGO=json.loads((DOCUMENTS/'brand_logos.json').read_text())['oneplus']
# Portrait chassis axes; tablets are displayed landscape by the review/gallery.
MODELS={
 '13':(76.5,162.9,8.5,6.82,1440,3168,9.4,'https://www.oneplus.com/us/13/specs'),
 '13r':(75.8,161.7,8,6.78,1264,2780,9.4,'https://www.oneplus.in/13r/specs'),
 'pad':(189.41,258.03,6.54,11.61,2000,2800,11,'https://www.oneplus.com/us/oneplus-pad/specs'),
 'pad-2':(195.06,268.66,6.49,12.1,2120,3000,10,'https://www.oneplus.com/uk/oneplus-pad-2/specs'),
 'pad-3':(209.66,289.61,5.97,13.2,2400,3392,10,'https://www.oneplus.com/uk/oneplus-pad-3/specs'),
 'pad-go':(188.04,255.12,6.89,11.35,1720,2408,11,'https://www.oneplus.com/uk/oneplus-pad-go/specs'),
}
IMAGES={
 '13':'https://oasis.opstatics.com/content/dam/oasis/page/2024/global/phones/13/specs/13-blue.png',
 '13r':'https://oasis.opstatics.com/content/dam/oasis/page/2024/global/phones/13r/specs/13R-Trail.png',
 'pad':'https://oasis.opstatics.com/content/dam/oasis/page/2023/pad/pad-specs1.png',
 'pad-2':'https://oasis.opstatics.com/content/dam/oasis/page/2024/global/product/rainbow/specgrey.png',
 'pad-3':'https://www.oneplus.com/content/dam/oneplus/2025/specs/pad3/images/Pad3_Erhai_Blue_1080x1080.png',
 'pad-go':'https://oasis.opstatics.com/content/dam/oasis/page/2023/bluey/bluey-spec.png',
}
def rgb(h):return [int(h[i:i+2],16)/255 for i in (1,3,5)]
def logo_contours(width,landscape):
 out=[]
 for sub in SvgPath(LOGO['d']).as_subpaths():
  points=[]
  for seg in sub:
   if seg.__class__.__name__ in ('Move','Close'):continue
   n=1 if seg.__class__.__name__=='Line' else 12
   for i in range(n+1):
    p=seg.point(i/n);x=(p.x-.5)*width;y=(p.y-.5/LOGO['aspect'])*width
    point=[y,-x] if landscape else [x,y]
    if not points or points[-1]!=point:points.append(point)
  if len(points)>2:out.append(points)
 return out

def make(key,row):
 w,h,d,diag,px,py,r,url=row;tablet=key.startswith('pad')
 finishes={}
 for name,palette in COLORS['oneplus_'+key.replace('-','_')].items():
  c=rgb(palette[1]);dark=sum(c)/3<.5
  bar=[.025,.03,.04] if key=='pad-3' else [.72,.74,.77] if key=='13' else [v*.82 for v in c]
  finishes[name.replace('_',' ').title()]={'back':{'rgb':c,'metal':.6 if tablet else .15,'rough':.4},'rail':{'rgb':c,'metal':.8,'rough':.3},'bar':{'rgb':bar,'metal':.75,'rough':.3},'logo':{'rgb':[min(1,v*1.5+.1) if dark else v*.6 for v in c],'rough':.45},'band':{'rgb':[min(1,v*1.14) for v in c],'metal':.5,'rough':.35}}
 default=next(iter(finishes));m={**finishes[default],'black':{'rgb':[.008,.011,.016],'rough':.4},'flash':{'rgb':[.85,.84,.76],'rough':.4}}
 scale=diag*25.4/math.hypot(px,py);sw,sh=px*scale,py*scale
 bezel=min((w-sw)/2,(h-sh)/2)
 def xy(u,v):return [w*(.5-v),h*(u-.5)] if tablet else [w*(.5-u),h*(.5-v)]
 windows=[];lenses=[]
 if not tablet:
  # Bounds measured in the 1080-square official composite. Height is unobscured;
  # rear width inferred from published aspect because the front overlaps it.
  bounds=[194,120,588,960] if key=='13' else [201,119,597,958]
  housing=[213,164,482,433] if key=='13' else [225,156,482,413]
  sx=h/(bounds[3]-bounds[1]);cx=(housing[0]+housing[2])/2;cy=(housing[1]+housing[3])/2
  center=[w/2-(cx-bounds[0])*sx,h/2-(cy-bounds[1])*sx]
  diameter=(housing[2]-housing[0])*sx
  camera={'center_mm':center,'size_mm':[diameter,diameter,diameter/2],'bump_mm':2.4 if key=='13' else 2.0,'roll_mm':.35,'integrated_plateau':True,'skip_source_pupil':True,'optical_bump_mm':.15,'lens_ring_mm':.22,'windows':windows,'lenses':lenses,'flash':[],'flash_offset_mm':.25}
  # Three real cameras and one black flash surround, with room inside the rim.
  coords=[(302,250),(395,250),(302,344),(395,344)] if key=='13' else [(303,232),(393,232),(303,319),(393,319)]
  for i,(x,y) in enumerate(coords):
   pos=[w/2-(x-bounds[0])*sx,h/2-(y-bounds[1])*sx];wr=(36 if key=='13' else 33)*sx
   windows.append([*pos,wr*2,wr*2,wr])
   if i<3:lenses.append({'kind':'main' if i==0 else 'ultrawide','center_mm':pos,'radius_mm':wr*.48,'window':i})
   else:camera['flash'].append([*pos,wr*.36])
  camera['sensors']=[[*[center[0]-diameter*.36,center[1]],.45]]
  camera['sensor_surface']='camera'
  camera_ref={'reference':f'research/oneplus/{key}.png','body_bounds_px':bounds,'housing_bounds_px':housing,'scale_mm_per_px':sx,'uncertainty_mm':.8,'note':'Composite has rear width partly occluded; published chassis aspect used for width. Protrusion estimated, not measured.'}
  cutouts=[{'center_mm':[0,h/2-6.2],'radius_mm':1.35}]
 else:
  # Rear positions measured in landscape orientation from the bare upper part
  # of the official composite. Pad 3 moves its camera to a corner capsule.
  cx,cy=xy(.914,.077) if key=='pad-3' else xy(.5,.112 if key!='pad-go' else .092)
  size=[17.0,36.5,8.5] if key=='pad-3' else [26,26,13] if key in ('pad','pad-2') else [22,22,11]
  if key=='pad-3':pos=xy(.94,.077);wr=4.1;flash=[[*xy(.878,.077),1.0]]
  else:pos=[cx,cy];wr=8 if key in ('pad','pad-2') else 7;flash=[]
  windows.append([*pos,2*wr,2*wr,wr]);lenses.append({'kind':'main','center_mm':pos,'radius_mm':wr*.4,'window':0})
  camera={'center_mm':[cx,cy],'size_mm':size,'bump_mm':1.2,'roll_mm':.18,'integrated_plateau':True,'skip_source_pupil':True,'optical_bump_mm':.1,'lens_ring_mm':.25,'windows':windows,'lenses':lenses,'flash':flash,'flash_offset_mm':.1}
  cutouts=[{'center_mm':[-w/2+max(2,(w-sw)/4),0],'radius_mm':1.2}]
  camera_ref={'reference':f'research/oneplus/{key}.png','orientation':'landscape','housing_size_mm':size[:2],'center_normalized':[.914,.077] if key=='pad-3' else [.5,.112 if key!='pad-go' else .092],'uncertainty_mm':1.2,'note':'Official composite render, approximate front-on fitting; protrusion estimated.'}
 name='OnePlus '+(key.replace('pad','Pad').replace('-',' ') if tablet else key.upper().replace('R','R'))
 p={'id':'oneplus-'+key,'name':name,'manufacturer':'OnePlus','form_factor':'tablet' if tablet else 'phone','status':'provisional','finish':default,
  'body_mm':{'width':w,'height':h,'depth':d,'corner_radius':r,'edge_roll':.55 if key in ('13','pad','pad-go') else .3,'front_rail_mm':.4},'materials':m,'finishes':finishes,
  'screen':{'object':'Device screen','node':'Device screen','panel':'Body','resolution':[px,py],'fit_box_mm':[sw,sh],'center_mm':[0,0,d/2+.035],'corner_radius_mm':max(1,r-bezel),'create_cutouts':True,'cutouts':cutouts},
  'camera':camera,'buttons':[{'name':'Power','side':'right','center_y_mm':h/2-44,'length_mm':10,'width_mm':2,'thickness_mm':.3,'radius_mm':.8},{'name':'Volume','side':'right','center_y_mm':h/2-23,'length_mm':18,'width_mm':2,'thickness_mm':.3,'radius_mm':.8}],
  'rear_logo':{'kind':'oneplus','surface_offset_mm':.08,'center_mm':xy(.5,.52) if tablet else [0,-4],'contours_mm':logo_contours(13 if tablet else 12,tablet)},
  'accuracy':{'body_dimensions':'OnePlus official metric chassis dimensions. OnePlus 13 uses 8.5 mm glass chassis; Midnight Ocean leather is 8.9 mm and remains an approximate finish on that chassis.','screen_geometry':'Published full diagonal and native pixel aspect; concentric estimated corners. Bezel camera estimated from product render.','camera_geometry':'Official rear-render fit, measurements below. Bump depth, roll, glass and optical internals illustrative; not OEM CAD.','finishes':'Official finish names, approximate existing collection sRGB swatches; not calibrated physical materials.','omissions':'Ports, speaker holes, alert slider, antenna seams and microscopic inscriptions omitted.'},'sources':[url,IMAGES[key]],'rear_reference':camera_ref}
 if key=='pad-go':p['rear_details']=[{'name':'Upper contrasting rear band','center_mm':xy(.5,.09),'size_mm':[w*.18-1,h-1,10],'depth_mm':.15,'material':'band'}]
 return p
if __name__=='__main__':
 for key,row in MODELS.items():
  p=apply_branding(make(key,row));(BASE/'profiles'/(p['id']+'.json')).write_text(json.dumps(p,indent=2))
 (BASE/'research/oneplus-model-measurements.json').write_text(json.dumps({key:make(key,row)['rear_reference'] for key,row in MODELS.items()},indent=2))
 print('Generated',len(MODELS),'OnePlus profiles')
